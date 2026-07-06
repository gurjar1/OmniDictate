from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "smoke_test_assets" / "microphone" / "physical-gate-dry-run.json"
DEFAULT_DEVICE_INVENTORY = ROOT / "smoke_test_assets" / "microphone" / "audio-device-inventory.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print the human run card from a physical microphone gate dry-run report."
    )
    parser.add_argument(
        "--report-json",
        default=str(DEFAULT_REPORT),
        help="Path to physical-gate-dry-run.json from tools\\physical_microphone_gate.py --dry-run.",
    )
    return parser.parse_args(argv)


def _read_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _inventory_recommended_device(path: Path = DEFAULT_DEVICE_INVENTORY) -> str:
    if not path.is_file():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(payload.get("recommended_device_argument") or "").strip()


def _effective_device(report: dict) -> tuple[str, str]:
    recommended = _inventory_recommended_device()
    report_device = str(report.get("device") or "").strip()
    if recommended:
        return recommended, "audio-device-inventory.json recommended_device_argument"
    return report_device, "physical-gate-dry-run.json device"


def _execution_command(report: dict) -> str:
    command = [
        r".\venv\Scripts\python.exe",
        "tools\\physical_microphone_gate.py",
        "--model",
        str(report.get("model") or "large-v3-turbo"),
        "--duration",
        str(report.get("duration_seconds") or 7).rstrip("0").rstrip("."),
        "--countdown",
        str(report.get("countdown_seconds") or 3).rstrip("0").rstrip("."),
        "--timeout",
        str(report.get("timeout_seconds") or 40).rstrip("0").rstrip("."),
    ]
    device, _source = _effective_device(report)
    if device:
        command.extend(["--device", device])
    command.extend(["--report-json", r"smoke_test_assets\microphone\physical-gate-report.json"])
    return subprocess.list2cmdline(command)


def build_run_card(report: dict) -> list[str]:
    prompt = report.get("manual_prompt") or {}
    paths = report.get("paths") or {}
    required_modes = prompt.get("required_loop_modes") or []
    mode_text = ", ".join(str(mode).upper() for mode in required_modes)
    device, device_source = _effective_device(report)
    lines = [
        "Physical Microphone Gate Run Card",
        f"Status: {report.get('status', '')}",
        f"Model: {report.get('model', '')}",
        f"Device: {device or prompt.get('device') or report.get('device') or '<default input>'}",
        f"Device source: {device_source}",
        f"Phrase: {prompt.get('phrase') or report.get('expected', '')}",
        f"Countdown: {prompt.get('countdown_seconds', report.get('countdown_seconds', ''))}s",
        f"Recording duration: {prompt.get('recording_duration_seconds', report.get('duration_seconds', ''))}s",
        f"Live-loop timeout: {prompt.get('live_loop_timeout_seconds', report.get('timeout_seconds', ''))}s",
        f"Minimum word ratio: {prompt.get('min_word_ratio', report.get('min_word_ratio', ''))}",
        f"Required modes: {mode_text}",
        f"Saved WAV: {paths.get('wav', '')}",
        f"Capture report: {paths.get('capture_report', '')}",
        f"Loop report: {paths.get('loop_report', '')}",
        f"Pass rule: {prompt.get('instruction', '')}",
    ]
    command = _execution_command(report)
    if command:
        lines.extend(["Execution command:", command])
    return lines


def main() -> int:
    args = parse_args()
    report_path = Path(args.report_json)
    if not report_path.is_absolute():
        report_path = ROOT / report_path
    report = _read_report(report_path)
    print("\n".join(build_run_card(report)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
