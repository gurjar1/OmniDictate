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
    parser = argparse.ArgumentParser(description="Run the real GGUF/OpenAI-compatible server gate.")
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--server-implementation", required=True, help="Named real server, e.g. LM Studio.")
    parser.add_argument("--model", default="", help="Optional model id for the direct probe.")
    parser.add_argument("--gguf-model", default="", help="Optional model id for OmniDictate GGUF backend.")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--no-image", action="store_true", help="Use text-only direct probe.")
    parser.add_argument("--audio", default=str(ROOT / "smoke_test_assets" / "gemma_live_smoke.wav"))
    parser.add_argument("--image", default=str(ROOT / "smoke_test_assets" / "gemma_live_smoke.png"))
    parser.add_argument("--whisper-model", default="tiny")
    parser.add_argument("--expected", default=DEFAULT_PHRASE)
    parser.add_argument("--min-word-ratio", type=float, default=0.6)
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "smoke_test_assets" / "gguf"),
        help="Directory for GGUF gate reports.",
    )
    parser.add_argument("--report-json", default="", help="Optional gate summary JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Print/write commands without contacting a server.")
    return parser.parse_args(argv)


def _fmt_float(value: float) -> str:
    return f"{value:g}"


def build_commands(args: argparse.Namespace, python_exe: str | None = None) -> tuple[list[list[str]], dict[str, str]]:
    python = python_exe or sys.executable
    output_dir = Path(args.output_dir)
    probe_report = output_dir / "real-server-probe.json"
    smoke_report = output_dir / "real-server-smoke.json"

    probe_command = [
        python,
        str(ROOT / "tools" / "gguf_server_probe.py"),
        "--url",
        args.url,
        "--timeout",
        _fmt_float(args.timeout),
        "--report-json",
        str(probe_report),
    ]
    if args.model:
        probe_command.extend(["--model", args.model])
    if args.no_image:
        probe_command.append("--no-image")

    smoke_command = [
        python,
        str(ROOT / "tools" / "gemma_smoke_test.py"),
        "--runtime",
        "gguf-server",
        "--gguf-url",
        args.url,
        "--audio",
        str(Path(args.audio)),
        "--image",
        str(Path(args.image)),
        "--whisper-model",
        args.whisper_model,
        "--expected",
        args.expected,
        "--min-word-ratio",
        _fmt_float(args.min_word_ratio),
        "--report-json",
        str(smoke_report),
    ]
    if args.gguf_model:
        smoke_command.extend(["--gguf-model", args.gguf_model])

    audit_command = [
        python,
        str(ROOT / "tools" / "gguf_gate_report_audit.py"),
        "--probe-report",
        str(probe_report),
        "--smoke-report",
        str(smoke_report),
        "--server-implementation",
        args.server_implementation,
        "--expected",
        args.expected,
        "--min-word-ratio",
        _fmt_float(args.min_word_ratio),
    ]
    paths = {
        "probe_report": str(probe_report),
        "smoke_report": str(smoke_report),
    }
    return [probe_command, smoke_command, audit_command], paths


def _display_command(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _validate_server_label(label: str) -> str:
    stripped = label.strip()
    if not stripped:
        raise ValueError("--server-implementation is required")
    if "mock" in stripped.lower():
        raise ValueError("--server-implementation must name a real server, not a mock")
    return stripped


def _missing_fixture_paths(args: argparse.Namespace) -> list[Path]:
    return [path for path in (Path(args.audio), Path(args.image)) if not path.is_file()]


def main() -> int:
    args = parse_args()
    try:
        server_label = _validate_server_label(args.server_implementation)
    except ValueError as exc:
        print(f"GGUF gate configuration failed: {exc}")
        return 2

    commands, paths = build_commands(args)
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    payload = {
        "status": "dry-run" if args.dry_run else "running",
        "url": args.url,
        "server_implementation": server_label,
        "model": args.model,
        "gguf_model": args.gguf_model,
        "expected": args.expected,
        "min_word_ratio": args.min_word_ratio,
        "paths": paths,
        "commands": [_display_command(command) for command in commands],
        "results": results,
    }

    print("GGUF real-server gate sequence:")
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
        payload["failure"] = "Missing GGUF smoke fixture(s): " + ", ".join(str(path) for path in missing_fixtures)
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
    print("GGUF real-server gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
