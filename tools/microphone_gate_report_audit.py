from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.whisper_fixture_test import DEFAULT_PHRASE, normalize_words


REQUIRED_MODES = {"vad", "ptt"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate whether saved microphone reports close the physical VAD/PTT phrase gate."
    )
    parser.add_argument("--capture-report", required=True, help="JSON from microphone_capture_diagnostic.py.")
    parser.add_argument("--loop-report", required=True, help="JSON from live_microphone_smoke.py.")
    parser.add_argument("--expected", default=DEFAULT_PHRASE)
    parser.add_argument("--min-word-ratio", type=float, default=0.6)
    parser.add_argument("--min-peak", type=float, default=0.005)
    return parser.parse_args()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _word_ratio(actual: str, expected: str) -> float:
    expected_words = normalize_words(expected)
    if not expected_words:
        return 0.0
    actual_words = set(normalize_words(actual))
    matched = [word for word in expected_words if word in actual_words]
    return len(matched) / len(expected_words)


def audit_reports(
    capture_report: dict,
    loop_report: dict,
    expected: str = DEFAULT_PHRASE,
    min_word_ratio: float = 0.6,
    min_peak: float = 0.005,
) -> list[str]:
    failures: list[str] = []

    if not capture_report.get("prompted"):
        failures.append("capture report was not created from a prompted human speech run")
    if capture_report.get("expected") != expected:
        failures.append("capture report expected phrase does not match the gate phrase")
    capture_device = str(capture_report.get("device") or "")
    loop_device = str(loop_report.get("device") or "")
    if capture_device and loop_device and capture_device != loop_device:
        failures.append("capture report device does not match live loop report device")
    if float(capture_report.get("peak") or 0.0) < min_peak:
        failures.append("capture report peak is below the speech-level threshold")
    if float(capture_report.get("clipping_ratio") or 0.0) > 0.05:
        failures.append("capture report indicates clipped audio")
    capture_transcript = str(capture_report.get("transcript") or "")
    if _word_ratio(capture_transcript, expected) < min_word_ratio:
        failures.append("capture report transcript does not meet the word-match threshold")

    if loop_report.get("outcome") != "passed":
        failures.append("live loop report outcome is not passed")
    if loop_report.get("expected") != expected:
        failures.append("live loop report expected phrase does not match the gate phrase")
    modes = {str(result.get("mode") or "") for result in loop_report.get("results") or []}
    if modes != REQUIRED_MODES:
        failures.append("live loop report must contain passing VAD and PTT results")
    for result in loop_report.get("results") or []:
        mode = str(result.get("mode") or "<missing>")
        transcript = str(result.get("transcript") or "")
        if _word_ratio(transcript, expected) < min_word_ratio:
            failures.append(f"live loop {mode} transcript does not meet the word-match threshold")
    if loop_report.get("errors"):
        failures.append("live loop report contains worker errors")

    return failures


def main() -> int:
    args = parse_args()
    failures = audit_reports(
        _read_json(Path(args.capture_report)),
        _read_json(Path(args.loop_report)),
        expected=args.expected,
        min_word_ratio=args.min_word_ratio,
        min_peak=args.min_peak,
    )
    if failures:
        print("Physical microphone gate report audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Physical microphone gate report audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
