from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

import librosa

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.base import PromptMode, TargetAppContext, TranscriptionRequest, VisualContextSnapshot
from engines.whisper_backend import WhisperBackend


DEFAULT_PHRASE = "hello world this is a simple speech test"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a live Faster-Whisper transcription check.")
    parser.add_argument("--model", default="tiny", help="Whisper model to load. Use tiny for a quick smoke.")
    parser.add_argument("--language", default="en", help="Language code passed to faster-whisper.")
    parser.add_argument("--audio", default="", help="Optional WAV/audio file. If omitted, Windows SAPI generates one.")
    parser.add_argument("--expected", default=DEFAULT_PHRASE, help="Expected transcript text.")
    parser.add_argument("--min-word-ratio", type=float, default=0.75, help="Minimum expected-word match ratio.")
    parser.add_argument("--keep-audio", action="store_true", help="Keep generated WAV and print its path.")
    return parser.parse_args()


def normalize_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def synthesize_wav(text: str) -> Path:
    try:
        import win32com.client
    except Exception as exc:  # pragma: no cover - environment-specific fallback
        raise RuntimeError("Windows SAPI synthesis requires pywin32/win32com.") from exc

    output_path = Path(tempfile.gettempdir()) / "omnidictate_whisper_fixture.wav"
    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    stream.Open(str(output_path), 3, False)
    old_stream = voice.AudioOutputStream
    try:
        voice.AudioOutputStream = stream
        voice.Speak(text)
    finally:
        voice.AudioOutputStream = old_stream
        stream.Close()
    return output_path


def assert_transcript_matches(actual: str, expected: str, min_word_ratio: float) -> None:
    expected_words = normalize_words(expected)
    actual_words = set(normalize_words(actual))
    if not expected_words:
        raise AssertionError("Expected text produced no comparable words.")

    matched = [word for word in expected_words if word in actual_words]
    ratio = len(matched) / len(expected_words)
    print(f"Expected: {expected}")
    print(f"Actual:   {actual}")
    print(f"Matched {len(matched)}/{len(expected_words)} expected words ({ratio:.0%}).")
    if ratio < min_word_ratio:
        missing = [word for word in expected_words if word not in actual_words]
        raise AssertionError(f"Transcript did not meet match threshold. Missing: {', '.join(missing)}")


def main() -> int:
    args = parse_args()
    audio_path = Path(args.audio) if args.audio else synthesize_wav(args.expected)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    print(f"Audio fixture: {audio_path}")
    audio, sample_rate = librosa.load(audio_path, sr=16000, mono=True)
    if audio.size == 0:
        raise AssertionError("Audio fixture loaded as empty.")

    settings = AppSettings(backend="faster-whisper", whisper_model=args.model, language=args.language)
    backend = WhisperBackend(settings)
    load_result = backend.load()
    print(f"Backend status: {load_result.status_message}")
    for warning in load_result.warnings:
        print(f"Warning: {warning}")
    if not load_result.success:
        raise RuntimeError(load_result.status_message)

    try:
        request = TranscriptionRequest(
            audio=audio,
            sample_rate=sample_rate,
            language=args.language,
            prompt_mode=PromptMode.PURE,
            visual_context=VisualContextSnapshot(),
            target_app=TargetAppContext(title="Whisper fixture", process_name="whisper_fixture_test"),
            max_new_tokens=48,
        )
        result = backend.transcribe(request)
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

    print("Whisper fixture test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
