from __future__ import annotations

import time

import numpy as np

from .base import BackendLoadResult, ExecutionRoute, PromptMode, TranscriptionBackend, TranscriptionRequest, TranscriptionResult
from .runtime_detection import ctranslate2_supported_compute_types, empty_torch_cuda_cache, whisper_cuda_is_available


class WhisperBackend(TranscriptionBackend):
    def __init__(self, app_settings):
        super().__init__(app_settings)
        self.model = None

    def load(self) -> BackendLoadResult:
        model_name = self.app_settings.whisper_model
        model_path = model_name
        if model_name == "large-v3-turbo":
            model_path = "deepdml/faster-whisper-large-v3-turbo-ct2"

        warnings: list[str] = []
        try:
            from faster_whisper import WhisperModel

            use_cuda = whisper_cuda_is_available()
            device = "cuda" if use_cuda else "cpu"
            compute_type = "float16" if use_cuda else "int8"
            loaded_device = device
            loaded_compute_type = compute_type
            try:
                self.model = WhisperModel(model_path, device=device, compute_type=compute_type, local_files_only=False)
            except Exception as exc:
                if use_cuda and "float16" in str(exc):
                    warnings.append("CUDA float16 unavailable. Using float32 fallback.")
                    self.model = WhisperModel(model_path, device="cuda", compute_type="float32", local_files_only=False)
                    loaded_device = "cuda"
                    loaded_compute_type = "float32"
                else:
                    warnings.append(f"Primary Whisper load failed: {exc}. Using CPU int8 fallback.")
                    self.model = WhisperModel(model_path, device="cpu", compute_type="int8", local_files_only=False)
                    loaded_device = "cpu"
                    loaded_compute_type = "int8"
            self._is_loaded = True
            if use_cuda:
                cuda_types = sorted(ctranslate2_supported_compute_types("cuda"))
                if cuda_types:
                    warnings.append(f"CTranslate2 CUDA compute types: {', '.join(cuda_types)}.")
            return BackendLoadResult(
                True,
                f"Whisper model '{model_name}' loaded on {loaded_device} ({loaded_compute_type}).",
                warnings,
            )
        except Exception as exc:
            self.model = None
            self._is_loaded = False
            return BackendLoadResult(False, f"Error loading Whisper model: {exc}", warnings)

    def unload(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
        empty_torch_cuda_cache()
        self._is_loaded = False

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        if self.model is None:
            raise RuntimeError("Whisper backend is not loaded.")

        started = time.time()
        audio = request.audio.astype(np.float32, copy=False)
        segments, _ = self.model.transcribe(
            audio,
            beam_size=5,
            language=request.language,
            temperature=0.0,
            condition_on_previous_text=False,
        )
        text = "".join(segment.text for segment in segments).strip()
        latency = time.time() - started
        return TranscriptionResult(
            text=text,
            raw_text=text,
            prompt_mode=PromptMode(request.prompt_mode),
            used_visual_context=False,
            latency_seconds=latency,
            execution_route=ExecutionRoute.WHISPER_ONLY,
        )
