from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import external_gate_prerequisite_audit


class ExternalGatePrerequisiteAuditTest(unittest.TestCase):
    def test_current_audit_reports_release_scope_statuses_without_live_side_effects(self):
        status, failures, payload = external_gate_prerequisite_audit.build_prerequisite_audit()

        self.assertEqual(status, "passed")
        self.assertEqual(failures, [])
        self.assertEqual(payload["open_gate_count"], 3)
        self.assertEqual(
            [row["key"] for row in payload["gate_rows"]],
            ["physical-microphone", "gemma-e4b-live", "gguf-real-server"],
        )
        self.assertEqual(
            [row["release_scope_status"] for row in payload["gate_rows"]],
            ["proven", "scoped-out", "scoped-out"],
        )
        self.assertFalse(payload["gemma_e4b_model_dir"]["has_safetensors"])
        self.assertFalse(payload["gate_rows"][0]["ready_for_live_attempt"])
        self.assertFalse(payload["gate_rows"][1]["ready_for_live_attempt"])
        self.assertFalse(payload["gate_rows"][2]["ready_for_live_attempt"])
        self.assertEqual(
            payload["gate_rows"][0]["device_inventory_report"]["path"],
            "smoke_test_assets\\microphone\\audio-device-inventory.json",
        )
        self.assertTrue(all(row["closure_report"] for row in payload["gate_rows"]))
        self.assertTrue(all(row["closure_audit_command"] for row in payload["gate_rows"]))
        self.assertIn("microphone_gate_report_audit.py", payload["gate_rows"][0]["closure_audit_command"])
        self.assertIn("gemma_e4b_gate_report_audit.py", payload["gate_rows"][1]["closure_audit_command"])
        self.assertIn("gguf_gate_report_audit.py", payload["gate_rows"][2]["closure_audit_command"])
        self.assertIn("--device 1 --report-json", payload["gate_rows"][0]["next_command"])

    def test_e4b_becomes_ready_for_attempt_when_fixture_and_safetensors_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_storage = Path(temp_dir)
            model_dir = model_storage / "gemma-4-E4B-it"
            model_dir.mkdir(parents=True)
            (model_dir / "model.safetensors").write_bytes(b"weights")

            status, failures, payload = external_gate_prerequisite_audit.build_prerequisite_audit(model_storage)

        self.assertEqual(status, "passed")
        self.assertEqual(failures, [])
        e4b = next(row for row in payload["gate_rows"] if row["key"] == "gemma-e4b-live")
        self.assertTrue(e4b["ready_for_live_attempt"])

    def test_missing_required_file_is_reported(self):
        fake_missing = ROOT / "smoke_test_assets" / "missing-audio.wav"
        spec = {
            **external_gate_prerequisite_audit.GATE_EVIDENCE["gemma-e4b-live"],
            "required_files": [fake_missing],
        }
        patched = {
            **external_gate_prerequisite_audit.GATE_EVIDENCE,
            "gemma-e4b-live": spec,
        }
        with mock.patch.object(external_gate_prerequisite_audit, "GATE_EVIDENCE", patched):
            _status, _failures, payload = external_gate_prerequisite_audit.build_prerequisite_audit()

        e4b = next(row for row in payload["gate_rows"] if row["key"] == "gemma-e4b-live")
        self.assertIn("smoke_test_assets\\missing-audio.wav", e4b["missing_files"])

    def test_cli_writes_report_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "external-gate-prerequisites.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "external_gate_prerequisite_audit.py"),
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
        self.assertEqual(payload["status"], "passed")
        self.assertIn("physical-microphone", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
