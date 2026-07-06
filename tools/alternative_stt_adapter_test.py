from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.base import ExecutionRoute, PromptMode, TargetAppContext, TranscriptionRequest, VisualContextSnapshot
from engines.transformers_asr_backend import TransformersASRBackend
from whisper_fixture_test import DEFAULT_PHRASE, assert_transcript_matches


class _FakePipeline:
    def __init__(self):
        self.calls = []

    def __call__(self, payload):
        self.calls.append(payload)
        return {"text": DEFAULT_PHRASE}


def _pipeline_factory(task: str, model: str, device: int):
    assert task == "automatic-speech-recognition"
    assert model == "UsefulSensors/moonshine-tiny"
    assert device in {-1, 0}
    return _FakePipeline()


def main() -> int:
    settings = AppSettings(backend="transformers-asr", alternative_stt_model="UsefulSensors/moonshine-tiny")
    backend = TransformersASRBackend(settings, pipeline_factory=_pipeline_factory)
    load_result = backend.load()
    if not load_result.success:
        raise AssertionError(load_result.status_message)

    audio = np.zeros(16000, dtype=np.float32)
    request = TranscriptionRequest(
        audio=audio,
        sample_rate=16000,
        language="en",
        prompt_mode=PromptMode.PURE,
        visual_context=VisualContextSnapshot(),
        target_app=TargetAppContext(title="Alternative STT adapter test"),
    )
    result = backend.transcribe(request)
    if result.execution_route != ExecutionRoute.ALTERNATIVE_STT:
        raise AssertionError(f"Unexpected route: {result.execution_route}")
    assert_transcript_matches(result.text, DEFAULT_PHRASE, 1.0)
    backend.unload()
    print("Alternative STT adapter test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
