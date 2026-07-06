from __future__ import annotations

from dataclasses import replace
import time

import numpy as np
import torch
from faster_whisper import WhisperModel
from PIL import Image

from .base import BackendLoadResult, ExecutionRoute, PromptMode, TranscriptionBackend, TranscriptionRequest, TranscriptionResult
from .model_manager import ModelManager
from .prompt_modes import build_gemma_messages, clean_gemma_response, parse_reasoning_output


class Gemma4Backend(TranscriptionBackend):
    def __init__(self, app_settings):
        super().__init__(app_settings)
        self.model = None
        self.processor = None
        self.whisper_frontend = None
        self.model_manager = ModelManager(app_settings)

    @staticmethod
    def _resolve_whisper_model_path(model_name: str) -> str:
        if model_name == "large-v3-turbo":
            return "deepdml/faster-whisper-large-v3-turbo-ct2"
        return model_name

    @staticmethod
    def _describe_device_map(model) -> str:
        device_map = getattr(model, "hf_device_map", None)
        if isinstance(device_map, dict) and device_map:
            counts: dict[str, int] = {}
            for destination in device_map.values():
                label = str(destination)
                counts[label] = counts.get(label, 0) + 1
            return ", ".join(f"{label} x{count}" for label, count in sorted(counts.items()))

        try:
            return str(next(model.parameters()).device)
        except Exception:
            return "unknown"

    def _build_whisper_frontend(self, model_name: str):
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
        warnings: list[str] = []
        if self.app_settings.gemma_audio_input_mode != "hybrid-whisper":
            return warnings

        whisper_model_name = getattr(self.app_settings, "gemma_hybrid_whisper_model", None) or self.app_settings.whisper_model or "small"
        self.whisper_frontend, device, compute_type, frontend_warnings = self._build_whisper_frontend(whisper_model_name)
        warnings.extend(frontend_warnings)
        warnings.append(
            f"Hybrid audio mode enabled. Faster-Whisper '{whisper_model_name}' will produce the draft transcript before Gemma refinement using {device} ({compute_type})."
        )
        return warnings

    def _load_transformers_model(self, model_reference: str, kwargs: dict, warnings: list[str], model_cls):
        try:
            return model_cls.from_pretrained(
                model_reference,
                cache_dir=self.app_settings.model_storage_path,
                **kwargs,
            )
        except Exception as exc:
            if kwargs.get("device_map") == {"": 0}:
                fallback_kwargs = dict(kwargs)
                fallback_kwargs["device_map"] = "auto"
                warnings.append(f"Forced full-GPU load failed: {exc}. Retrying with automatic device mapping.")
                return model_cls.from_pretrained(
                    model_reference,
                    cache_dir=self.app_settings.model_storage_path,
                    **fallback_kwargs,
                )
            raise

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

    def load(self) -> BackendLoadResult:
        warnings: list[str] = []
        try:
            from transformers import AutoProcessor

            try:
                from transformers import AutoModelForMultimodalLM
            except ImportError:
                from transformers import AutoModelForImageTextToText as AutoModelForMultimodalLM

            model_reference = self.model_manager.resolve_model_reference()
            self.model_manager.ensure_model_storage_path()
            kwargs, manager_warnings = self.model_manager.build_model_kwargs()
            warnings.extend(manager_warnings)

            if kwargs.get("device_map") is None:
                kwargs.pop("device_map")

            self.processor = AutoProcessor.from_pretrained(
                model_reference,
                cache_dir=self.app_settings.model_storage_path,
            )
            self.model = self._load_transformers_model(model_reference, kwargs, warnings, AutoModelForMultimodalLM)
            self.model.eval()
            if getattr(self.model, "generation_config", None) is not None:
                self.model.generation_config.top_p = None
                self.model.generation_config.top_k = None
            warnings.extend(self._load_whisper_frontend())
            warnings.append(f"Gemma device map: {self._describe_device_map(self.model)}")
            self._is_loaded = True
            quantization = self.app_settings.gemma_quantization or "auto"
            if "quantization_config" not in kwargs and quantization in {"4-bit", "8-bit"}:
                quantization = f"dtype fallback from {quantization}"
            return BackendLoadResult(
                True,
                f"Gemma model '{model_reference}' loaded ({quantization}).",
                warnings,
            )
        except Exception as exc:
            self.model = None
            self.processor = None
            self._is_loaded = False
            return BackendLoadResult(False, f"Error loading Gemma model: {exc}", warnings)

    def unload(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
        if self.whisper_frontend is not None:
            del self.whisper_frontend
            self.whisper_frontend = None
        self.processor = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self._is_loaded = False

    def _prepare_inputs(self, request: TranscriptionRequest):
        messages = build_gemma_messages(request)
        enable_thinking = request.prompt_mode == PromptMode.REASONING and request.enable_thinking
        prompt_text = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=enable_thinking,
        )

        images = self._prepare_visual_inputs(request)
        processor_kwargs = {
            "text": prompt_text,
            "return_tensors": "pt",
        }
        if request.transcript_text is None:
            audio = np.expand_dims(request.audio.astype(np.float32, copy=False), axis=0)
            processor_kwargs["audio"] = audio
        if images:
            processor_kwargs["images"] = images

        inputs = self.processor(**processor_kwargs)
        model_device = getattr(self.model, "device", None)
        if model_device is not None:
            inputs = inputs.to(model_device)
        return inputs

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

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        if self.model is None or self.processor is None:
            raise RuntimeError("Gemma backend is not loaded.")

        started = time.time()
        effective_request = request
        if self.app_settings.gemma_audio_input_mode == "hybrid-whisper":
            transcript = self._transcribe_with_whisper_frontend(request)
            transcript = clean_gemma_response(transcript)
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

        execution_route = (
            ExecutionRoute.GEMMA_HYBRID_REFINEMENT
            if self.app_settings.gemma_audio_input_mode == "hybrid-whisper"
            else ExecutionRoute.GEMMA_NATIVE_AUDIO
        )

        inputs = self._prepare_inputs(effective_request)
        input_len = inputs["input_ids"].shape[-1]
        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=effective_request.max_new_tokens,
                do_sample=False,
            )

        decoded = clean_gemma_response(
            self.processor.decode(
                output_ids[0][input_len:],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )
        )
        latency = time.time() - started

        if effective_request.prompt_mode == PromptMode.REASONING:
            preview = parse_reasoning_output(decoded)
            return TranscriptionResult(
                text=preview.typed_text,
                raw_text=decoded,
                prompt_mode=effective_request.prompt_mode,
                used_visual_context=not effective_request.visual_context.is_empty,
                latency_seconds=latency,
                execution_route=execution_route,
                requires_confirmation=self.app_settings.reasoning_requires_preview,
                preview=preview,
            )

        return TranscriptionResult(
            text=decoded,
            raw_text=decoded,
            prompt_mode=effective_request.prompt_mode,
            used_visual_context=not effective_request.visual_context.is_empty,
            latency_seconds=latency,
            execution_route=execution_route,
        )
