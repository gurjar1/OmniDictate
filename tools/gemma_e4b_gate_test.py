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

from tools import gemma_e4b_gate, open_gate_summary


class GemmaE4BGateTest(unittest.TestCase):
    def test_build_commands_include_preflight_smoke_and_audit(self):
        args = gemma_e4b_gate.parse_args([])
        args.output_dir = r"smoke_test_assets"

        commands, paths = gemma_e4b_gate.build_commands(args, python_exe=r".\venv\Scripts\python.exe")
        joined = "\n".join(subprocess.list2cmdline(command) for command in commands)

        self.assertEqual(len(commands), 3)
        self.assertIn("gemma_model_preflight.py", joined)
        self.assertIn("--require-local", joined)
        self.assertIn("gemma_smoke_test.py", joined)
        self.assertIn("--runtime transformers", joined)
        self.assertIn("--model google/gemma-4-E4B-it", joined)
        self.assertIn("--audio-mode hybrid-whisper", joined)
        self.assertIn("gemma_e4b_gate_report_audit.py", joined)
        self.assertTrue(paths["preflight_report"].endswith("gemma-e4b-preflight.json"))
        self.assertTrue(paths["smoke_report"].endswith("gemma-e4b-live-smoke.json"))

    def test_dry_run_writes_summary_without_loading_e4b(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "e4b-gate-dry-run.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "gemma_e4b_gate.py"),
                    "--output-dir",
                    str(Path(temp_dir) / "e4b"),
                    "--report-json",
                    str(report),
                    "--dry-run",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["status"], "dry-run")
        self.assertEqual(payload["model"], "google/gemma-4-E4B-it")
        self.assertEqual(len(payload["commands"]), 3)
        self.assertEqual(payload["results"], [])

    def test_missing_fixture_fails_before_loading_e4b(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "e4b-gate-missing-fixture.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "gemma_e4b_gate.py"),
                    "--audio",
                    str(Path(temp_dir) / "missing.wav"),
                    "--image",
                    str(Path(temp_dir) / "missing.png"),
                    "--output-dir",
                    str(Path(temp_dir) / "e4b"),
                    "--report-json",
                    str(report),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(payload["status"], "failed")
        self.assertIn("Missing E4B smoke fixture", payload["failure"])
        self.assertEqual(payload["results"], [])

    def test_open_gate_summary_uses_one_command_runner(self):
        gate = next(gate for gate in open_gate_summary.OPEN_GATES if gate.key == "gemma-e4b-live")

        self.assertEqual(len(gate.next_command), 1)
        self.assertIn("gemma_e4b_gate.py", gate.next_command[0])
        self.assertIn("--model google/gemma-4-E4B-it", gate.next_command[0])
        self.assertIn("--report-json smoke_test_assets\\gemma-e4b-gate-report.json", gate.next_command[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
