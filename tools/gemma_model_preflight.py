from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.model_manager import ModelManager


def _directory_summary(path: Path) -> dict:
    files = [child for child in path.rglob("*") if child.is_file()]
    total = sum(child.stat().st_size for child in files)
    has_safetensors = any(child.suffix == ".safetensors" for child in files)
    return {
        "exists": path.exists(),
        "files": len(files),
        "bytes": total,
        "has_safetensors": has_safetensors,
    }


def _torch_summary() -> dict:
    try:
        import torch
    except Exception as exc:
        return {"available": False, "error": str(exc)}

    summary = {
        "available": True,
        "version": getattr(torch, "__version__", "unknown"),
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_devices": [],
    }
    if torch.cuda.is_available():
        for index in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(index)
            summary["cuda_devices"].append(
                {
                    "index": index,
                    "name": props.name,
                    "total_memory_bytes": int(props.total_memory),
                }
            )
    return summary


def _transformers_summary() -> dict:
    try:
        import transformers
        from transformers import AutoProcessor

        try:
            from transformers import AutoModelForMultimodalLM  # noqa: F401
            model_cls = "AutoModelForMultimodalLM"
        except ImportError:
            from transformers import AutoModelForImageTextToText  # noqa: F401
            model_cls = "AutoModelForImageTextToText"
        return {
            "available": True,
            "version": getattr(transformers, "__version__", "unknown"),
            "processor_class": AutoProcessor.__name__,
            "model_class": model_cls,
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight Gemma 4 model availability without loading weights.")
    parser.add_argument("--model", default="google/gemma-4-E4B-it", help="Gemma model id to inspect.")
    parser.add_argument(
        "--model-storage",
        default=str(ROOT / "smoke_test_assets" / "models"),
        help="Local model storage directory used by OmniDictate.",
    )
    parser.add_argument("--report-json", default="", help="Optional JSON report path.")
    parser.add_argument(
        "--require-local",
        action="store_true",
        help="Fail if the resolved local model directory is missing or has no safetensors files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = AppSettings(
        backend="gemma-4",
        gemma_model=args.model,
        model_storage_path=args.model_storage,
        gemma_audio_input_mode="hybrid-whisper",
        gemma_quantization="4-bit",
    )
    manager = ModelManager(settings)
    local_dir = Path(args.model_storage) / args.model.rsplit("/", 1)[-1]
    resolved_reference = manager.resolve_model_reference()
    kwargs, warnings = manager.build_model_kwargs()
    report = {
        "model": args.model,
        "model_storage": str(Path(args.model_storage).resolve()),
        "local_dir": str(local_dir.resolve()),
        "resolved_reference": resolved_reference,
        "local_summary": _directory_summary(local_dir),
        "transformers": _transformers_summary(),
        "torch": _torch_summary(),
        "model_kwargs_keys": sorted(kwargs.keys()),
        "warnings": warnings,
        "recommended_hybrid_command": (
            ".\\venv\\Scripts\\python.exe tools\\gemma_smoke_test.py "
            "--audio smoke_test_assets\\gemma_live_smoke.wav "
            "--image smoke_test_assets\\gemma_live_smoke.png "
            f"--runtime transformers --model {args.model} "
            "--quantization 4-bit --audio-mode hybrid-whisper --whisper-model tiny "
            '--duration 5 --expected "hello world this is a simple speech test" --min-word-ratio 0.75'
        ),
        "recommended_native_audio_command": (
            ".\\venv\\Scripts\\python.exe tools\\gemma_smoke_test.py "
            "--audio smoke_test_assets\\gemma_live_smoke.wav "
            "--image smoke_test_assets\\gemma_live_smoke.png "
            f"--runtime transformers --model {args.model} "
            "--quantization 16-bit --audio-mode native-audio --whisper-model tiny "
            '--duration 5 --expected "hello world this is a simple speech test" --min-word-ratio 0.5'
        ),
    }

    print(json.dumps(report, indent=2))
    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote report: {report_path.resolve()}")

    local_summary = report["local_summary"]
    if args.require_local and (not local_summary["exists"] or not local_summary["has_safetensors"]):
        print("Gemma local model preflight failed: local weights are missing.")
        return 1

    print("Gemma model preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
