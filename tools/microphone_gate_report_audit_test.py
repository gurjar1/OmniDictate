from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.microphone_gate_report_audit import audit_reports
from tools.whisper_fixture_test import DEFAULT_PHRASE


def _capture_report(transcript: str = DEFAULT_PHRASE, prompted: bool = True, peak: float = 0.08) -> dict:
    return {
        "source": "spoken-phrase-large-v3-turbo.wav",
        "duration_seconds": 7.0,
        "rms": 0.03,
        "peak": peak,
        "active_ratio": 0.4,
        "clipping_ratio": 0.0,
        "transcript": transcript,
        "prompted": prompted,
        "expected": DEFAULT_PHRASE,
        "device": "Microphone (Realtek(R) Audio)",
    }


def _loop_report(outcome: str = "passed") -> dict:
    return {
        "model": "large-v3-turbo",
        "mode": "both",
        "manual": True,
        "countdown": 3.0,
        "device": "Microphone (Realtek(R) Audio)",
        "capture_only": False,
        "expected": DEFAULT_PHRASE,
        "min_word_ratio": 0.6,
        "max_transcripts": 1,
        "outcome": outcome,
        "failure": "",
        "failed_mode": "",
        "results": [
            {"mode": "vad", "transcript": DEFAULT_PHRASE},
            {"mode": "ptt", "transcript": DEFAULT_PHRASE},
        ],
        "transcripts": [DEFAULT_PHRASE, DEFAULT_PHRASE],
        "statuses": ["Listening...", "Recording (VAD)...", "Recording (PTT)..."],
        "errors": [],
    }


class MicrophoneGateReportAuditTest(unittest.TestCase):
    def test_valid_reports_close_gate(self):
        self.assertEqual(audit_reports(_capture_report(), _loop_report()), [])

    def test_tiny_mismatch_does_not_close_gate(self):
        capture = _capture_report(transcript="We're open to the world.", peak=0.02)
        loop = _loop_report(outcome="failed")
        loop["results"] = []
        loop["transcripts"] = ["We're open to the world."]
        loop["failure"] = "AssertionError: Transcript did not match"
        loop["failed_mode"] = "vad"

        failures = audit_reports(capture, loop)

        self.assertIn("capture report transcript does not meet the word-match threshold", failures)
        self.assertIn("live loop report outcome is not passed", failures)
        self.assertIn("live loop report must contain passing VAD and PTT results", failures)

    def test_selected_device_mismatch_does_not_close_gate(self):
        capture = _capture_report()
        loop = _loop_report()
        loop["device"] = "Different microphone"

        failures = audit_reports(capture, loop)

        self.assertIn("capture report device does not match live loop report device", failures)

    def test_cli_reports_failure_for_unprompted_low_level_capture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            capture_path = temp_path / "capture.json"
            loop_path = temp_path / "loop.json"
            capture_path.write_text(json.dumps(_capture_report(prompted=False, peak=0.001)), encoding="utf-8")
            loop_path.write_text(json.dumps(_loop_report()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "microphone_gate_report_audit.py"),
                    "--capture-report",
                    str(capture_path),
                    "--loop-report",
                    str(loop_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("not created from a prompted human speech run", result.stdout)
        self.assertIn("peak is below", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
