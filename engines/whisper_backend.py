from __future__ import annotations

import re
import time

import numpy as np

from .base import (
    BackendLoadResult,
    ExecutionRoute,
    PromptMode,
    RuntimeAction,
    RuntimeDiagnostics,
    TranscriptionBackend,
    TranscriptionRequest,
    TranscriptionResult,
)
from .runtime_detection import (
    ctranslate2_runtime_probe,
    ctranslate2_supported_compute_types,
    empty_torch_cuda_cache,
    whisper_cuda_is_available,
)


NVIDIA_DRIVER_URL = "https://www.nvidia.com/en-us/drivers/"
CUDA_TOOLKIT_URL = "https://developer.nvidia.com/cuda-toolkit-archive"
CUDNN_ARCHIVE_URL = "https://developer.nvidia.com/rdp/cudnn-archive"
VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"


def _runtime_requirement_hint(ctranslate2_version: str) -> str:
    match = re.match(r"^(\d+)\.(\d+)", ctranslate2_version or "")
    if not match:
        return "Use the GPU runtime versions recommended in the OmniDictate release notes."

    major = int(match.group(1))
    minor = int(match.group(2))
    if major > 4 or (major == 4 and minor >= 5):
        return "This OmniDictate build usually needs CUDA 12 and cuDNN 9 for GPU mode."
    if major == 4:
        return "This OmniDictate build usually needs CUDA 12 and cuDNN 8 for GPU mode."
    return "This OmniDictate build usually needs CUDA 11 and cuDNN 8 for GPU mode."


def _runtime_actions() -> list[RuntimeAction]:
    return [
        RuntimeAction("Open NVIDIA driver downloads", NVIDIA_DRIVER_URL),
        RuntimeAction("Open CUDA Toolkit archive", CUDA_TOOLKIT_URL),
        RuntimeAction("Open cuDNN archive", CUDNN_ARCHIVE_URL),
        RuntimeAction("Download Microsoft VC++ Redistributable x64", VC_REDIST_URL),
    ]


def _build_runtime_diagnostics(
    *,
    model_name: str,
    loaded_device: str,
    loaded_compute_type: str,
    warnings: list[str],
    primary_error: str = "",
    load_error: str = "",
) -> RuntimeDiagnostics:
    probe = ctranslate2_runtime_probe()
    ctranslate2_version = str(probe.get("version") or "")
    requirement_hint = _runtime_requirement_hint(ctranslate2_version)
    technical_details = [
        f"Whisper model: {model_name}",
        f"CTranslate2 version: {ctranslate2_version or 'unknown'}",
        f"CTranslate2 CUDA devices: {probe.get('cuda_device_count', 0)}",
    ]
    supported_types = probe.get("supported_compute_types") or []
    if supported_types:
        technical_details.append(f"CTranslate2 CUDA compute types: {', '.join(supported_types)}")
    if probe.get("error"):
        technical_details.append(str(probe["error"]))
    if primary_error:
        technical_details.append(f"GPU load attempt: {primary_error}")
    if load_error:
        technical_details.append(f"Load error: {load_error}")
    technical_details.extend(warnings)

    if load_error:
        return RuntimeDiagnostics(
            status="error",
            headline="Whisper could not start",
            summary=(
                "OmniDictate could not load the speech model. This is often caused by a missing "
                "Windows runtime, a blocked model download, or an incomplete GPU runtime."
            ),
            next_steps=[
                "Restart OmniDictate and try once more.",
                "If Windows mentions a missing DLL, install the Microsoft VC++ Redistributable x64.",
                "If the message mentions CUDA or cuDNN, install the NVIDIA driver first, then the matching CUDA/cuDNN runtime.",
                "If the model was downloading, check internet access and try again.",
            ],
            technical_details=technical_details,
            actions=_runtime_actions(),
        )

    if loaded_device == "cuda" and loaded_compute_type == "float16":
        return RuntimeDiagnostics(
            status="gpu-ready",
            headline="GPU acceleration is working",
            summary="OmniDictate is using your NVIDIA GPU for faster Whisper transcription.",
            device=loaded_device,
            compute_type=loaded_compute_type,
            next_steps=[
                "No action is needed.",
                "If transcription still feels slow, close other GPU-heavy apps and try a shorter phrase.",
            ],
            technical_details=technical_details,
        )

    if loaded_device == "cuda":
        return RuntimeDiagnostics(
            status="gpu-compat",
            headline="GPU acceleration is working in compatibility mode",
            summary=(
                "OmniDictate is using your NVIDIA GPU, but it had to use a safer compatibility "
                "mode. This can be slower than the normal GPU mode, but it should still be faster than CPU-only mode."
            ),
            device=loaded_device,
            compute_type=loaded_compute_type,
            next_steps=[
                "You can keep using OmniDictate.",
                "For best speed, update the NVIDIA driver and check that the matching CUDA/cuDNN runtime is installed.",
            ],
            technical_details=technical_details,
            actions=_runtime_actions(),
        )

    return RuntimeDiagnostics(
        status="cpu-mode",
        headline="CPU mode",
        summary=(
            "OmniDictate is working, but it did not find a usable NVIDIA GPU runtime. "
            "Transcription can be slower in CPU mode."
        ),
        device=loaded_device,
        compute_type=loaded_compute_type,
        next_steps=[
            "You can keep using OmniDictate in CPU mode.",
            "If this PC does not have an NVIDIA GPU, no GPU setup is available on this machine.",
            f"If this PC has an NVIDIA GPU, install or update the NVIDIA driver. Then install the matching CUDA/cuDNN runtime. {requirement_hint}",
            "Restart OmniDictate after installing GPU components and start dictation again.",
        ],
        technical_details=technical_details,
        actions=_runtime_actions(),
    )


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
            primary_error = ""
            try:
                self.model = WhisperModel(model_path, device=device, compute_type=compute_type, local_files_only=False)
            except Exception as exc:
                primary_error = str(exc)
                if use_cuda and "float16" in str(exc):
                    warnings.append("GPU fast mode was unavailable. Using GPU compatibility mode.")
                    self.model = WhisperModel(model_path, device="cuda", compute_type="float32", local_files_only=False)
                    loaded_device = "cuda"
                    loaded_compute_type = "float32"
                else:
                    warnings.append(f"GPU model load failed. Using slower CPU mode. Details: {exc}")
                    self.model = WhisperModel(model_path, device="cpu", compute_type="int8", local_files_only=False)
                    loaded_device = "cpu"
                    loaded_compute_type = "int8"
            self._is_loaded = True
            if use_cuda:
                cuda_types = sorted(ctranslate2_supported_compute_types("cuda"))
                if cuda_types:
                    warnings.append(f"GPU acceleration details: {', '.join(cuda_types)}.")
            return BackendLoadResult(
                True,
                f"Whisper model '{model_name}' loaded on {loaded_device} ({loaded_compute_type}).",
                warnings,
                _build_runtime_diagnostics(
                    model_name=model_name,
                    loaded_device=loaded_device,
                    loaded_compute_type=loaded_compute_type,
                    warnings=warnings,
                    primary_error=primary_error,
                ),
            )
        except Exception as exc:
            self.model = None
            self._is_loaded = False
            message = f"Error loading Whisper model: {exc}"
            return BackendLoadResult(
                False,
                message,
                warnings,
                _build_runtime_diagnostics(
                    model_name=model_name,
                    loaded_device="",
                    loaded_compute_type="",
                    warnings=warnings,
                    load_error=str(exc),
                ),
            )

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
