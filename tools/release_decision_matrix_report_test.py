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

from tools import release_decision_matrix_report


class ReleaseDecisionMatrixReportTest(unittest.TestCase):
    def test_build_matrix_reports_current_ready_state(self):
        status, failures, payload = release_decision_matrix_report.build_release_decision_matrix()

        self.assertEqual(status, "ready")
        self.assertEqual(failures, [])
        self.assertTrue(payload["publish_ready"])
        self.assertEqual(payload["summary"]["final_public_status"], "passed")
        self.assertEqual(payload["summary"]["final_artifact_status"], "ready")
        self.assertEqual(payload["summary"]["open_gate_count"], 3)
        self.assertEqual(
            [row["key"] for row in payload["gate_rows"]],
            ["physical-microphone", "gemma-e4b-live", "gguf-real-server"],
        )
        self.assertEqual(
            [row["release_scope_status"] for row in payload["gate_rows"]],
            ["proven", "scoped-out", "scoped-out"],
        )
        self.assertTrue(all(row["next_command"] for row in payload["gate_rows"]))
        self.assertEqual(len(payload["next_preparation_commands"]), 3)
        self.assertIn("physical_microphone_run_card.py", payload["next_preparation_commands"][0])
        self.assertIn("physical_microphone_run_card.py", payload["gate_rows"][0]["preparation_command"])
        self.assertIn("gemma_model_preflight.py", payload["gate_rows"][1]["preparation_command"])
        self.assertIn("gguf_server_probe.py", payload["gate_rows"][2]["preparation_command"])
        self.assertTrue(all(row["dry_run_command"] for row in payload["gate_rows"]))
        self.assertTrue(all("ready_for_live_attempt" in row for row in payload["gate_rows"]))
        self.assertTrue(all(row["closure_report"] for row in payload["gate_rows"]))
        self.assertTrue(all(row["closure_audit_command"] for row in payload["gate_rows"]))
        self.assertTrue(all(row["closure_state"] for row in payload["gate_rows"]))
        self.assertTrue(all(row["scope_decision_target"] for row in payload["gate_rows"]))
        self.assertIn("release-status-report.json", payload["reports"]["release_status"])
        self.assertIn("external-gates-dry-run.json", payload["reports"]["external_gates_dry_run"])
        self.assertIn("external-gate-prerequisites.json", payload["reports"]["external_gate_prerequisites"])
        self.assertIn("external-gate-closure-audit.json", payload["reports"]["external_gate_closure_audit"])

    def test_cli_writes_report_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "release-decision-matrix.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "release_decision_matrix_report.py"),
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
        self.assertIn("gemma_model_preflight.py", result.stdout)
        self.assertIn("gguf_server_probe.py", result.stdout)
        self.assertEqual(payload["gate_rows"][0]["release_scope_status"], "proven")

    def test_mismatched_external_gate_report_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            external_report = Path(temp_dir) / "external-gates-dry-run.json"
            prerequisites_report = Path(temp_dir) / "external-gate-prerequisites.json"
            closure_report = Path(temp_dir) / "external-gate-closure-audit.json"
            github_report = Path(temp_dir) / "github-release-preflight.json"
            external_report.write_text(
                json.dumps(
                    {
                        "status": "dry-run-passed",
                        "gates": [
                            {
                                "key": "old-gate",
                                "command": "old command",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            prerequisites_report.write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "gate_rows": [
                            {
                                "key": "old-gate",
                                "ready_for_live_attempt": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            closure_report.write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "gate_rows": [
                            {
                                "key": "old-gate",
                                "closure_state": "eligible-for-proven",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            github_report.write_text(json.dumps({"status": "blocked", "publish_ready": False}), encoding="utf-8")

            status, failures, _payload = release_decision_matrix_report.build_release_decision_matrix(
                external_report,
                prerequisites_report,
                closure_report,
                github_report,
            )

        self.assertEqual(status, "invalid")
        self.assertTrue(
            any("external gate dry-run report does not match current open gate set" in failure for failure in failures)
        )
        self.assertTrue(
            any("external gate prerequisites report does not match current open gate set" in failure for failure in failures)
        )
        self.assertTrue(
            any("external gate closure audit report does not match current open gate set" in failure for failure in failures)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
