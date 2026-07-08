from __future__ import annotations

import queue
import re
import sys
import threading
import time

import numpy as np
import pythoncom
import sounddevice as sd
from pynput import keyboard
from PySide6.QtCore import QObject, QTimer, Signal, Slot

from app_settings import AppSettings
from engines.base import PromptMode, RuntimeDiagnostics, TranscriptionRequest, TranscriptionResult
from engines.context_capture import VisualContextManager, get_foreground_app_context
from engines.whisper_backend import WhisperBackend


SAMPLE_RATE = 16000
CHUNK_DURATION = 0.02
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
MAX_AUDIO_QUEUE_SIZE = 32
MAX_REQUEST_QUEUE_SIZE = 16
MAX_VAD_UTTERANCE_SECONDS = 25
MAX_PTT_UTTERANCE_SECONDS = 120


def get_punctuation_char(punctuation_name: str):
    pmap = {
        "question mark": "?",
        "exclamation mark": "!",
        "comma": ",",
        "period": ".",
        "full stop": ".",
        "colon": ":",
        "semicolon": ";",
        "open parenthesis": "(",
        "close parenthesis": ")",
        "open bracket": "[",
        "close bracket": "]",
        "open brace": "{",
        "close brace": "}",
        "hyphen": "-",
        "dash": "-",
        "underscore": "_",
        "plus": "+",
        "equals": "=",
        "at": "@",
        "hash": "#",
        "dollar": "$",
        "percent": "%",
        "caret": "^",
        "ampersand": "&",
        "asterisk": "*",
    }
    return pmap.get(punctuation_name.lower())


def create_backend(app_settings: AppSettings):
    if app_settings.backend == "transformers-asr":
        try:
            from engines.transformers_asr_backend import TransformersASRBackend
        except Exception as exc:
            return UnavailableBackend("Transformers ASR", exc)

        return TransformersASRBackend(app_settings)
    if app_settings.backend == "gemma-4":
        try:
            from engines.gemma4_backend import Gemma4Backend
        except Exception as exc:
            return UnavailableBackend("Transformers Gemma", exc)

        return Gemma4Backend(app_settings)
    if app_settings.backend == "gemma-gguf-server":
        try:
            from engines.gemma_gguf_backend import GemmaGGUFBackend
        except Exception as exc:
            return UnavailableBackend("Gemma GGUF server", exc)

        return GemmaGGUFBackend(app_settings)
    return WhisperBackend(app_settings)


class UnavailableBackend:
    def __init__(self, label: str, error: Exception):
        self.label = label
        self.error = error

    def load(self):
        from engines.base import BackendLoadResult, RuntimeDiagnostics

        message = f"{self.label} backend is unavailable in this build: {self.error}"
        return BackendLoadResult(
            False,
            message,
            [],
            RuntimeDiagnostics(
                status="error",
                headline="Selected runtime is not available",
                summary=(
                    "This OmniDictate build cannot use the selected speech runtime. "
                    "The public installer uses Faster-Whisper for local dictation."
                ),
                next_steps=[
                    "Open Settings and choose Faster-Whisper.",
                    "Use Pure transcription for the public Windows build.",
                    "Restart dictation after saving Settings.",
                ],
                technical_details=[message],
            ),
        )

    def unload(self) -> None:
        return

    def transcribe(self, _request):
        raise RuntimeError(f"{self.label} backend is unavailable in this build: {self.error}")


class DictationWorker(QObject):
    status_updated = Signal(str)
    transcription_ready = Signal(str)
    preview_requested = Signal(object)
    error_occurred = Signal(str)
    audio_level = Signal(float)
    context_updated = Signal(str)
    route_updated = Signal(str)
    runtime_updated = Signal(object)
    stop_completed = Signal()

    def __init__(
        self,
        gui_wid,
        app_settings: AppSettings,
        visual_context_manager: VisualContextManager,
        parent=None,
    ):
        super().__init__(parent)
        self.gui_wid = gui_wid
        self.app_settings = app_settings
        self.visual_context_manager = visual_context_manager

        self.language_code = app_settings.language
        self._vad_enabled = app_settings.vad_enabled
        self.silence_threshold = app_settings.silence_threshold
        self.silence_frames = int(0.5 * SAMPLE_RATE / CHUNK_SIZE)
        self.char_delay = app_settings.char_delay
        self.type_into_active_app = app_settings.type_into_active_app
        self.min_ptt_duration_seconds = max(0, app_settings.min_ptt_duration_ms) / 1000.0
        self.filter_words = set(word.lower().strip() for word in app_settings.filter_words if word.strip())

        self.backend = None
        self.audio_stream = None
        self._is_running = False
        self._ptt_active = False
        self._ptt_started_at: float | None = None
        self.audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=MAX_AUDIO_QUEUE_SIZE)
        self.request_queue: queue.Queue[TranscriptionRequest] = queue.Queue(maxsize=MAX_REQUEST_QUEUE_SIZE)
        self.text_queue: queue.Queue[str] = queue.Queue()
        self.recording = False
        self.audio_buffer: list[np.ndarray] = []
        self.vad_active = False
        self.frames_since_speech = 0
        self._ptt_chunk_has_speech = False
        self._last_audio_overflow_notice = 0.0

        self.typing_thread_instance = None
        self.inference_thread_instance = None
        self.stop_typing_event = threading.Event()
        self.stop_inference_event = threading.Event()

        self.audio_check_timer = QTimer(self)
        self.audio_check_timer.timeout.connect(self._check_audio_queue)
        self.audio_check_interval = 50

    @Slot(bool)
    def set_vad_enabled(self, enabled: bool):
        if self._vad_enabled != enabled:
            self._vad_enabled = enabled
            self.app_settings.vad_enabled = enabled
            if not enabled and self.vad_active:
                self.recording = False
                self.vad_active = False
                self.audio_buffer = []
                if self._is_running:
                    self.status_updated.emit("Listening...")

    @Slot(bool)
    def set_ptt_state(self, is_pressed: bool):
        if is_pressed:
            if not self._ptt_active:
                self._ptt_started_at = time.monotonic()
                self._ptt_chunk_has_speech = False
                self.frames_since_speech = 0
                if self.vad_active:
                    self.recording = False
                    self.vad_active = False
                    self.audio_buffer = []
            self._ptt_active = True
            return

        was_ptt_active = self._ptt_active
        started_at = self._ptt_started_at
        self._ptt_active = is_pressed
        self._ptt_started_at = None
        if not was_ptt_active:
            return
        if not self.recording or self.vad_active:
            self.audio_buffer = []
            self._ptt_chunk_has_speech = False
            self.frames_since_speech = 0
            if self._is_running:
                self.status_updated.emit("Listening...")
            return

        self.recording = False
        elapsed = time.monotonic() - started_at if started_at else 0.0
        if elapsed < self.min_ptt_duration_seconds:
            self.audio_buffer = []
            self._ptt_chunk_has_speech = False
            if self._is_running:
                self.status_updated.emit("Ignored short PTT tap.")
                self.status_updated.emit("Listening...")
            return

        try:
            self._process_audio_buffer(source="ptt-final")
        except Exception as exc:
            self.error_occurred.emit(f"PTT processing error: {exc}")
        finally:
            self._ptt_chunk_has_speech = False
            self.frames_since_speech = 0

    @Slot(str)
    def set_prompt_mode(self, prompt_mode: str):
        try:
            normalized_mode = PromptMode(prompt_mode)
        except ValueError:
            return
        self.app_settings.prompt_mode = normalized_mode.value
        self.status_updated.emit(f"Output style changed to {normalized_mode.value.replace('-', ' ')}.")

    @Slot(str)
    def queue_manual_text(self, text: str):
        queued_text = (text or "").strip()
        if queued_text:
            self.text_queue.put(queued_text + " ")

    @Slot()
    def start_processing(self):
        if self._is_running:
            return

        self.backend = create_backend(self.app_settings)
        load_result = self.backend.load()
        runtime_diagnostics = load_result.runtime_diagnostics
        if runtime_diagnostics is None:
            runtime_diagnostics = RuntimeDiagnostics(
                status="checked",
                headline="Runtime loaded",
                summary=load_result.status_message,
                technical_details=[load_result.status_message, *load_result.warnings],
            )
        self.runtime_updated.emit(runtime_diagnostics)
        self.status_updated.emit(load_result.status_message)
        for warning in load_result.warnings:
            self.status_updated.emit(warning)
        if not load_result.success:
            self.error_occurred.emit(load_result.status_message)
            return

        self._is_running = True
        self.recording = False
        self.vad_active = False
        self.frames_since_speech = 0
        self.audio_buffer = []
        self._ptt_chunk_has_speech = False
        self._clear_queue(self.audio_queue)
        self._clear_queue(self.request_queue)
        self._clear_queue(self.text_queue)
        self.stop_typing_event.clear()
        self.stop_inference_event.clear()

        self.typing_thread_instance = threading.Thread(target=self._typing_loop, daemon=True)
        self.typing_thread_instance.start()
        self.inference_thread_instance = threading.Thread(target=self._inference_loop, daemon=True)
        self.inference_thread_instance.start()

        try:
            device_info = sd.query_devices(kind="input")
            self.status_updated.emit(f"Using device: {device_info['name']}")
            self.audio_stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                blocksize=CHUNK_SIZE,
                device=None,
                channels=1,
                dtype="int16",
                latency="high",
                callback=self._audio_callback,
            )
            self.audio_stream.start()
            self.context_updated.emit(self.visual_context_manager.describe())
            self.status_updated.emit("Listening...")
            self.audio_check_timer.start(self.audio_check_interval)
        except sd.PortAudioError as exc:
            self.error_occurred.emit(f"PortAudio Error: {exc}")
            self.stop_processing()
        except Exception as exc:
            self.error_occurred.emit(f"Audio stream error: {exc}")
            self.stop_processing()

    @Slot()
    def stop_processing(self):
        if not self._is_running and self.backend is None:
            self.stop_completed.emit()
            return

        self.status_updated.emit("Stopping...")
        self._is_running = False
        self.audio_check_timer.stop()
        self.stop_typing_event.set()
        self.stop_inference_event.set()
        self._clear_queue(self.request_queue)

        if self.audio_stream:
            try:
                self.audio_stream.abort()
                self.audio_stream.close()
            except Exception:
                pass
            finally:
                self.audio_stream = None

        self._join_thread(self.inference_thread_instance)
        self._join_thread(self.typing_thread_instance)
        self.inference_thread_instance = None
        self.typing_thread_instance = None
        self._clear_queue(self.audio_queue)
        self._clear_queue(self.request_queue)
        self._clear_queue(self.text_queue)

        if self.backend is not None:
            try:
                self.backend.unload()
            except Exception as exc:
                self.error_occurred.emit(f"Error unloading backend: {exc}")
            finally:
                self.backend = None

        self.recording = False
        self.vad_active = False
        self.audio_buffer = []
        self._ptt_chunk_has_speech = False
        self.context_updated.emit(self.visual_context_manager.describe())
        self.status_updated.emit("Idle")
        self.stop_completed.emit()

    def _audio_callback(self, indata, frames, callback_time, status):
        if status:
            now = time.time()
            if now - self._last_audio_overflow_notice >= 2.0:
                self._last_audio_overflow_notice = now
                self.status_updated.emit(f"Microphone callback warning: {status}")
        if self._is_running:
            audio_bytes = bytes(indata)
            try:
                self.audio_queue.put_nowait(audio_bytes)
            except queue.Full:
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self.audio_queue.put_nowait(audio_bytes)
                except queue.Full:
                    pass

    @Slot()
    def _check_audio_queue(self):
        if not self._is_running:
            return

        try:
            processed_chunk_count = 0
            max_chunks_per_cycle = 5
            while not self.audio_queue.empty() and processed_chunk_count < max_chunks_per_cycle:
                raw_audio_chunk = self.audio_queue.get_nowait()
                processed_chunk_count += 1
                try:
                    chunk_np = np.frombuffer(raw_audio_chunk, dtype=np.int16)
                    amplitude = np.abs(chunk_np).mean()
                except Exception as exc:
                    print(f"Error processing audio chunk: {exc}")
                    continue

                self.audio_level.emit(float(amplitude))

                if self._ptt_active:
                    self._handle_ptt_chunk(chunk_np, amplitude)
                    continue

                if not self._vad_enabled:
                    continue

                if not self.recording:
                    if amplitude > self.silence_threshold:
                        self.status_updated.emit("Recording (VAD)...")
                        self.recording = True
                        self.vad_active = True
                        self.audio_buffer = [chunk_np]
                        self.frames_since_speech = 0
                elif self.vad_active:
                    if amplitude > self.silence_threshold:
                        self.frames_since_speech = 0
                        self.audio_buffer.append(chunk_np)
                    else:
                        self.frames_since_speech += 1
                        if self.frames_since_speech > self.silence_frames:
                            self.recording = False
                            self.vad_active = False
                            self._process_audio_buffer(source="vad")
        except queue.Empty:
            return
        except Exception as exc:
            self.error_occurred.emit(f"Audio check loop error: {exc}")

    def _handle_ptt_chunk(self, chunk_np: np.ndarray, amplitude: float):
        if not self.recording or self.vad_active:
            self.status_updated.emit("Recording (PTT)...")
            self.recording = True
            self.vad_active = False
            self.audio_buffer = []
            self.frames_since_speech = 0
            self._ptt_chunk_has_speech = False

        if amplitude > self.silence_threshold:
            if not self._ptt_chunk_has_speech:
                self.audio_buffer = []
            self._ptt_chunk_has_speech = True
            self.frames_since_speech = 0
            self.audio_buffer.append(chunk_np)
            return

        if not self._ptt_chunk_has_speech:
            self.frames_since_speech = 0
            self.audio_buffer = []
            return

        self.audio_buffer.append(chunk_np)
        self.frames_since_speech += 1
        if self.frames_since_speech > self.silence_frames:
            self._process_audio_buffer(source="ptt-chunk")
            self._ptt_chunk_has_speech = False
            self.frames_since_speech = 0
            if self._is_running and self._ptt_active:
                self.status_updated.emit("Recording (PTT)...")

    def _process_audio_buffer(self, source: str = "vad"):
        if not self.audio_buffer:
            if self._is_running and not self._ptt_active:
                self.status_updated.emit("Listening...")
            return

        buffer_copy = list(self.audio_buffer)
        self.audio_buffer = []
        try:
            audio_data = np.concatenate(buffer_copy)
        except ValueError:
            return

        audio_float32 = audio_data.astype(np.float32) / 32768.0
        if audio_float32.size == 0:
            return

        max_seconds = MAX_PTT_UTTERANCE_SECONDS if source.startswith("ptt") else MAX_VAD_UTTERANCE_SECONDS
        max_samples = int(max_seconds * SAMPLE_RATE)
        if audio_float32.shape[0] > max_samples:
            label = "PTT recording" if source.startswith("ptt") else "VAD utterance"
            self.status_updated.emit(
                f"{label} exceeded {max_seconds} seconds; transcribing the first {max_seconds} seconds."
            )
            audio_float32 = audio_float32[:max_samples]

        request = self._build_transcription_request(audio_float32)
        if request is None:
            return

        self._enqueue_transcription_request(request)

    def _enqueue_transcription_request(self, request: TranscriptionRequest) -> None:
        self.status_updated.emit("Queued utterance for transcription...")
        try:
            self.request_queue.put_nowait(request)
        except queue.Full:
            self.error_occurred.emit(
                "Transcription is behind and the phrase queue is full. Pause briefly or use a faster model."
            )

    def _build_transcription_request(self, audio_float32: np.ndarray) -> TranscriptionRequest | None:
        try:
            prompt_mode = PromptMode(self.app_settings.prompt_mode)
        except ValueError:
            prompt_mode = PromptMode.PURE

        visual_context = self.visual_context_manager.capture_snapshot()
        self.context_updated.emit(visual_context.description)
        target_app = get_foreground_app_context()
        if prompt_mode == PromptMode.REASONING:
            max_new_tokens = 192
        elif prompt_mode == PromptMode.CONTEXT:
            max_new_tokens = 64
        else:
            max_new_tokens = 48

        return TranscriptionRequest(
            audio=audio_float32,
            sample_rate=SAMPLE_RATE,
            language=self.language_code,
            prompt_mode=prompt_mode,
            visual_context=visual_context,
            target_app=target_app,
            enable_thinking=(prompt_mode == PromptMode.REASONING),
            max_new_tokens=max_new_tokens,
        )

    def _inference_loop(self):
        while not self.stop_inference_event.is_set():
            try:
                request = self.request_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            if self.backend is None:
                continue

            try:
                self.status_updated.emit("Transcribing...")
                result = self.backend.transcribe(request)
                self._handle_transcription_result(result)
            except Exception as exc:
                self.error_occurred.emit(f"Transcription error: {exc}")
            finally:
                if self._is_running and not self.recording and not self._ptt_active:
                    self.status_updated.emit("Listening...")

    def _handle_transcription_result(self, result: TranscriptionResult) -> None:
        self.route_updated.emit(result.execution_label)
        for warning in result.warnings:
            self.status_updated.emit(warning)

        processed_text = (result.text or "").strip()
        if not processed_text:
            return
        if processed_text.lower() in self.filter_words:
            return

        self.transcription_ready.emit(processed_text)

        if result.requires_confirmation and result.preview is not None:
            self.preview_requested.emit(result.preview)
            return

        if not self.type_into_active_app:
            self.status_updated.emit("Transcribe Only: typing is off.")
            return

        self._route_text_output(processed_text)

    def _route_text_output(self, processed_text: str) -> None:
        punc_match = re.match(
            r"^(question mark|exclamation mark|comma|period|full stop|colon|semicolon|open parenthesis|close parenthesis|open bracket|close bracket|open brace|close brace|hyphen|dash|underscore|plus|equals|at|hash|dollar|percent|caret|ampersand|asterisk)[.?!]?$",
            processed_text.lower().strip(),
        )
        if punc_match:
            punc_char = get_punctuation_char(punc_match.group(1))
            if punc_char:
                self.text_queue.put(punc_char)
                return

        self.text_queue.put(processed_text + " ")

    def _foreground_is_own_window(self, foreground_hwnd: int) -> bool:
        return foreground_hwnd == self.gui_wid

    def _discard_text_if_own_window(self, pending_text: str | None, foreground_hwnd: int) -> bool:
        if not self._foreground_is_own_window(foreground_hwnd):
            return False
        if pending_text:
            self._clear_queue(self.text_queue)
            self.status_updated.emit("Skipped typing because OmniDictate is focused.")
        return True

    def _type_pending_text(self, keyboard_controller, pending_text: str, foreground_hwnd: int) -> bool:
        if self._foreground_is_own_window(foreground_hwnd):
            return False

        for char in pending_text:
            if not self._is_running or self.stop_typing_event.is_set():
                break
            keyboard_controller.press(char)
            keyboard_controller.release(char)
            time.sleep(self.char_delay)
        return True

    def _typing_loop(self):
        keyboard_controller = keyboard.Controller()
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
        pending_text = None
        try:
            import ctypes

            while self._is_running and not self.stop_typing_event.is_set():
                if pending_text is None:
                    try:
                        pending_text = self.text_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                try:
                    hwnd = ctypes.windll.user32.GetForegroundWindow()
                    if self._discard_text_if_own_window(pending_text, hwnd):
                        pending_text = None
                        continue

                    if self._type_pending_text(keyboard_controller, pending_text, hwnd):
                        pending_text = None
                        if self._is_running and not self.recording and not self._ptt_active:
                            self.status_updated.emit("Listening...")
                except Exception as exc:
                    pending_text = None
                    self.error_occurred.emit(f"Error typing text: {exc}")
        finally:
            pythoncom.CoUninitialize()

    @staticmethod
    def _clear_queue(target_queue: queue.Queue) -> None:
        while True:
            try:
                target_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                break

    @staticmethod
    def _join_thread(thread_obj: threading.Thread | None) -> None:
        if thread_obj and thread_obj.is_alive():
            thread_obj.join(timeout=1.5)
