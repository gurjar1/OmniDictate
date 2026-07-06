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

from tools import physical_microphone_run_card


class PhysicalMicrophoneRunCardTest(unittest.TestCase):
    def test_build_run_card_prints_human_prompt_fields(self):
        report = {
            "status": "dry-run",
            "model": "large-v3-turbo",
            "expected": "hello world this is a simple speech test",
            "min_word_ratio": 0.6,
            "device": "1",
            "duration_seconds": 7.0,
            "countdown_seconds": 3.0,
            "timeout_seconds": 40.0,
            "manual_prompt": {
                "phrase": "hello world this is a simple speech test",
                "device": "1",
                "countdown_seconds": 3.0,
                "recording_duration_seconds": 7.0,
                "live_loop_timeout_seconds": 40.0,
                "min_word_ratio": 0.6,
                "required_loop_modes": ["vad", "ptt"],
                "instruction": "Speak clearly.",
            },
            "paths": {
                "wav": "spoken.wav",
                "capture_report": "capture.json",
                "loop_report": "loop.json",
            },
            "commands": [
                r".\venv\Scripts\python.exe tools\physical_microphone_gate.py --dry-run --report-json smoke_test_assets\microphone\physical-gate-dry-run.json --device 1"
            ],
        }

        lines = physical_microphone_run_card.build_run_card(report)
        text = "\n".join(lines)

        self.assertIn("Physical Microphone Gate Run Card", text)
        self.assertIn("Device: 1", text)
        self.assertIn("Phrase: hello world this is a simple speech test", text)
        self.assertIn("Required modes: VAD, PTT", text)
        self.assertIn("Pass rule: Speak clearly.", text)
        self.assertIn("tools\\physical_microphone_gate.py", text)
        self.assertIn("--device 1", text)
        self.assertIn("physical-gate-report.json", text)
        self.assertNotIn("--dry-run", text)

    def test_cli_reads_report_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "physical-gate-dry-run.json"
            report.write_text(
                json.dumps(
                    {
                        "status": "dry-run",
                        "model": "large-v3-turbo",
                        "device": "1",
                        "manual_prompt": {
                            "phrase": "hello world this is a simple speech test",
                            "device": "1",
                            "required_loop_modes": ["vad", "ptt"],
                        },
                        "paths": {},
                        "commands": [],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "physical_microphone_run_card.py"),
                    "--report-json",
                    str(report),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Device: 1", result.stdout)
        self.assertIn("Required modes: VAD, PTT", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
