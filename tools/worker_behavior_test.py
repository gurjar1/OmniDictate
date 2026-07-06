from __future__ import annotations

import queue
import sys
import unittest
from pathlib import Path

import numpy as np
from PySide6.QtCore import QCoreApplication

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from core_logic import CHUNK_SIZE, SAMPLE_RATE, DictationWorker
from engines.base import PromptMode, TargetAppContext, TranscriptionRequest, TranscriptionResult, VisualContextSnapshot
from engines.context_capture import VisualContextManager


def _ensure_qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def _build_worker() -> DictationWorker:
    _ensure_qt_app()
    settings = AppSettings(
        backend="faster-whisper",
        whisper_model="tiny",
        filter_words=["ignore me"],
        silence_threshold=500,
        char_delay=0.0,
        min_ptt_duration_ms=0,
    )
    return DictationWorker(
        gui_wid=1001,
        app_settings=settings,
        visual_context_manager=VisualContextManager(settings),
    )


def _fake_request(audio: np.ndarray) -> TranscriptionRequest:
    return TranscriptionRequest(
        audio=audio,
        sample_rate=SAMPLE_RATE,
        language="en",
        prompt_mode=PromptMode.PURE,
        visual_context=VisualContextSnapshot(),
        target_app=TargetAppContext(title="Worker behavior test", process_name="unittest"),
    )


def _result(text: str) -> TranscriptionResult:
    return TranscriptionResult(
        text=text,
        raw_text=text,
        prompt_mode=PromptMode.PURE,
        used_visual_context=False,
        latency_seconds=0.01,
    )


class _FakeKeyboard:
    def __init__(self):
        self.events: list[tuple[str, str]] = []

    def press(self, char: str):
        self.events.append(("press", char))

    def release(self, char: str):
        self.events.append(("release", char))


class WorkerBehaviorTest(unittest.TestCase):
    def test_punctuation_command_routes_to_character(self):
        worker = _build_worker()

        worker._handle_transcription_result(_result("comma"))

        self.assertEqual(worker.text_queue.get_nowait(), ",")

    def test_filter_word_is_not_queued_for_typing(self):
        worker = _build_worker()

        worker._handle_transcription_result(_result("ignore me"))

        with self.assertRaises(queue.Empty):
            worker.text_queue.get_nowait()

    def test_normal_text_gets_trailing_space_for_typing(self):
        worker = _build_worker()

        worker._handle_transcription_result(_result("hello world"))

        self.assertEqual(worker.text_queue.get_nowait(), "hello world ")

    def test_transcribe_only_mode_does_not_queue_typing(self):
        worker = _build_worker()
        worker.type_into_active_app = False

        worker._handle_transcription_result(_result("hello world"))

        with self.assertRaises(queue.Empty):
            worker.text_queue.get_nowait()

    def test_ptt_release_queues_transcription_request(self):
        worker = _build_worker()
        worker._is_running = True
        worker._build_transcription_request = _fake_request
        speech = (np.ones(CHUNK_SIZE, dtype=np.int16) * 1200).tobytes()

        worker.set_ptt_state(True)
        worker.audio_queue.put_nowait(speech)
        worker._check_audio_queue()
        worker.set_ptt_state(False)

        self.assertFalse(worker.request_queue.empty())

    def test_short_ptt_tap_is_ignored(self):
        worker = _build_worker()
        worker.min_ptt_duration_seconds = 0.5
        worker._is_running = True
        worker._build_transcription_request = _fake_request
        worker.recording = True
        worker.vad_active = False
        worker.audio_buffer = [np.ones(CHUNK_SIZE, dtype=np.int16) * 1200]

        worker.set_ptt_state(True)
        worker.set_ptt_state(False)

        self.assertTrue(worker.request_queue.empty())
        self.assertEqual(worker.audio_buffer, [])

    def test_vad_silence_after_speech_queues_transcription_request(self):
        worker = _build_worker()
        worker._is_running = True
        worker._build_transcription_request = _fake_request
        worker.recording = True
        worker.vad_active = True
        worker.frames_since_speech = worker.silence_frames
        worker.audio_buffer = [np.ones(CHUNK_SIZE, dtype=np.int16) * 1200]
        silence = np.zeros(CHUNK_SIZE, dtype=np.int16).tobytes()

        worker.audio_queue.put_nowait(silence)
        worker._check_audio_queue()

        self.assertFalse(worker.recording)
        self.assertFalse(worker.vad_active)
        self.assertFalse(worker.request_queue.empty())

    def test_typing_guard_does_not_type_into_own_window(self):
        worker = _build_worker()
        worker._is_running = True
        fake_keyboard = _FakeKeyboard()

        typed = worker._type_pending_text(fake_keyboard, "abc", foreground_hwnd=worker.gui_wid)

        self.assertFalse(typed)
        self.assertEqual(fake_keyboard.events, [])

    def test_own_window_focus_discards_pending_typing_history(self):
        worker = _build_worker()
        worker.text_queue.put("older words ")

        discarded = worker._discard_text_if_own_window("new words ", foreground_hwnd=worker.gui_wid)

        self.assertTrue(discarded)
        with self.assertRaises(queue.Empty):
            worker.text_queue.get_nowait()

    def test_other_window_focus_keeps_pending_typing_history(self):
        worker = _build_worker()
        worker.text_queue.put("older words ")

        discarded = worker._discard_text_if_own_window("new words ", foreground_hwnd=worker.gui_wid + 1)

        self.assertFalse(discarded)
        self.assertEqual(worker.text_queue.get_nowait(), "older words ")

    def test_typing_guard_allows_other_target_window(self):
        worker = _build_worker()
        worker._is_running = True
        fake_keyboard = _FakeKeyboard()

        typed = worker._type_pending_text(fake_keyboard, "ab", foreground_hwnd=worker.gui_wid + 1)

        self.assertTrue(typed)
        self.assertEqual(
            fake_keyboard.events,
            [("press", "a"), ("release", "a"), ("press", "b"), ("release", "b")],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
