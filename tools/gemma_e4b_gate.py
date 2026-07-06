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

E4B_MODEL = "google/gemma-4-E4B-it"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Gemma E4B local-weights/live-generation gate.")
    parser.add_argument("--model", default=E4B_MODEL)
    parser.add_argument("--audio", default=str(ROOT / "smoke_test_assets" / "gemma_live_smoke.wav"))
    parser.add_argument("--image", default=str(ROOT / "smoke_test_assets" / "gemma_live_smoke.png"))
    parser.add_argument("--whisper-model", default="tiny")
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--expected", default=DEFAULT_PHRASE)
    parser.add_argument("--min-word-ratio", type=float, default=0.75)
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "smoke_test_assets"),
        help="Directory for E4B gate reports.",
    )
    parser.add_argument("--report-json", default="", help="Optional gate summary JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Print/write commands without loading E4B.")
    return parser.parse_args(argv)


def _fmt_float(value: float) -> str:
    return f"{value:g}"


def build_commands(args: argparse.Namespace, python_exe: str | None = None) -> tuple[list[list[str]], dict[str, str]]:
    python = python_exe or sys.executable
    output_dir = Path(args.output_dir)
    preflight_report = output_dir / "gemma-e4b-preflight.json"
    smoke_report = output_dir / "gemma-e4b-live-smoke.json"

    preflight_command = [
        python,
        str(ROOT / "tools" / "gemma_model_preflight.py"),
        "--model",
        args.model,
        "--require-local",
        "--report-json",
        str(preflight_report),
    ]
    smoke_command = [
        python,
        str(ROOT / "tools" / "gemma_smoke_test.py"),
        "--runtime",
        "transformers",
        "--model",
        args.model,
        "--audio-mode",
        "hybrid-whisper",
        "--whisper-model",
        args.whisper_model,
        "--audio",
        str(Path(args.audio)),
        "--image",
        str(Path(args.image)),
        "--duration",
        _fmt_float(args.duration),
        "--expected",
        args.expected,
        "--min-word-ratio",
        _fmt_float(args.min_word_ratio),
        "--report-json",
        str(smoke_report),
    ]
    audit_command = [
        python,
        str(ROOT / "tools" / "gemma_e4b_gate_report_audit.py"),
        "--preflight-report",
        str(preflight_report),
        "--smoke-report",
        str(smoke_report),
        "--expected",
        args.expected,
        "--min-word-ratio",
        _fmt_float(args.min_word_ratio),
    ]
    paths = {
        "preflight_report": str(preflight_report),
        "smoke_report": str(smoke_report),
    }
    return [preflight_command, smoke_command, audit_command], paths


def _display_command(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _missing_fixture_paths(args: argparse.Namespace) -> list[Path]:
    return [path for path in (Path(args.audio), Path(args.image)) if not path.is_file()]


def main() -> int:
    args = parse_args()
    commands, paths = build_commands(args)
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    payload = {
        "status": "dry-run" if args.dry_run else "running",
        "model": args.model,
        "audio": args.audio,
        "image": args.image,
        "expected": args.expected,
        "min_word_ratio": args.min_word_ratio,
        "paths": paths,
        "commands": [_display_command(command) for command in commands],
        "results": results,
    }

    print("Gemma E4B gate sequence:")
    for command in commands:
        print(f"- {_display_command(command)}")

    if args.dry_run:
        if args.report_json:
            _write_report(Path(args.report_json), payload)
            print(f"Wrote report: {Path(args.report_json).resolve()}")
        return 0

    missing_fixtures = _missing_fixture_paths(args)
    if missing_fixtures:
        payload["status"] = "failed"
        payload["failure"] = "Missing E4B smoke fixture(s): " + ", ".join(str(path) for path in missing_fixtures)
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
    print("Gemma E4B gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
