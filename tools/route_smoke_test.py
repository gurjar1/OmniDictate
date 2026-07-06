from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.base import ExecutionRoute, PromptMode, TargetAppContext, TranscriptionRequest, VisualContextSnapshot, VisualSource
from engines.gemma4_backend import Gemma4Backend
from engines.gemma_gguf_backend import GemmaGGUFBackend
from engines.whisper_backend import WhisperBackend


class _FakeSegment:
    def __init__(self, text: str):
        self.text = text


class _FakeWhisperModel:
    def transcribe(self, _audio, **_kwargs):
        return [ _FakeSegment(" draft from whisper ") ], None


class _FakeModel:
    def generate(self, **_kwargs):
        return np.array([[11, 12, 13, 14]])


class _FakeProcessor:
    def decode(self, _tokens, **_kwargs):
        return " refined route output "


def _build_request(prompt_mode: PromptMode, include_visual: bool = False) -> TranscriptionRequest:
    visual_context = VisualContextSnapshot()
    if include_visual:
        visual_context = VisualContextSnapshot(
            source=VisualSource.ATTACHED_IMAGE,
            images=[object()],
            description="Images: sample.png",
        )

    return TranscriptionRequest(
        audio=np.zeros(16000, dtype=np.float32),
        sample_rate=16000,
        language=None,
        prompt_mode=prompt_mode,
        visual_context=visual_context,
        target_app=TargetAppContext(title="Route Smoke Test", process_name="unittest"),
        enable_thinking=False,
        max_new_tokens=32,
    )


class RouteSmokeTest(unittest.TestCase):
    def test_whisper_backend_reports_whisper_only(self):
        backend = WhisperBackend(AppSettings(backend="faster-whisper", whisper_model="small"))
        backend.model = _FakeWhisperModel()

        result = backend.transcribe(_build_request(PromptMode.PURE))

        self.assertEqual(result.execution_route, ExecutionRoute.WHISPER_ONLY)

    def test_gemma_hybrid_reports_hybrid_refinement(self):
        backend = Gemma4Backend(AppSettings(backend="gemma-4", gemma_audio_input_mode="hybrid-whisper"))
        backend.model = _FakeModel()
        backend.processor = _FakeProcessor()
        backend._transcribe_with_whisper_frontend = lambda _request: "draft transcript"
        backend._prepare_inputs = lambda _request: {"input_ids": np.array([[1, 2]])}

        result = backend.transcribe(_build_request(PromptMode.CONTEXT, include_visual=True))

        self.assertEqual(result.execution_route, ExecutionRoute.GEMMA_HYBRID_REFINEMENT)

    def test_gemma_native_reports_native_audio(self):
        backend = Gemma4Backend(AppSettings(backend="gemma-4", gemma_audio_input_mode="native-audio"))
        backend.model = _FakeModel()
        backend.processor = _FakeProcessor()
        backend._prepare_inputs = lambda _request: {"input_ids": np.array([[1, 2]])}

        result = backend.transcribe(_build_request(PromptMode.CONTEXT, include_visual=True))

        self.assertEqual(result.execution_route, ExecutionRoute.GEMMA_NATIVE_AUDIO)

    def test_gguf_backend_reports_server_refinement(self):
        backend = GemmaGGUFBackend(AppSettings(backend="gemma-gguf-server"))
        backend.whisper_frontend = object()
        backend.requests = object()
        backend._transcribe_with_whisper_frontend = lambda _request: "draft transcript"
        backend._post_chat_completion = lambda _request: "server refinement"

        result = backend.transcribe(_build_request(PromptMode.CONTEXT, include_visual=True))

        self.assertEqual(result.execution_route, ExecutionRoute.GGUF_SERVER_REFINEMENT)


if __name__ == "__main__":
    unittest.main(verbosity=2)