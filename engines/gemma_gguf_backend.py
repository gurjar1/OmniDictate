from __future__ import annotations

import base64
import io
from dataclasses import replace
import time

import numpy as np
from faster_whisper import WhisperModel
from PIL import Image

from .base import BackendLoadResult, ExecutionRoute, PromptMode, TranscriptionBackend, TranscriptionRequest, TranscriptionResult
from .prompt_modes import build_system_prompt, build_user_instruction, clean_gemma_response, parse_reasoning_output


class GemmaGGUFBackend(TranscriptionBackend):
    def __init__(self, app_settings):
        super().__init__(app_settings)
        self.whisper_frontend = None
        self.server_base_url = self._normalize_base_url(app_settings.gguf_server_url)
        self.server_model_name = (app_settings.gguf_model_name or "").strip()
        self.requests = None

    @staticmethod
    def _normalize_base_url(url: str) -> str:
        normalized = (url or "http://127.0.0.1:8080/v1").strip().rstrip("/")
        if normalized.endswith("/v1"):
            return normalized
        return normalized + "/v1"

    @staticmethod
    def _resolve_whisper_model_path(model_name: str) -> str:
        if model_name == "large-v3-turbo":
            return "deepdml/faster-whisper-large-v3-turbo-ct2"
        return model_name

    def _build_whisper_frontend(self, model_name: str):
        import torch

        model_path = self._resolve_whisper_model_path(model_name)
        use_cuda = torch.cuda.is_available()
        device = "cuda" if use_cuda else "cpu"
        compute_type = "float16" if use_cuda else "int8"
        warnings: list[str] = []
        try:
            model = WhisperModel(model_path, device=device, compute_type=compute_type, local_files_only=False)
            return model, device, compute_type, warnings
        except Exception as exc:
            if use_cuda and "float16" in str(exc).lower():
                warnings.append("Whisper frontend float16 unavailable. Using CUDA float32 fallback.")
                model = WhisperModel(model_path, device="cuda", compute_type="float32", local_files_only=False)
                return model, "cuda", "float32", warnings

            warnings.append(f"Whisper frontend GPU load failed: {exc}. Using CPU int8 fallback.")
            model = WhisperModel(model_path, device="cpu", compute_type="int8", local_files_only=False)
            return model, "cpu", "int8", warnings

    def _load_whisper_frontend(self) -> list[str]:
        whisper_model_name = getattr(self.app_settings, "gemma_hybrid_whisper_model", None) or self.app_settings.whisper_model or "small"
        self.whisper_frontend, device, compute_type, warnings = self._build_whisper_frontend(whisper_model_name)
        warnings.append(
            f"GGUF hybrid mode enabled. Faster-Whisper '{whisper_model_name}' will produce the draft transcript before the local GGUF server refines it using {device} ({compute_type})."
        )
        return warnings

    def _resolve_server_model(self, warnings: list[str]) -> str:
        configured_model = (self.app_settings.gguf_model_name or "").strip()
        models_url = f"{self.server_base_url}/models"
        try:
            response = self.requests.get(models_url, timeout=10)
            response.raise_for_status()
            payload = response.json()
            model_entries = payload.get("data") or []
            model_ids = [str(entry.get("id", "")).strip() for entry in model_entries if str(entry.get("id", "")).strip()]
            if configured_model:
                if model_ids and configured_model not in model_ids:
                    warnings.append(
                        f"Configured GGUF model '{configured_model}' was not listed by the server. The request will still use it directly."
                    )
                return configured_model

            if model_ids:
                selected_model = model_ids[0]
                if len(model_ids) > 1:
                    warnings.append(
                        f"No GGUF model name was configured. Auto-selecting '{selected_model}' from the server model list."
                    )
                else:
                    warnings.append(f"GGUF server model auto-selected: '{selected_model}'.")
                return selected_model
        except Exception as exc:
            if configured_model:
                warnings.append(
                    f"Could not list models from the GGUF server: {exc}. Using configured model '{configured_model}' directly."
                )
                return configured_model
            raise RuntimeError(
                f"Could not reach the GGUF server at {models_url}. Start llama-server or another OpenAI-compatible local server first."
            ) from exc

        raise RuntimeError(
            "The GGUF server did not return any models. Configure a model name explicitly or start the server with a loaded multimodal model."
        )

    def load(self) -> BackendLoadResult:
        warnings: list[str] = []
        try:
            import requests

            self.requests = requests
            self.server_base_url = self._normalize_base_url(self.app_settings.gguf_server_url)
            warnings.extend(self._load_whisper_frontend())
            self.server_model_name = self._resolve_server_model(warnings)
            self._is_loaded = True
            return BackendLoadResult(
                True,
                f"Gemma GGUF server backend ready at '{self.server_base_url}' using model '{self.server_model_name}'.",
                warnings,
            )
        except Exception as exc:
            self.whisper_frontend = None
            self.requests = None
            self._is_loaded = False
            return BackendLoadResult(False, f"Error loading Gemma GGUF server backend: {exc}", warnings)

    def unload(self) -> None:
        if self.whisper_frontend is not None:
            del self.whisper_frontend
            self.whisper_frontend = None
        self.requests = None
        self._is_loaded = False

    def _transcribe_with_whisper_frontend(self, request: TranscriptionRequest) -> str:
        if self.whisper_frontend is None:
            raise RuntimeError("Hybrid Faster-Whisper frontend is not loaded.")

        audio = request.audio.astype(np.float32, copy=False)
        segments, _ = self.whisper_frontend.transcribe(
            audio,
            beam_size=5,
            language=request.language,
            temperature=0.0,
            condition_on_previous_text=False,
        )
        return "".join(segment.text for segment in segments).strip()

    def _prepare_visual_inputs(self, request: TranscriptionRequest):
        images = list(request.visual_context.images) + list(request.visual_context.video_frames)
        if not images:
            return images

        budget = int(getattr(self.app_settings, "image_token_budget", 140) or 140)
        max_dimension = {
            70: 384,
            140: 512,
            280: 768,
        }.get(budget, 512)

        prepared_images = []
        for image in images:
            if not isinstance(image, Image.Image):
                prepared_images.append(image)
                continue

            prepared_image = image.convert("RGB")
            if max(prepared_image.size) > max_dimension:
                prepared_image = prepared_image.copy()
                prepared_image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            prepared_images.append(prepared_image)
        return prepared_images

    @staticmethod
    def _encode_image_as_data_url(image: Image.Image) -> str:
        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")
        encoded = base64.b64encode(image_buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _build_chat_messages(self, request: TranscriptionRequest) -> list[dict]:
        content: list[dict] = []
        for image in self._prepare_visual_inputs(request):
            if isinstance(image, Image.Image):
                content.append({
                    "type": "image_url",
                    "image_url": {"url": self._encode_image_as_data_url(image)},
                })
        content.append({"type": "text", "text": build_user_instruction(request)})
        return [
            {"role": "system", "content": build_system_prompt(request)},
            {"role": "user", "content": content},
        ]

    def _post_chat_completion(self, request: TranscriptionRequest) -> str:
        payload = {
            "model": self.server_model_name,
            "messages": self._build_chat_messages(request),
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": request.max_new_tokens,
            "stream": False,
        }
        response = self.requests.post(
            f"{self.server_base_url}/chat/completions",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("GGUF server returned no completion choices.")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
            content = "\n".join(part for part in text_parts if part)
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("GGUF server returned an empty completion.")
        return content

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        if self.whisper_frontend is None or self.requests is None:
            raise RuntimeError("Gemma GGUF server backend is not loaded.")

        started = time.time()
        transcript = clean_gemma_response(self._transcribe_with_whisper_frontend(request))
        if request.prompt_mode == PromptMode.PURE:
            latency = time.time() - started
            return TranscriptionResult(
                text=transcript,
                raw_text=transcript,
                prompt_mode=request.prompt_mode,
                used_visual_context=False,
                latency_seconds=latency,
                execution_route=ExecutionRoute.WHISPER_ONLY,
            )
        if request.prompt_mode == PromptMode.CONTEXT and request.visual_context.is_empty:
            latency = time.time() - started
            return TranscriptionResult(
                text=transcript,
                raw_text=transcript,
                prompt_mode=request.prompt_mode,
                used_visual_context=False,
                latency_seconds=latency,
                execution_route=ExecutionRoute.WHISPER_ONLY,
            )

        effective_request = replace(request, transcript_text=transcript)
        decoded = clean_gemma_response(self._post_chat_completion(effective_request))
        latency = time.time() - started

        if effective_request.prompt_mode == PromptMode.REASONING:
            preview = parse_reasoning_output(decoded)
            return TranscriptionResult(
                text=preview.typed_text,
                raw_text=decoded,
                prompt_mode=effective_request.prompt_mode,
                used_visual_context=not effective_request.visual_context.is_empty,
                latency_seconds=latency,
                execution_route=ExecutionRoute.GGUF_SERVER_REFINEMENT,
                requires_confirmation=self.app_settings.reasoning_requires_preview,
                preview=preview,
            )

        return TranscriptionResult(
            text=decoded,
            raw_text=decoded,
            prompt_mode=effective_request.prompt_mode,
            used_visual_context=not effective_request.visual_context.is_empty,
            latency_seconds=latency,
            execution_route=ExecutionRoute.GGUF_SERVER_REFINEMENT,
        )