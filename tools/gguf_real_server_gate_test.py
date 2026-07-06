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

from tools import gguf_real_server_gate, open_gate_summary


class GGUFRealServerGateTest(unittest.TestCase):
    def test_build_commands_include_probe_smoke_and_audit(self):
        args = gguf_real_server_gate.parse_args(["--server-implementation", "LM Studio"])
        args.output_dir = r"smoke_test_assets\gguf"

        commands, paths = gguf_real_server_gate.build_commands(args, python_exe=r".\venv\Scripts\python.exe")
        joined = "\n".join(subprocess.list2cmdline(command) for command in commands)

        self.assertEqual(len(commands), 3)
        self.assertIn("gguf_server_probe.py", joined)
        self.assertIn("--url http://127.0.0.1:8080/v1", joined)
        self.assertIn("gemma_smoke_test.py", joined)
        self.assertIn("--runtime gguf-server", joined)
        self.assertIn("--gguf-url http://127.0.0.1:8080/v1", joined)
        self.assertIn("gguf_gate_report_audit.py", joined)
        self.assertIn("--server-implementation \"LM Studio\"", joined)
        self.assertTrue(paths["probe_report"].endswith("real-server-probe.json"))
        self.assertTrue(paths["smoke_report"].endswith("real-server-smoke.json"))

    def test_dry_run_writes_summary_without_contacting_server(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "gguf-gate-dry-run.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "gguf_real_server_gate.py"),
                    "--server-implementation",
                    "LM Studio",
                    "--output-dir",
                    str(Path(temp_dir) / "gguf"),
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
        self.assertEqual(payload["server_implementation"], "LM Studio")
        self.assertEqual(len(payload["commands"]), 3)
        self.assertEqual(payload["results"], [])

    def test_mock_label_is_rejected_before_dry_run(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "gguf_real_server_gate.py"),
                "--server-implementation",
                "mock server",
                "--dry-run",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("must name a real server", result.stdout)

    def test_missing_fixture_fails_before_contacting_server(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "gguf-gate-missing-fixture.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "gguf_real_server_gate.py"),
                    "--server-implementation",
                    "LM Studio",
                    "--audio",
                    str(Path(temp_dir) / "missing.wav"),
                    "--image",
                    str(Path(temp_dir) / "missing.png"),
                    "--output-dir",
                    str(Path(temp_dir) / "gguf"),
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
        self.assertIn("Missing GGUF smoke fixture", payload["failure"])
        self.assertEqual(payload["results"], [])

    def test_open_gate_summary_uses_one_command_runner(self):
        gate = next(gate for gate in open_gate_summary.OPEN_GATES if gate.key == "gguf-real-server")

        self.assertEqual(len(gate.next_command), 1)
        self.assertIn("gguf_real_server_gate.py", gate.next_command[0])
        self.assertIn("--server-implementation \"LM Studio\"", gate.next_command[0])
        self.assertIn("--report-json smoke_test_assets\\gguf\\real-server-gate-report.json", gate.next_command[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
