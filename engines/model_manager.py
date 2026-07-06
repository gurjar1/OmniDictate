from __future__ import annotations

import os
from pathlib import Path

import torch


class ModelManager:
    def __init__(self, app_settings):
        self.app_settings = app_settings

    @staticmethod
    def _preferred_cuda_dtype():
        if torch.cuda.is_available() and hasattr(torch.cuda, "is_bf16_supported") and torch.cuda.is_bf16_supported():
            return torch.bfloat16
        if torch.cuda.is_available():
            return torch.float16
        return torch.float32

    def resolve_model_reference(self) -> str:
        configured_path = (self.app_settings.model_storage_path or "").strip()
        if configured_path:
            local_candidate = Path(configured_path) / self.app_settings.gemma_model.rsplit("/", 1)[-1]
            if local_candidate.exists():
                return str(local_candidate)
        return self.app_settings.gemma_model

    def build_model_kwargs(self) -> tuple[dict, list[str]]:
        warnings: list[str] = []
        hybrid_mode = getattr(self.app_settings, "gemma_audio_input_mode", "hybrid-whisper") == "hybrid-whisper"
        kwargs: dict = {
            "device_map": {"": 0} if torch.cuda.is_available() and hybrid_mode else ("auto" if torch.cuda.is_available() else None),
        }

        quantization = (self.app_settings.gemma_quantization or "").lower()
        audio_multimodal_model = (
            self.app_settings.gemma_model.rsplit("/", 1)[-1] in {"gemma-4-E2B-it", "gemma-4-E4B-it"}
            and getattr(self.app_settings, "gemma_audio_input_mode", "hybrid-whisper") == "native-audio"
        )
        if quantization in {"4-bit", "8-bit"} and audio_multimodal_model:
            warnings.append(
                "Quantized loading is temporarily disabled for Gemma audio multimodal inference because the current "
                "bitsandbytes path crashes during generation. Falling back to dtype loading."
            )
        elif quantization in {"4-bit", "8-bit"}:
            try:
                from transformers import BitsAndBytesConfig

                if quantization == "4-bit":
                    kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=self._preferred_cuda_dtype(),
                    )
                else:
                    kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
            except Exception as exc:
                warnings.append(f"Quantization backend unavailable: {exc}. Falling back to dtype loading.")

        if "quantization_config" not in kwargs:
            kwargs["dtype"] = self._preferred_cuda_dtype()

        kwargs["local_files_only"] = False
        return kwargs, warnings

    def ensure_model_storage_path(self) -> str:
        path = self.app_settings.model_storage_path
        if path:
            os.makedirs(path, exist_ok=True)
        return path
