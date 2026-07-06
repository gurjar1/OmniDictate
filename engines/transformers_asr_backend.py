from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import numpy as np

from .base import BackendLoadResult, ExecutionRoute, PromptMode, TranscriptionBackend, TranscriptionRequest, TranscriptionResult


class TransformersASRBackend(TranscriptionBackend):
    """Optional adapter for Hugging Face Transformers ASR models such as Moonshine."""

    def __init__(self, app_settings, pipeline_factory: Callable[..., Any] | None = None):
        super().__init__(app_settings)
        self.pipeline_factory = pipeline_factory
        self.pipeline = None

    def load(self) -> BackendLoadResult:
        model_name = self.app_settings.alternative_stt_model
        warnings: list[str] = []
        try:
            factory = self.pipeline_factory
            if factory is None:
                from transformers import pipeline

                factory = pipeline
            self.pipeline = factory(
                "automatic-speech-recognition",
                model=model_name,
                device=0 if self._cuda_available() else -1,
            )
            self._is_loaded = True
            return BackendLoadResult(True, f"Transformers ASR model '{model_name}' loaded.", warnings)
        except Exception as exc:
            self.pipeline = None
            self._is_loaded = False
            return BackendLoadResult(False, f"Error loading Transformers ASR model '{model_name}': {exc}", warnings)

    def unload(self) -> None:
        self.pipeline = None
        self._is_loaded = False

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        if self.pipeline is None:
            raise RuntimeError("Transformers ASR backend is not loaded.")

        started = time.time()
        audio = request.audio.astype(np.float32, copy=False)
        output = self.pipeline({"array": audio, "sampling_rate": request.sample_rate})
        text = self._extract_text(output)
        latency = time.time() - started
        return TranscriptionResult(
            text=text,
            raw_text=text,
            prompt_mode=PromptMode(request.prompt_mode),
            used_visual_context=False,
            latency_seconds=latency,
            execution_route=ExecutionRoute.ALTERNATIVE_STT,
        )

    @staticmethod
    def _extract_text(output: Any) -> str:
        if isinstance(output, dict):
            return str(output.get("text", "")).strip()
        if isinstance(output, list):
            return " ".join(TransformersASRBackend._extract_text(item) for item in output).strip()
        return str(output).strip()

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False
