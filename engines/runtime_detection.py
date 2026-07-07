from __future__ import annotations

from typing import Any


def import_torch() -> Any | None:
    try:
        import torch
    except Exception:
        return None
    return torch


def torch_cuda_is_available() -> bool:
    torch = import_torch()
    if torch is None:
        return False
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def ctranslate2_cuda_is_available() -> bool:
    try:
        import ctranslate2
    except Exception:
        return False
    try:
        return int(ctranslate2.get_cuda_device_count()) > 0
    except Exception:
        return False


def ctranslate2_runtime_probe() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "available": False,
        "version": "",
        "cuda_device_count": 0,
        "supported_compute_types": [],
        "error": "",
    }
    try:
        import ctranslate2
    except Exception as exc:
        payload["error"] = f"CTranslate2 import failed: {exc}"
        return payload

    payload["available"] = True
    payload["version"] = str(getattr(ctranslate2, "__version__", ""))
    try:
        payload["cuda_device_count"] = int(ctranslate2.get_cuda_device_count())
    except Exception as exc:
        payload["error"] = f"CTranslate2 CUDA check failed: {exc}"
        return payload

    if payload["cuda_device_count"] > 0:
        try:
            payload["supported_compute_types"] = sorted(ctranslate2.get_supported_compute_types("cuda"))
        except Exception as exc:
            payload["error"] = f"CTranslate2 CUDA compute-type check failed: {exc}"
    return payload


def whisper_cuda_is_available() -> bool:
    return ctranslate2_cuda_is_available() or torch_cuda_is_available()


def ctranslate2_supported_compute_types(device: str) -> set[str]:
    try:
        import ctranslate2
    except Exception:
        return set()
    try:
        return set(ctranslate2.get_supported_compute_types(device))
    except Exception:
        return set()


def empty_torch_cuda_cache() -> None:
    torch = import_torch()
    if torch is None:
        return
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        return
