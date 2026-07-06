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

from tools import release_status_report


class ReleaseStatusReportTest(unittest.TestCase):
    def test_build_release_status_reports_current_ready_state(self):
        status, failures, payload = release_status_report.build_release_status()

        self.assertEqual(status, "ready")
        self.assertEqual(failures, [])
        self.assertEqual(payload["schema_version"], 1)
        self.assertRegex(payload["generated_at_utc"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertEqual(payload["open_gate_count"], 3)
        self.assertEqual(payload["publication"]["schema_version"], 1)
        self.assertIn("generated_at_utc", payload["publication"])
        self.assertEqual(payload["publication"]["final_public_status"], "passed")
        self.assertEqual(payload["publication"]["final_artifact_status"], "ready")
        self.assertEqual(
            [gate["key"] for gate in payload["open_gates"]],
            ["physical-microphone", "gemma-e4b-live", "gguf-real-server"],
        )
        self.assertEqual(
            [gate["release_scope_status"] for gate in payload["open_gates"]],
            ["proven", "scoped-out", "scoped-out"],
        )
        self.assertEqual(payload["publication"]["open_gate_count"], 0)
        self.assertEqual(payload["publication"]["open_gates"], [])
        self.assertEqual(len(payload["next_commands"]), 3)
        self.assertEqual(len(payload["next_preparation_commands"]), 3)
        self.assertIn("physical_microphone_run_card.py", payload["next_preparation_command"])
        self.assertTrue(any("gemma_model_preflight.py" in command for command in payload["next_preparation_commands"]))
        self.assertTrue(any("gguf_server_probe.py" in command for command in payload["next_preparation_commands"]))
        self.assertEqual(len(payload["next_recommended_commands"]), 3)
        self.assertIn("physical_microphone_gate.py", payload["next_recommended_command"])
        self.assertIn("--device 1 --report-json", payload["next_commands"][0])
        self.assertIn("--device 1 --report-json", payload["open_gates"][0]["next_command"][0])
        self.assertIn(
            "smoke_test_assets\\microphone\\audio-device-inventory.json",
            payload["microphone_device_inventory_report"],
        )
        self.assertIn("external_gate_orchestrator.py", payload["external_gate_dry_run_command"])
        self.assertIn("--microphone-device", payload["external_gate_selected_microphone_command"])
        self.assertIn("--microphone-device 1", payload["external_gate_selected_microphone_command"])
        self.assertNotIn("<", payload["external_gate_selected_microphone_command"])
        self.assertEqual(
            payload["phase4_checklist"],
            "docs/implementation-plans-and-checklists/phase-4-release-execution.md",
        )

    def test_cli_writes_report_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "release-status-report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "release_status_report.py"),
                    "--json",
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
        self.assertEqual(payload["status"], "ready")
        self.assertIn("physical_microphone_gate.py", result.stdout)
        self.assertIn("physical_microphone_run_card.py", result.stdout)
        self.assertIn("--device 1 --report-json", result.stdout)
        self.assertIn("physical_microphone_gate.py", payload["next_recommended_command"])
        self.assertIn("external_gate_orchestrator.py", result.stdout)
        self.assertEqual(payload["publication"]["open_gate_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
