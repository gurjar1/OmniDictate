from __future__ import annotations

import argparse
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import librosa
import numpy as np
from PySide6.QtCore import QCoreApplication

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from app_settings import AppSettings
from core_logic import CHUNK_SIZE, DictationWorker, create_backend
from engines.context_capture import VisualContextManager
from live_typing_smoke import _close_notepad, _focus_notepad, _read_text, _save_notepad_file
from whisper_fixture_test import DEFAULT_PHRASE, assert_transcript_matches, synthesize_wav


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Drive the OmniDictate VAD -> Whisper -> typing loop with generated speech audio."
    )
    parser.add_argument("--model", default="tiny", help="Whisper model to load.")
    parser.add_argument("--language", default="en", help="Language code passed to Whisper.")
    parser.add_argument("--expected", default=DEFAULT_PHRASE, help="Expected text for the generated audio.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Seconds to wait for typed output.")
    parser.add_argument("--min-word-ratio", type=float, default=0.75, help="Minimum expected-word match ratio.")
    parser.add_argument("--keep-files", action="store_true", help="Keep generated audio and Notepad temp files.")
    return parser.parse_args()


def _drain_worker_queues(worker: DictationWorker) -> None:
    for target_queue in (worker.audio_queue, worker.request_queue, worker.text_queue):
        while True:
            try:
                target_queue.get_nowait()
            except queue.Empty:
                break


def _audio_to_chunks(audio: np.ndarray) -> list[np.ndarray]:
    speech = np.clip(audio, -1.0, 1.0)
    audio_i16 = (speech * 32767).astype(np.int16)
    trailing_silence = np.zeros(CHUNK_SIZE * 40, dtype=np.int16)
    combined = np.concatenate([audio_i16, trailing_silence])
    pad = (-combined.size) % CHUNK_SIZE
    if pad:
        combined = np.concatenate([combined, np.zeros(pad, dtype=np.int16)])
    return [combined[start : start + CHUNK_SIZE] for start in range(0, combined.size, CHUNK_SIZE)]


def _start_worker(worker: DictationWorker):
    worker.backend = create_backend(worker.app_settings)
    load_result = worker.backend.load()
    print(f"Backend status: {load_result.status_message}")
    for warning in load_result.warnings:
        print(f"Warning: {warning}")
    if not load_result.success:
        raise RuntimeError(load_result.status_message)

    _drain_worker_queues(worker)
    worker._is_running = True
    worker.recording = False
    worker.vad_active = False
    worker.frames_since_speech = 0
    worker.stop_inference_event.clear()
    worker.stop_typing_event.clear()

    inference_thread = threading.Thread(target=worker._inference_loop, daemon=True)
    typing_thread = threading.Thread(target=worker._typing_loop, daemon=True)
    inference_thread.start()
    typing_thread.start()
    return inference_thread, typing_thread


def _stop_worker(worker: DictationWorker, threads) -> None:
    worker._is_running = False
    worker.stop_inference_event.set()
    worker.stop_typing_event.set()
    for thread in threads:
        thread.join(timeout=2.0)
    if worker.backend is not None:
        worker.backend.unload()
        worker.backend = None


def main() -> int:
    args = parse_args()
    QCoreApplication.instance() or QCoreApplication([])

    audio_path = synthesize_wav(args.expected)
    audio, sample_rate = librosa.load(audio_path, sr=16000, mono=True)
    if sample_rate != 16000 or audio.size == 0:
        raise AssertionError(f"Invalid generated audio: sample_rate={sample_rate}, samples={audio.size}")

    notepad_path = Path(tempfile.gettempdir()) / f"omnidictate_full_loop_smoke_{int(time.time())}.txt"
    notepad_path.write_text("", encoding="utf-8")
    process = subprocess.Popen(["notepad.exe", str(notepad_path)])
    target_hwnd = 0

    settings = AppSettings(
        backend="faster-whisper",
        whisper_model=args.model,
        language=args.language,
        vad_enabled=True,
        silence_threshold=500,
        char_delay=0.02,
        screen_context_enabled=False,
        webcam_enabled=False,
    )
    worker = DictationWorker(
        gui_wid=0,
        app_settings=settings,
        visual_context_manager=VisualContextManager(settings),
    )
    route_event = threading.Event()
    original_route_text_output = worker._route_text_output

    def _route_text_output_and_signal(processed_text: str) -> None:
        original_route_text_output(processed_text)
        route_event.set()

    worker._route_text_output = _route_text_output_and_signal
    threads = ()

    try:
        target_hwnd = _focus_notepad(process.pid, notepad_path.name)
        threads = _start_worker(worker)

        for chunk in _audio_to_chunks(audio):
            worker.audio_queue.put_nowait(chunk.tobytes())
            worker._check_audio_queue()

        if not route_event.wait(timeout=args.timeout):
            raise AssertionError("Timed out waiting for worker transcription routing.")
        time.sleep(max(1.0, len(args.expected) * settings.char_delay + 0.75))

        deadline = time.time() + args.timeout
        typed_content = ""
        last_match_error: AssertionError | None = None
        while time.time() < deadline:
            _save_notepad_file()
            typed_content = _read_text(notepad_path)
            if typed_content.strip():
                try:
                    assert_transcript_matches(typed_content, args.expected, args.min_word_ratio)
                    print(f"Full synthetic loop smoke passed. File={notepad_path}")
                    return 0
                except AssertionError as exc:
                    last_match_error = exc
            time.sleep(0.5)

        if last_match_error is not None:
            raise AssertionError(f"Timed out waiting for a complete typed transcript: {last_match_error}") from last_match_error
        raise AssertionError("Timed out waiting for typed full-loop output.")
    finally:
        _stop_worker(worker, threads)
        if target_hwnd:
            _close_notepad(target_hwnd, process)
        elif process.poll() is None:
            process.terminate()
        if not args.keep_files:
            for path in (audio_path, notepad_path):
                try:
                    path.unlink()
                except OSError:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
