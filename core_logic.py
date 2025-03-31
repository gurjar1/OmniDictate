# core_logic.py

# Standard library imports
import time
import threading
import sys
import os
import queue
import re

# Third-party library imports
import numpy as np
import torch
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard # Keep for Controller in typing thread

# PySide6 imports for threading and signals
from PySide6.QtCore import QObject, Signal, QTimer, Slot

# --- Configuration Constants ---
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.02
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
# CHAR_DELAY passed via __init__

# --- Helper Functions ---
# (Unchanged - delete_last_n_words_direct, insert_punctuation, insert_new_line)
def delete_last_n_words_direct(n):
    """Deletes the last n words directly in the active window."""
    try:
        from pywinauto import application
        import ctypes, time
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd == 0: print("Error: Could not get foreground window handle."); return False
        app = application.Application().connect(handle=hwnd)
        active_window = app.top_window()
        active_window.set_focus(); time.sleep(0.05)
        for _ in range(n): active_window.type_keys("^+{LEFT}"); time.sleep(0.05)
        active_window.type_keys("{DELETE}"); time.sleep(0.05)
        return True
    except ImportError: print("Error: pywinauto not installed."); return False
    except Exception as e: print(f"Error deleting text: {e}"); return False

def insert_punctuation(punctuation_name):
    """Inserts punctuation based on a verbal command."""
    try:
        from pywinauto import application
        import ctypes, time
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd == 0: print("Error: Could not get foreground window handle."); return False
        app = application.Application().connect(handle=hwnd)
        active_window = app.top_window()
        active_window.set_focus(); time.sleep(0.05)
        pmap = {"question mark": "?", "exclamation mark": "!", "comma": ",", "period": ".", "full stop": ".", "colon": ":", "semicolon": ";", "open parenthesis": "(", "close parenthesis": ")", "open bracket": "[", "close bracket": "]", "open brace": "{", "close brace": "}", "hyphen": "-", "dash": "-", "underscore": "_", "plus": "+", "equals": "=", "at": "@", "hash": "#", "dollar": "$", "percent": "%", "caret": "^", "ampersand": "&", "asterisk": "*"}
        punc = pmap.get(punctuation_name.lower())
        if punc: active_window.type_keys(punc, pause=0.01); print(f"Inserted: {punc}"); return True
        else: print(f"Unknown punctuation: {punctuation_name}"); return False
    except ImportError: print("Error: pywinauto not installed."); return False
    except Exception as e: print(f"Error inserting punctuation: {e}"); return False

def insert_new_line():
    """Inserts a new line."""
    try:
        from pywinauto import application
        import ctypes, time
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd == 0: print("Error: Could not get foreground window handle."); return False
        app = application.Application().connect(handle=hwnd)
        active_window = app.top_window()
        active_window.set_focus(); time.sleep(0.05)
        active_window.type_keys("{ENTER}"); print("Inserted new line."); return True
    except ImportError: print("Error: pywinauto not installed."); return False
    except Exception as e: print(f"Error inserting new line: {e}"); return False


# --- Worker Class ---
class DictationWorker(QObject):
    status_updated = Signal(str)
    transcription_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, gui_wid, model_size="large-v3", language="en", vad_enabled=True,
                 silence_threshold=500, silence_duration=0.5, char_delay=0.02,
                 filter_words=None, new_line_commands=None, parent=None):
        super().__init__(parent)
        self.gui_wid = gui_wid
        self.model_size = model_size
        self.language_code = language
        self._vad_enabled = vad_enabled
        self.silence_threshold = silence_threshold
        self.silence_frames = int(silence_duration * SAMPLE_RATE / CHUNK_SIZE)
        self.char_delay = char_delay
        self.filter_words = set(word.lower().strip() for word in filter_words) if filter_words else set()
        self.new_line_commands = set(cmd.lower().strip() for cmd in new_line_commands) if new_line_commands else {"new line", "next line"}

        print(f"Worker Init: GUI WID={self.gui_wid}, Model={self.model_size}, Lang={self.language_code}, VAD={self._vad_enabled}")
        print(f"Worker Init: Silence Thresh={self.silence_threshold}, Frames={self.silence_frames}, Char Delay={self.char_delay}")
        print(f"Worker Init: Filter Words={self.filter_words}")
        print(f"Worker Init: New Line Cmds={self.new_line_commands}")

        self.model = None
        self.audio_stream = None
        self._is_running = False
        self._ptt_active = False
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        self.recording = False
        self.audio_buffer = []
        self.vad_active = False
        self.frames_since_speech = 0
        self.typing_thread_instance = None
        self.stop_typing_event = threading.Event()
        self.audio_check_timer = QTimer(self)
        self.audio_check_timer.timeout.connect(self._check_audio_queue)
        self.audio_check_interval = 50

    # --- Public Slots ---
    @Slot(bool)
    def set_vad_enabled(self, enabled: bool):
        if self._vad_enabled != enabled:
            print(f"Setting VAD Enabled: {enabled}")
            self._vad_enabled = enabled
            if not enabled and self.vad_active:
                self.recording = False; self.vad_active = False; self.audio_buffer = []
                if self._is_running: self.status_updated.emit("Listening...")

    @Slot(bool)
    def set_ptt_state(self, is_pressed: bool):
        self._ptt_active = is_pressed
        if not is_pressed and self.recording and not self.vad_active:
            print("Recording stopped (PTT Release). Transcribing...")
            self.recording = False
            self._process_audio_buffer()

    # --- Core Logic Methods ---
    def load_model(self, force_reload=False):
        if self.model and not force_reload: return True
        if self.model and force_reload: print(f"Force reloading model '{self.model_size}'..."); del self.model; self.model = None;
        if torch.cuda.is_available(): print("Clearing CUDA cache..."); torch.cuda.empty_cache()
        try:
            self.status_updated.emit(f"Loading model '{self.model_size}'...")
            use_cuda = torch.cuda.is_available(); device = "cuda" if use_cuda else "cpu"; compute_type = "float16" if use_cuda else "int8"
            if not self.model_size: raise ValueError("Model size empty.")
            self.model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
            status_msg = f"Model '{self.model_size}' loaded on {device.upper()}."; print(status_msg); self.status_updated.emit(status_msg)
            return True
        except Exception as e: error_msg = f"Error loading model: {e}"; print(error_msg); self.error_occurred.emit(error_msg); self.model = None; return False

    @Slot()
    def start_processing(self):
        if self._is_running: return
        if not self.load_model(force_reload=True): self.error_occurred.emit("Model failed to load."); return

        self._is_running = True; self.status_updated.emit("Starting...")
        self.audio_buffer = []; self.recording = False; self.vad_active = False; self.frames_since_speech = 0

        # *** CORRECTED QUEUE CLEARING LOOPS ***
        print("Clearing queues...")
        while True:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break # Exit loop when queue is empty
            except Exception as e_q:
                print(f"Error clearing audio queue item: {e_q}")
                break # Exit on other errors too

        while True:
            try:
                self.text_queue.get_nowait()
            except queue.Empty:
                break # Exit loop when queue is empty
            except Exception as e_q:
                print(f"Error clearing text queue item: {e_q}")
                break
        print("Queues cleared.")
        # *** END CORRECTION ***

        self.stop_typing_event.clear()
        if self.typing_thread_instance and self.typing_thread_instance.is_alive(): print("Warning: Typing thread still alive?")
        self.typing_thread_instance = threading.Thread(target=self._typing_loop, daemon=True)
        self.typing_thread_instance.start()

        try:
            device_info = sd.query_devices(kind='input')
            self.status_updated.emit(f"Using device: {device_info['name']}")
            self.audio_stream = sd.InputStream(samplerate=SAMPLE_RATE, blocksize=CHUNK_SIZE, device=None, channels=1, dtype='int16', callback=self._audio_callback)
            self.audio_stream.start()
            self.status_updated.emit("Listening...")
            self.audio_check_timer.start(self.audio_check_interval)
        except sd.PortAudioError as pae: error_msg = f"PortAudio Error: {pae}"; print(error_msg); self.error_occurred.emit(error_msg); self.stop_processing()
        except Exception as e: error_msg = f"Audio stream error: {e}"; print(error_msg); self.error_occurred.emit(error_msg); self.stop_processing()

    @Slot()
    def stop_processing(self):
        if not self._is_running: return
        print("Stopping worker processing..."); self.status_updated.emit("Stopping...")
        self._is_running = False; self.audio_check_timer.stop()

        if self.audio_stream:
            try: self.audio_stream.abort(); self.audio_stream.close(); print("Audio stream stopped.")
            except Exception as e: print(f"Error stopping audio stream: {e}")
            finally: self.audio_stream = None

        self.stop_typing_event.set()
        if self.typing_thread_instance and self.typing_thread_instance.is_alive():
            print("Waiting for typing thread to finish...")
            self.typing_thread_instance.join(timeout=1.5)
            if self.typing_thread_instance.is_alive(): print("Warning: Typing thread did not stop gracefully.")
        self.typing_thread_instance = None

        # *** CORRECTED QUEUE CLEARING LOOPS ***
        print("Clearing queues...")
        while True:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
            except Exception as e_q:
                print(f"Error clearing audio queue item: {e_q}")
                break
        while True:
            try:
                self.text_queue.get_nowait()
            except queue.Empty:
                break
            except Exception as e_q:
                print(f"Error clearing text queue item: {e_q}")
                break
        print("Queues cleared.")
        # *** END CORRECTION ***

        if self.model:
            print("Unloading model...")
            try:
                del self.model; self.model = None
                if torch.cuda.is_available(): print("Clearing CUDA cache..."); torch.cuda.empty_cache()
                print("Model unloaded.")
            except Exception as e: print(f"Error during model unload: {e}")

        self.recording = False; self.vad_active = False; self.audio_buffer = []
        print("Worker processing stopped."); self.status_updated.emit("Idle")

    # --- Internal Methods ---
    def _audio_callback(self, indata, frames, time, status):
        if status: error_msg = f"Audio Callback Error: {status}"; print(error_msg, file=sys.stderr)
        if self._is_running: self.audio_queue.put(bytes(indata))

    @Slot()
    def _check_audio_queue(self):
        # (Unchanged)
        if not self._is_running: return
        try:
            processed_chunk_count = 0; max_chunks_per_cycle = 5
            while not self.audio_queue.empty() and processed_chunk_count < max_chunks_per_cycle:
                raw_audio_chunk = self.audio_queue.get_nowait(); processed_chunk_count += 1
                try: chunk_np = np.frombuffer(raw_audio_chunk, dtype=np.int16); amplitude = np.abs(chunk_np).mean()
                except Exception as e: print(f"Error VAD chunk: {e}"); continue

                if self._ptt_active:
                    if not self.recording: self.status_updated.emit("Recording (PTT)..."); self.recording = True; self.vad_active = False; self.audio_buffer = []
                    self.audio_buffer.append(chunk_np); self.frames_since_speech = 0; continue
                elif self._vad_enabled:
                    if not self.recording:
                        if amplitude > self.silence_threshold: self.status_updated.emit("Recording (VAD)..."); self.recording = True; self.vad_active = True; self.audio_buffer = []; self.audio_buffer.append(chunk_np); self.frames_since_speech = 0
                    elif self.recording and self.vad_active:
                        if amplitude > self.silence_threshold: self.frames_since_speech = 0; self.audio_buffer.append(chunk_np)
                        else:
                            self.frames_since_speech += 1
                            if self.frames_since_speech > self.silence_frames: self.status_updated.emit("Transcribing (VAD)..."); self.recording = False; self.vad_active = False; self._process_audio_buffer()
        except queue.Empty: pass
        except Exception as e: error_msg = f"Audio check loop error: {e}"; print(error_msg); self.error_occurred.emit(error_msg)

    def _process_audio_buffer(self):
        # (Unchanged)
        if not self.audio_buffer: return
        buffer_copy = list(self.audio_buffer); self.audio_buffer = []
        try: audio_data = np.concatenate(buffer_copy); audio_float32 = audio_data.astype(np.float32) / 32768.0
        except ValueError: print("Error concatenating buffer copy."); return
        if audio_float32.size == 0: print("Concatenated audio empty."); return

        start_time = time.time(); transcribed_text = ""
        try:
            if not self.model: self.error_occurred.emit("Model not loaded."); return
            segments, info = self.model.transcribe(audio_float32, beam_size=5, language=self.language_code, temperature=0.0, condition_on_previous_text=False)
            transcribed_text = "".join(segment.text for segment in segments)
        except Exception as e: error_msg = f"Transcription error: {e}"; print(error_msg); self.error_occurred.emit(error_msg); return
        finally:
             if self._is_running and not self.recording and not self._ptt_active: self.status_updated.emit("Listening...")
        end_time = time.time()

        processed_text = transcribed_text.strip()
        if processed_text.lower() in self.filter_words: print(f"Filtered out phrase: '{processed_text}'"); return

        if processed_text:
            print(f"Transcribed: {processed_text} (Latency: {end_time - start_time:.2f}s)")
            self.transcription_ready.emit(processed_text)

            text_lower = processed_text.lower(); is_command = False
            if text_lower in self.new_line_commands: insert_new_line(); is_command = True
            if not is_command:
                punc_match = re.match(r"(question mark|exclamation mark|comma|period|full stop|colon|semicolon|open parenthesis|close parenthesis|open bracket|close bracket|open brace|close brace|hyphen|dash|underscore|plus|equals|at|hash|dollar|percent|caret|ampersand|asterisk)", text_lower)
                if punc_match: insert_punctuation(punc_match.group(1)); is_command = True
            if not is_command:
                cmd_match = re.match(r"(delete|remove) last (\d+|one|two|three|four|five|six|seven|eight|nine|ten) words?", text_lower)
                if cmd_match:
                    action, num_str = cmd_match.groups(); num = 0
                    if num_str.isdigit(): num = int(num_str)
                    else: w2n = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}; num = w2n.get(num_str, 0)
                    if action in ("delete", "remove") and num > 0:
                        if delete_last_n_words_direct(num): print(f"Deleted last {num} words.")
                    is_command = True

            if not is_command: self.text_queue.put(processed_text + " ")

    def _typing_loop(self):
        # (Unchanged)
        print("Typing thread started, ID:", threading.get_ident())
        import pythoncom
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
        try:
            import ctypes, time
            try: from pynput import keyboard; keyboard_controller = keyboard.Controller()
            except ImportError: print("ERROR: pynput not installed."); self.error_occurred.emit("pynput not installed."); return

            while self._is_running and not self.stop_typing_event.is_set():
                try:
                    text_to_type = self.text_queue.get(timeout=0.5)
                    try:
                        hwnd = ctypes.windll.user32.GetForegroundWindow()
                        if hwnd == self.gui_wid: print("Skipping typing: OmniDictate window active."); continue
                        for char in text_to_type:
                            if not self._is_running or self.stop_typing_event.is_set(): break
                            keyboard_controller.press(char)
                            keyboard_controller.release(char)
                            time.sleep(self.char_delay)
                    except Exception as e: error_msg = f"Error typing text: {e}"; print(error_msg); self.error_occurred.emit(error_msg)
                except queue.Empty: continue
                except Exception as e: error_msg = f"Typing queue error: {e}"; print(error_msg); self.error_occurred.emit(error_msg); time.sleep(0.1)
        finally:
            pythoncom.CoUninitialize()
            print("Typing thread exiting, ID:", threading.get_ident())