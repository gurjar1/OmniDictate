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
