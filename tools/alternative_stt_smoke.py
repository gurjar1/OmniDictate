from __future__ import annotations

import argparse
import sys
from pathlib import Path

import librosa

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.base import PromptMode, TargetAppContext, TranscriptionRequest, VisualContextSnapshot
from engines.transformers_asr_backend import TransformersASRBackend
from whisper_fixture_test import DEFAULT_PHRASE, assert_transcript_matches, synthesize_wav


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optional live smoke for an experimental Transformers ASR adapter.")
    parser.add_argument("--model", default="UsefulSensors/moonshine-tiny")
    parser.add_argument("--audio", default="", help="Optional audio file. If omitted, Windows SAPI generates one.")
    parser.add_argument("--expected", default=DEFAULT_PHRASE)
    parser.add_argument("--min-word-ratio", type=float, default=0.6)
    parser.add_argument("--keep-audio", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audio_path = Path(args.audio) if args.audio else synthesize_wav(args.expected)
    audio, sample_rate = librosa.load(audio_path, sr=16000, mono=True)

    settings = AppSettings(backend="transformers-asr", alternative_stt_model=args.model, language="en")
    backend = TransformersASRBackend(settings)
    load_result = backend.load()
    print(f"Backend status: {load_result.status_message}")
    if not load_result.success:
        raise RuntimeError(load_result.status_message)

    try:
        result = backend.transcribe(
            TranscriptionRequest(
                audio=audio,
                sample_rate=sample_rate,
                language="en",
                prompt_mode=PromptMode.PURE,
                visual_context=VisualContextSnapshot(),
                target_app=TargetAppContext(title="Alternative STT smoke", process_name="alternative_stt_smoke"),
            )
        )
        print(f"Route: {result.execution_label}")
        print(f"Latency: {result.latency_seconds:.2f}s")
        assert_transcript_matches(result.text, args.expected, args.min_word_ratio)
    finally:
        backend.unload()
        if not args.audio and not args.keep_audio:
            try:
                audio_path.unlink()
            except OSError:
                pass

    print("Alternative STT live smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
