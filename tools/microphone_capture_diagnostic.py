from __future__ import annotations

import argparse
import json
import sys
import time
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.base import PromptMode, TargetAppContext, TranscriptionRequest, VisualContextSnapshot
from engines.whisper_backend import WhisperBackend
from whisper_fixture_test import DEFAULT_PHRASE, assert_transcript_matches, normalize_words


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record a physical microphone sample, save it, report levels, and optionally transcribe it."
    )
    parser.add_argument("--duration", type=float, default=6.0, help="Seconds to record.")
    parser.add_argument("--sample-rate", type=int, default=16000, help="Recording sample rate.")
    parser.add_argument("--device", default=None, help="Optional sounddevice input device index or name.")
    parser.add_argument(
        "--source-device",
        default="",
        help="Optional metadata for the input device used to create --input WAV evidence.",
    )
    parser.add_argument(
        "--source-prompted",
        action="store_true",
        help="Mark --input WAV evidence as originating from a prompted human speech capture.",
    )
    parser.add_argument("--output", default=str(ROOT / "smoke_test_assets" / "microphone" / "live-mic-capture.wav"))
    parser.add_argument("--input", default="", help="Existing WAV file to validate/transcribe instead of recording.")
    parser.add_argument("--report-json", default="", help="Optional path for a JSON stats/transcript report.")
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List input-capable audio devices and exit without recording.",
    )
    parser.add_argument("--model", default="", help="Optional Whisper model to transcribe the captured WAV.")
    parser.add_argument("--expected", default=DEFAULT_PHRASE, help="Expected phrase for optional transcript matching.")
    parser.add_argument("--min-word-ratio", type=float, default=0.6)
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Print a speak-now prompt before recording. Useful for human physical-microphone evidence.",
    )
    parser.add_argument(
        "--countdown",
        type=float,
        default=3.0,
        help="Seconds to wait after --prompt before recording starts.",
    )
    parser.add_argument(
        "--allow-low-level",
        action="store_true",
        help="Do not fail when the recording is near-silent. Useful for collecting baseline device evidence.",
    )
    return parser.parse_args(argv)


def _write_pcm16_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    clipped = np.clip(audio, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def _read_pcm_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    if sample_width == 1:
        raw = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        audio = (raw - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width} bytes")

    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio.astype(np.float32, copy=False), sample_rate


def _audio_stats(audio: np.ndarray, sample_rate: int) -> dict[str, float]:
    abs_audio = np.abs(audio)
    peak = float(np.max(abs_audio)) if audio.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0
    duration = float(audio.size / sample_rate) if sample_rate else 0.0
    active_ratio = float(np.mean(abs_audio > 0.015)) if audio.size else 0.0
    clipping_ratio = float(np.mean(abs_audio >= 0.98)) if audio.size else 0.0
    return {
        "duration_seconds": duration,
        "rms": rms,
        "peak": peak,
        "active_ratio": active_ratio,
        "clipping_ratio": clipping_ratio,
    }


def _print_devices() -> None:
    import sounddevice as sd

    print(f"Default audio devices: {sd.default.device}")
    try:
        print(f"Default input: {sd.query_devices(kind='input')['name']}")
    except Exception as exc:
        print(f"Default input query failed: {exc}")


def _device_inventory(sd_module=None) -> dict[str, object]:
    sd = sd_module
    if sd is None:
        import sounddevice as sd  # type: ignore[no-redef]

    devices = []
    try:
        default_devices = list(sd.default.device)
    except TypeError:
        default_devices = sd.default.device
    try:
        default_input = sd.query_devices(kind="input")
        default_input_name = default_input.get("name", "")
    except Exception:
        default_input_name = ""

    for index, device in enumerate(sd.query_devices()):
        max_input_channels = int(device.get("max_input_channels", 0) or 0)
        if max_input_channels <= 0:
            continue
        devices.append(
            {
                "index": index,
                "name": str(device.get("name", "")),
                "hostapi": int(device.get("hostapi", -1) or -1),
                "max_input_channels": max_input_channels,
                "default_samplerate": float(device.get("default_samplerate", 0.0) or 0.0),
            }
        )

    default_input_index = None
    if isinstance(default_devices, list) and default_devices:
        default_input_index = default_devices[0]
    default_input_device = next(
        (device for device in devices if device["index"] == default_input_index),
        None,
    )
    name_counts: dict[str, int] = {}
    for device in devices:
        name = str(device["name"])
        name_counts[name] = name_counts.get(name, 0) + 1
    duplicate_names = sorted(name for name, count in name_counts.items() if count > 1)

    return {
        "kind": "audio-device-inventory",
        "default_devices": default_devices,
        "default_input_name": default_input_name,
        "recommended_device_argument": str(default_input_index) if default_input_device else "",
        "recommended_device": default_input_device or {},
        "duplicate_input_names": duplicate_names,
        "input_devices": devices,
    }


def _print_device_inventory(payload: dict[str, object]) -> None:
    print(f"Default audio devices: {payload['default_devices']}")
    print(f"Default input: {payload['default_input_name']}")
    if payload["recommended_device_argument"]:
        print(f"Recommended --device: {payload['recommended_device_argument']}")
    if payload["duplicate_input_names"]:
        print("Duplicate input names detected; prefer a numeric --device index for the physical gate.")
    print("Input-capable devices:")
    for device in payload["input_devices"]:
        row = device
        print(
            f"- [{row['index']}] {row['name']} "
            f"channels={row['max_input_channels']} "
            f"default_samplerate={row['default_samplerate']:.0f}"
        )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sounddevice_device_arg(device: str | None) -> int | str | None:
    selected = str(device or "").strip()
    if not selected:
        return None
    try:
        return int(selected)
    except ValueError:
        return selected


def _record_audio(duration: float, sample_rate: int, device: str | None) -> np.ndarray:
    import sounddevice as sd

    frames = int(round(duration * sample_rate))
    recording = sd.rec(
        frames,
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        device=_sounddevice_device_arg(device),
    )
    sd.wait()
    return np.asarray(recording, dtype=np.float32).reshape(-1)


def _prompt_for_speech(expected: str, countdown: float, duration: float) -> None:
    print(f"Speak this phrase during the {duration:.1f}s recording:")
    print(f"  {expected}")
    if countdown <= 0:
        print("Recording starts now.")
        return
    remaining = int(round(countdown))
    while remaining > 0:
        print(f"Recording starts in {remaining}...")
        time.sleep(1.0)
        remaining -= 1
    print("Recording now.")


def _transcribe(audio: np.ndarray, sample_rate: int, model: str, expected: str, min_word_ratio: float) -> str:
    settings = AppSettings(
        backend="faster-whisper",
        whisper_model=model,
        language="en",
        screen_context_enabled=False,
        webcam_enabled=False,
    )
    backend = WhisperBackend(settings)
    load_result = backend.load()
    print(f"Whisper load: {load_result.status_message}")
    for warning in load_result.warnings:
        print(f"Whisper warning: {warning}")
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
                target_app=TargetAppContext(),
            )
        )
    finally:
        backend.unload()

    print(f"Transcript: {result.text}")
    if expected:
        expected_words = normalize_words(expected)
        actual_words = set(normalize_words(result.text))
        matched = [word for word in expected_words if word in actual_words]
        ratio = len(matched) / len(expected_words) if expected_words else 1.0
        print(f"Expected: {expected}")
        print(f"Matched {len(matched)}/{len(expected_words)} expected words ({ratio:.0%}).")
        assert_transcript_matches(result.text, expected, min_word_ratio)
    return result.text


def _write_report(
    path: Path,
    source: Path,
    stats: dict[str, float],
    transcript: str,
    prompted: bool,
    expected: str,
    device: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": str(source.resolve()),
        "duration_seconds": stats["duration_seconds"],
        "rms": stats["rms"],
        "peak": stats["peak"],
        "active_ratio": stats["active_ratio"],
        "clipping_ratio": stats["clipping_ratio"],
        "transcript": transcript,
        "prompted": prompted,
        "expected": expected,
        "device": device,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    output = Path(args.output)

    if args.list_devices:
        payload = _device_inventory()
        _print_device_inventory(payload)
        if args.report_json:
            report_path = Path(args.report_json)
            _write_json(report_path, payload)
            print(f"Wrote report: {report_path.resolve()}")
        return 0

    if args.input:
        source = Path(args.input)
        if not source.exists():
            raise FileNotFoundError(f"Input WAV not found: {source}")
        print(f"Loading existing WAV: {source.resolve()}")
        audio, sample_rate = _read_pcm_wav(source)
    else:
        source = output
        _print_devices()
        if args.prompt:
            _prompt_for_speech(args.expected, args.countdown, args.duration)
        print(f"Recording {args.duration:.1f}s at {args.sample_rate} Hz...")
        audio = _record_audio(args.duration, args.sample_rate, args.device)
        sample_rate = args.sample_rate
        _write_pcm16_wav(output, audio, sample_rate)

    stats = _audio_stats(audio, sample_rate)
    if args.input:
        print(f"Validated WAV: {source.resolve()}")
    else:
        print(f"Saved WAV: {output.resolve()}")
    print(
        "Audio stats: "
        f"duration={stats['duration_seconds']:.2f}s "
        f"rms={stats['rms']:.5f} "
        f"peak={stats['peak']:.5f} "
        f"active={stats['active_ratio']:.0%} "
        f"clipping={stats['clipping_ratio']:.2%}"
    )

    if stats["peak"] < 0.005 and not args.allow_low_level:
        raise AssertionError("Captured audio peak is extremely low; microphone input may be muted or silent.")
    if stats["clipping_ratio"] > 0.05:
        raise AssertionError("Captured audio appears clipped; lower microphone gain or playback volume.")

    transcript = ""
    if args.model:
        transcript = _transcribe(audio, sample_rate, args.model, args.expected, args.min_word_ratio)

    if args.report_json:
        report_path = Path(args.report_json)
        report_device = args.source_device if args.input else (args.device or "")
        _write_report(
            report_path,
            source,
            stats,
            transcript,
            bool(args.source_prompted if args.input else args.prompt),
            args.expected,
            report_device,
        )
        print(f"Wrote report: {report_path.resolve()}")

    print("Microphone capture diagnostic passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
