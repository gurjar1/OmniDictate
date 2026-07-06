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

from tools import open_gate_summary, physical_microphone_gate


class PhysicalMicrophoneGateTest(unittest.TestCase):
    def test_build_commands_include_capture_revalidation_loop_and_audit(self):
        args = physical_microphone_gate.parse_args([])
        args.output_dir = r"smoke_test_assets\microphone"

        commands, paths = physical_microphone_gate.build_commands(args, python_exe=r".\venv\Scripts\python.exe")
        joined = "\n".join(subprocess.list2cmdline(command) for command in commands)

        self.assertEqual(len(commands), 4)
        self.assertIn("microphone_capture_diagnostic.py", joined)
        self.assertIn("--prompt --countdown 3", joined)
        self.assertIn("--input", joined)
        self.assertIn("--source-prompted", joined)
        self.assertIn("live_microphone_smoke.py", joined)
        self.assertIn("--mode both", joined)
        self.assertIn("microphone_gate_report_audit.py", joined)
        self.assertTrue(paths["wav"].endswith("spoken-phrase-large-v3-turbo.wav"))
        self.assertTrue(paths["capture_report"].endswith("spoken-phrase-large-v3-turbo-report.json"))
        self.assertTrue(paths["loop_report"].endswith("live-loop-large-v3-turbo-report.json"))

    def test_selected_device_is_used_for_capture_and_live_loop(self):
        args = physical_microphone_gate.parse_args(["--device", "Microphone (Realtek(R) Audio)"])

        commands, _paths = physical_microphone_gate.build_commands(args, python_exe=r".\venv\Scripts\python.exe")
        capture = subprocess.list2cmdline(commands[0])
        loop = subprocess.list2cmdline(commands[2])
        revalidate = subprocess.list2cmdline(commands[1])

        self.assertIn("--device", capture)
        self.assertIn("\"Microphone (Realtek(R) Audio)\"", capture)
        self.assertIn("--device", loop)
        self.assertIn("\"Microphone (Realtek(R) Audio)\"", loop)
        self.assertNotIn("--device", revalidate)
        self.assertIn("--source-device", revalidate)
        self.assertIn("\"Microphone (Realtek(R) Audio)\"", revalidate)

    def test_ambiguous_device_name_validation_points_to_numeric_indexes(self):
        class FakeSoundDevice:
            @staticmethod
            def query_devices():
                return [
                    {"name": "Microphone (JBL Commercial CSUM06)", "max_input_channels": 1},
                    {"name": "Microphone (Other)", "max_input_channels": 1},
                    {"name": "Microphone (JBL Commercial CSUM06)", "max_input_channels": 2},
                    {"name": "Speaker", "max_input_channels": 0},
                ]

        failure = physical_microphone_gate._device_validation_failure(
            "Microphone (JBL Commercial CSUM06)",
            sd_module=FakeSoundDevice,
        )

        self.assertIn("Ambiguous input device name", failure)
        self.assertIn("0, 2", failure)
        self.assertIn("numeric --device index", failure)

    def test_reuse_capture_skips_capture_and_revalidation_commands(self):
        args = physical_microphone_gate.parse_args(["--reuse-capture"])

        commands, paths = physical_microphone_gate.build_commands(args, python_exe=r".\venv\Scripts\python.exe")
        joined = "\n".join(subprocess.list2cmdline(command) for command in commands)

        self.assertEqual(len(commands), 2)
        self.assertNotIn("microphone_capture_diagnostic.py", joined)
        self.assertIn("live_microphone_smoke.py", joined)
        self.assertIn("microphone_gate_report_audit.py", joined)
        self.assertTrue(paths["wav"].endswith("spoken-phrase-large-v3-turbo.wav"))
        self.assertTrue(paths["capture_report"].endswith("spoken-phrase-large-v3-turbo-report.json"))

    def test_dry_run_writes_summary_without_opening_microphone(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "physical-gate-dry-run.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "physical_microphone_gate.py"),
                    "--output-dir",
                    str(Path(temp_dir) / "mic"),
                    "--device",
                    "1",
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
        self.assertEqual(payload["device"], "1")
        self.assertEqual(payload["manual_prompt"]["device"], "1")
        self.assertEqual(payload["manual_prompt"]["phrase"], "hello world this is a simple speech test")
        self.assertEqual(payload["manual_prompt"]["required_loop_modes"], ["vad", "ptt"])
        self.assertIn("speak the phrase clearly", payload["manual_prompt"]["instruction"])
        self.assertEqual(len(payload["commands"]), 4)
        self.assertEqual(payload["results"], [])

    def test_reuse_capture_fails_before_live_loop_when_capture_evidence_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "physical-gate-reuse-missing.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "physical_microphone_gate.py"),
                    "--output-dir",
                    str(Path(temp_dir) / "mic"),
                    "--report-json",
                    str(report),
                    "--reuse-capture",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(payload["status"], "failed")
        self.assertTrue(payload["reuse_capture"])
        self.assertIn("--reuse-capture requires existing spoken WAV", payload["failure"])

    def test_open_gate_summary_uses_one_command_runner(self):
        physical_gate = next(gate for gate in open_gate_summary.OPEN_GATES if gate.key == "physical-microphone")

        self.assertEqual(len(physical_gate.next_command), 1)
        self.assertIn("physical_microphone_gate.py", physical_gate.next_command[0])
        self.assertIn("--report-json smoke_test_assets\\microphone\\physical-gate-report.json", physical_gate.next_command[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
