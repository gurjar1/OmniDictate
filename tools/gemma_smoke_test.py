from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import librosa
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.base import PromptMode, TargetAppContext, TranscriptionRequest, VisualContextSnapshot, VisualSource
from engines.gemma_gguf_backend import GemmaGGUFBackend
from engines.gemma4_backend import Gemma4Backend
from whisper_fixture_test import assert_transcript_matches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local Gemma smoke test with audio plus one image.")
    parser.add_argument("--audio", required=True, help="Path to a WAV or other librosa-supported audio file.")
    parser.add_argument("--image", required=True, help="Path to an image file to attach as visual context.")
    parser.add_argument("--runtime", default="transformers", choices=["transformers", "gguf-server"], help="Which Gemma runtime to test.")
    parser.add_argument("--model", default="google/gemma-4-E2B-it", help="Gemma model reference.")
    parser.add_argument("--quantization", default="4-bit", choices=["4-bit", "8-bit", "16-bit"], help="Load strategy.")
    parser.add_argument("--audio-mode", default="hybrid-whisper", choices=["hybrid-whisper", "native-audio"], help="Gemma audio handling mode.")
    parser.add_argument("--whisper-model", default="small", help="Whisper model used by the hybrid frontend.")
    parser.add_argument("--gguf-url", default="http://127.0.0.1:8080/v1", help="Base URL for the local OpenAI-compatible GGUF server.")
    parser.add_argument("--gguf-model", default="", help="Optional model name exposed by the GGUF server. Leave blank to auto-select the first model.")
    parser.add_argument("--duration", type=float, default=8.0, help="Audio duration in seconds to load from the sample.")
    parser.add_argument("--expected", default="", help="Optional expected transcript text to assert against.")
    parser.add_argument("--min-word-ratio", type=float, default=0.6, help="Minimum expected-word match ratio when --expected is used.")
    parser.add_argument("--report-json", default="", help="Optional path for a JSON smoke report.")
    return parser.parse_args()


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    report = {
        "runtime": args.runtime,
        "model": args.model,
        "quantization": args.quantization,
        "audio_mode": args.audio_mode,
        "whisper_model": args.whisper_model,
        "gguf_url": args.gguf_url,
        "gguf_model": args.gguf_model,
        "audio": args.audio,
        "image": args.image,
        "expected": args.expected,
        "min_word_ratio": args.min_word_ratio,
        "backend_load_success": False,
        "backend_status": "",
        "backend_warnings": [],
        "status": "not-started",
        "text": "",
        "execution_label": "",
        "used_visual_context": False,
        "latency_seconds": None,
        "result_warnings": [],
        "error": "",
    }

    audio_path = Path(args.audio)
    image_path = Path(args.image)
    if not audio_path.exists():
        print(f"Audio file not found: {audio_path}")
        report["status"] = "failed"
        report["error"] = f"Audio file not found: {audio_path}"
        if args.report_json:
            _write_report(Path(args.report_json), report)
        return 2
    if not image_path.exists():
        print(f"Image file not found: {image_path}")
        report["status"] = "failed"
        report["error"] = f"Image file not found: {image_path}"
        if args.report_json:
            _write_report(Path(args.report_json), report)
        return 2

    model_storage_path = ROOT / "smoke_test_assets" / "models"
    model_storage_path.mkdir(parents=True, exist_ok=True)

    app_settings = AppSettings(
        backend="gemma-gguf-server" if args.runtime == "gguf-server" else "gemma-4",
        gemma_model=args.model,
        gguf_server_url=args.gguf_url,
        gguf_model_name=args.gguf_model,
        gemma_quantization=args.quantization,
        gemma_audio_input_mode=args.audio_mode,
        whisper_model="large-v3-turbo",
        gemma_hybrid_whisper_model=args.whisper_model,
        prompt_mode="context",
        reasoning_requires_preview=False,
        model_storage_path=str(model_storage_path),
    )

    print(f"Loading audio from: {audio_path}")
    audio, sample_rate = librosa.load(audio_path, sr=16000, mono=True, duration=args.duration)
    print(f"Loaded {audio.shape[0] / sample_rate:.2f}s of audio at {sample_rate} Hz")

    print(f"Loading image from: {image_path}")
    image = Image.open(image_path).convert("RGB")

    backend = GemmaGGUFBackend(app_settings) if args.runtime == "gguf-server" else Gemma4Backend(app_settings)
    load_result = backend.load()
    report["backend_load_success"] = bool(load_result.success)
    report["backend_status"] = load_result.status_message
    report["backend_warnings"] = load_result.warnings
    print(f"Backend load success: {load_result.success}")
    print(f"Backend status: {load_result.status_message}")
    if load_result.warnings:
        print("Warnings:")
        for warning in load_result.warnings:
            print(f"- {warning}")
    if not load_result.success:
        report["status"] = "failed"
        report["error"] = load_result.status_message
        if args.report_json:
            _write_report(Path(args.report_json), report)
        return 1

    try:
        request = TranscriptionRequest(
            audio=audio,
            sample_rate=sample_rate,
            language=None,
            prompt_mode=PromptMode.CONTEXT,
            visual_context=VisualContextSnapshot(
                source=VisualSource.ATTACHED_IMAGE,
                images=[image],
                description=f"Images: {image_path.name}",
                metadata={"attachment_names": image_path.name},
            ),
            target_app=TargetAppContext(title="Gemma Smoke Test", process_name="gemma_smoke_test"),
            enable_thinking=False,
            max_new_tokens=64,
        )
        result = backend.transcribe(request)
        report["text"] = result.text
        report["execution_label"] = result.execution_label
        report["used_visual_context"] = bool(result.used_visual_context)
        report["latency_seconds"] = result.latency_seconds
        report["result_warnings"] = result.warnings
        print("Transcription result:")
        print(result.text)
        print(f"Route: {result.execution_label}")
        print(f"Used visual context: {result.used_visual_context}")
        print(f"Latency: {result.latency_seconds:.2f}s")
        if result.warnings:
            print("Result warnings:")
            for warning in result.warnings:
                print(f"- {warning}")
        if not result.text.strip():
            raise AssertionError("Gemma smoke returned an empty transcript.")
        if args.expected:
            assert_transcript_matches(result.text, args.expected, args.min_word_ratio)
        report["status"] = "passed"
        if args.report_json:
            _write_report(Path(args.report_json), report)
            print(f"Wrote report: {Path(args.report_json).resolve()}")
        return 0
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        if args.report_json:
            _write_report(Path(args.report_json), report)
            print(f"Wrote report: {Path(args.report_json).resolve()}")
        raise
    finally:
        backend.unload()


if __name__ == "__main__":
    raise SystemExit(main())
