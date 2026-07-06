from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.whisper_fixture_test import DEFAULT_PHRASE


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the guided physical microphone phrase gate end to end."
    )
    parser.add_argument("--model", default="large-v3-turbo")
    parser.add_argument("--expected", default=DEFAULT_PHRASE)
    parser.add_argument("--min-word-ratio", type=float, default=0.6)
    parser.add_argument("--duration", type=float, default=7.0)
    parser.add_argument("--countdown", type=float, default=3.0)
    parser.add_argument("--timeout", type=float, default=40.0)
    parser.add_argument("--device", default="", help="Optional sounddevice input device index or name.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "smoke_test_assets" / "microphone"),
        help="Directory for WAV and JSON evidence.",
    )
    parser.add_argument("--report-json", default="", help="Optional gate summary JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Print/write commands without opening the microphone.")
    parser.add_argument(
        "--reuse-capture",
        action="store_true",
        help=(
            "Reuse an existing spoken WAV and capture report, then rerun only "
            "the live VAD/PTT loop and final audit."
        ),
    )
    return parser.parse_args(argv)


def _fmt_float(value: float) -> str:
    return f"{value:g}"


def build_commands(args: argparse.Namespace, python_exe: str | None = None) -> tuple[list[list[str]], dict[str, str]]:
    python = python_exe or sys.executable
    output_dir = Path(args.output_dir)
    wav = output_dir / "spoken-phrase-large-v3-turbo.wav"
    capture_report = output_dir / "spoken-phrase-large-v3-turbo-report.json"
    loop_report = output_dir / "live-loop-large-v3-turbo-report.json"

    capture_command = [
        python,
        str(ROOT / "tools" / "microphone_capture_diagnostic.py"),
        "--duration",
        _fmt_float(args.duration),
        "--prompt",
        "--countdown",
        _fmt_float(args.countdown),
        "--model",
        args.model,
        "--expected",
        args.expected,
        "--min-word-ratio",
        _fmt_float(args.min_word_ratio),
        "--output",
        str(wav),
    ]
    if args.device:
        capture_command.extend(["--device", args.device])

    revalidate_command = [
        python,
        str(ROOT / "tools" / "microphone_capture_diagnostic.py"),
        "--input",
        str(wav),
        "--model",
        args.model,
        "--expected",
        args.expected,
        "--min-word-ratio",
        _fmt_float(args.min_word_ratio),
        "--report-json",
        str(capture_report),
        "--source-prompted",
    ]
    if args.device:
        revalidate_command.extend(["--source-device", args.device])

    loop_command = [
        python,
        str(ROOT / "tools" / "live_microphone_smoke.py"),
        "--model",
        args.model,
        "--mode",
        "both",
        "--timeout",
        _fmt_float(args.timeout),
        "--manual",
        "--countdown",
        _fmt_float(args.countdown),
        "--max-transcripts",
        "1",
        "--expected",
        args.expected,
        "--min-word-ratio",
        _fmt_float(args.min_word_ratio),
        "--report-json",
        str(loop_report),
    ]
    if args.device:
        loop_command.extend(["--device", args.device])
    audit_command = [
        python,
        str(ROOT / "tools" / "microphone_gate_report_audit.py"),
        "--capture-report",
        str(capture_report),
        "--loop-report",
        str(loop_report),
        "--expected",
        args.expected,
        "--min-word-ratio",
        _fmt_float(args.min_word_ratio),
    ]
    paths = {
        "wav": str(wav),
        "capture_report": str(capture_report),
        "loop_report": str(loop_report),
    }
    commands = [loop_command, audit_command] if args.reuse_capture else [
        capture_command,
        revalidate_command,
        loop_command,
        audit_command,
    ]
    return commands, paths


def _display_command(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def _device_validation_failure(device: str, sd_module=None) -> str:
    selected = str(device or "").strip()
    if not selected:
        return ""
    try:
        int(selected)
        return ""
    except ValueError:
        pass

    sd = sd_module
    if sd is None:
        import sounddevice as sd  # type: ignore[no-redef]

    matches = []
    for index, candidate in enumerate(sd.query_devices()):
        if int(candidate.get("max_input_channels", 0) or 0) <= 0:
            continue
        if str(candidate.get("name", "")) == selected:
            matches.append(index)

    if len(matches) > 1:
        indices = ", ".join(str(index) for index in matches)
        return (
            f"Ambiguous input device name {selected!r}; matching input indexes: {indices}. "
            "Use a numeric --device index from tools\\microphone_capture_diagnostic.py --list-devices."
        )
    return ""


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _manual_prompt_payload(args: argparse.Namespace) -> dict[str, object]:
    return {
        "phrase": args.expected,
        "device": args.device,
        "countdown_seconds": args.countdown,
        "recording_duration_seconds": args.duration,
        "live_loop_timeout_seconds": args.timeout,
        "min_word_ratio": args.min_word_ratio,
        "required_loop_modes": ["vad", "ptt"],
        "instruction": (
            "When prompted, speak the phrase clearly into the selected microphone. "
            "The gate passes only if the saved WAV transcript and both live VAD/PTT "
            "transcripts meet the word-match threshold."
        ),
    }


def main() -> int:
    args = parse_args()
    commands, paths = build_commands(args)
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    payload = {
        "status": "dry-run" if args.dry_run else "running",
        "model": args.model,
        "expected": args.expected,
        "min_word_ratio": args.min_word_ratio,
        "device": args.device,
        "duration_seconds": args.duration,
        "countdown_seconds": args.countdown,
        "timeout_seconds": args.timeout,
        "manual_prompt": _manual_prompt_payload(args),
        "paths": paths,
        "commands": [_display_command(command) for command in commands],
        "reuse_capture": bool(args.reuse_capture),
        "results": results,
    }

    print("Physical microphone gate sequence:")
    for command in commands:
        print(f"- {_display_command(command)}")

    device_failure = _device_validation_failure(args.device)
    if device_failure:
        payload["status"] = "failed"
        payload["failure"] = device_failure
        if args.report_json:
            _write_report(Path(args.report_json), payload)
            print(f"Wrote report: {Path(args.report_json).resolve()}")
        print(device_failure)
        return 2

    if args.dry_run:
        if args.report_json:
            _write_report(Path(args.report_json), payload)
            print(f"Wrote report: {Path(args.report_json).resolve()}")
        return 0

    if args.reuse_capture:
        missing_capture = [
            path for path in (Path(paths["wav"]), Path(paths["capture_report"])) if not path.is_file()
        ]
        if missing_capture:
            payload["status"] = "failed"
            payload["failure"] = (
                "--reuse-capture requires existing spoken WAV and capture report: "
                + ", ".join(str(path) for path in missing_capture)
            )
            if args.report_json:
                _write_report(Path(args.report_json), payload)
                print(f"Wrote report: {Path(args.report_json).resolve()}")
            print(payload["failure"])
            return 2

    for index, command in enumerate(commands, start=1):
        print("")
        print(f"==> Step {index}/{len(commands)}")
        print(_display_command(command))
        result = subprocess.run(command, cwd=ROOT, check=False)
        results.append({"command": _display_command(command), "returncode": result.returncode})
        if result.returncode != 0:
            payload["status"] = "failed"
            if args.report_json:
                _write_report(Path(args.report_json), payload)
                print(f"Wrote report: {Path(args.report_json).resolve()}")
            return result.returncode

    payload["status"] = "passed"
    if args.report_json:
        _write_report(Path(args.report_json), payload)
        print(f"Wrote report: {Path(args.report_json).resolve()}")
    print("Physical microphone gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
