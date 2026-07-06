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

from tools import external_gate_orchestrator


class ExternalGateOrchestratorTest(unittest.TestCase):
    def test_selected_all_matches_open_gate_order(self):
        gates = external_gate_orchestrator.selected_gates("all")

        self.assertEqual(
            [gate.key for gate in gates],
            ["physical-microphone", "gemma-e4b-live", "gguf-real-server"],
        )

    def test_microphone_device_is_forwarded_only_to_physical_gate(self):
        gates = external_gate_orchestrator.selected_gates("all", microphone_device="Microphone (Realtek(R) Audio)")
        commands = {gate.key: subprocess.list2cmdline(gate.dry_run_command) for gate in gates}

        self.assertIn("--device", commands["physical-microphone"])
        self.assertIn("\"Microphone (Realtek(R) Audio)\"", commands["physical-microphone"])
        self.assertNotIn("--device", commands["gemma-e4b-live"])
        self.assertNotIn("--device", commands["gguf-real-server"])

    def test_saved_inventory_device_is_used_by_default(self):
        gates = external_gate_orchestrator.selected_gates("all")
        commands = {gate.key: subprocess.list2cmdline(gate.dry_run_command) for gate in gates}

        self.assertIn("--device 1", commands["physical-microphone"])
        self.assertNotIn("--device", commands["gemma-e4b-live"])
        self.assertNotIn("--device", commands["gguf-real-server"])

    def test_default_dry_run_writes_aggregate_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "external-gates-dry-run.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "external_gate_orchestrator.py"),
                    "--report-json",
                    str(report),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["status"], "dry-run-passed")
        self.assertEqual(payload["mode"], "dry-run")
        self.assertEqual(payload["gate_count"], 3)
        self.assertEqual(payload["microphone_device"], "1")
        self.assertEqual(payload["microphone_device_source"], "inventory")
        self.assertEqual(len(payload["results"]), 3)
        self.assertEqual(
            [gate["release_scope_status"] for gate in payload["gates"]],
            ["proven", "scoped-out", "scoped-out"],
        )
        self.assertIn("--device 1", payload["gates"][0]["command"])
        self.assertTrue(all("--dry-run" in gate["command"] for gate in payload["gates"]))
        self.assertIn("Scope: proven", result.stdout)
        self.assertIn("Scope: scoped-out", result.stdout)

    def test_dry_run_report_records_microphone_device(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "external-gates-device-dry-run.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "external_gate_orchestrator.py"),
                    "--gate",
                    "physical-microphone",
                    "--microphone-device",
                    "8",
                    "--report-json",
                    str(report),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["microphone_device"], "8")
        self.assertEqual(payload["gates"][0]["release_scope_status"], "proven")
        self.assertIn("--device", payload["gates"][0]["command"])
        self.assertIn("--device 8", payload["gates"][0]["command"])

    def test_single_gate_dry_run_limits_scope(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "gguf-dry-run.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "external_gate_orchestrator.py"),
                    "--gate",
                    "gguf-real-server",
                    "--report-json",
                    str(report),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["gate_count"], 1)
        self.assertEqual(payload["gates"][0]["key"], "gguf-real-server")
        self.assertIn("gguf_real_server_gate.py", payload["gates"][0]["command"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
