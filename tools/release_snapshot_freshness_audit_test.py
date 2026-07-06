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

from tools import (
    external_gate_orchestrator,
    external_gate_closure_audit,
    external_gate_prerequisite_audit,
    github_release_preflight,
    publication_blocker_audit,
    release_decision_matrix_report,
    release_snapshot_freshness_audit,
    release_status_report,
)


class ReleaseSnapshotFreshnessAuditTest(unittest.TestCase):
    def test_matching_reports_pass_even_when_timestamps_differ(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            publication_path = root / "publication-blockers.json"
            release_status_path = root / "release-status-report.json"
            github_preflight_path = root / "github-release-preflight.json"
            external_gates_path = root / "external-gates-dry-run.json"
            prerequisites_path = root / "external-gate-prerequisites.json"
            closure_audit_path = root / "external-gate-closure-audit.json"
            decision_matrix_path = root / "release-decision-matrix.json"

            _status, _failures, publication_payload = publication_blocker_audit.audit_publication_blockers()
            _status, _failures, release_payload = release_status_report.build_release_status()
            _status, _failures, github_payload = github_release_preflight.build_github_release_preflight()
            external_payload = release_snapshot_freshness_audit._expected_external_gate_dry_run()
            _status, _failures, prerequisites_payload = external_gate_prerequisite_audit.build_prerequisite_audit()
            _status, _failures, closure_payload = external_gate_closure_audit.build_closure_audit()
            _status, _failures, decision_matrix_payload = release_decision_matrix_report.build_release_decision_matrix()
            publication_payload["generated_at_utc"] = "2000-01-01T00:00:00Z"
            release_payload["generated_at_utc"] = "2000-01-01T00:00:00Z"
            release_payload["publication"]["generated_at_utc"] = "2000-01-01T00:00:00Z"
            github_payload["generated_at_utc"] = "2000-01-01T00:00:00Z"
            github_payload["release_status_report"]["generated_at_utc"] = "2000-01-01T00:00:00Z"
            github_payload["release_status_report"]["publication"]["generated_at_utc"] = "2000-01-01T00:00:00Z"
            prerequisites_payload["generated_at_utc"] = "2000-01-01T00:00:00Z"
            closure_payload["generated_at_utc"] = "2000-01-01T00:00:00Z"
            decision_matrix_payload["generated_at_utc"] = "2000-01-01T00:00:00Z"
            publication_path.write_text(json.dumps(publication_payload), encoding="utf-8")
            release_status_path.write_text(json.dumps(release_payload), encoding="utf-8")
            github_preflight_path.write_text(json.dumps(github_payload), encoding="utf-8")
            external_gates_path.write_text(json.dumps(external_payload), encoding="utf-8")
            prerequisites_path.write_text(json.dumps(prerequisites_payload), encoding="utf-8")
            closure_audit_path.write_text(json.dumps(closure_payload), encoding="utf-8")
            decision_matrix_path.write_text(json.dumps(decision_matrix_payload), encoding="utf-8")

            status, failures, payload = release_snapshot_freshness_audit.audit_release_snapshots(
                publication_path,
                release_status_path,
                github_preflight_path,
                external_gates_path,
                prerequisites_path,
                closure_audit_path,
                decision_matrix_path,
            )

        self.assertEqual(status, "passed")
        self.assertEqual(failures, [])
        self.assertEqual(payload["ignored_keys"], ["generated_at_utc"])

    def test_stale_open_gate_set_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            publication_path = root / "publication-blockers.json"
            release_status_path = root / "release-status-report.json"
            github_preflight_path = root / "github-release-preflight.json"
            external_gates_path = root / "external-gates-dry-run.json"
            prerequisites_path = root / "external-gate-prerequisites.json"
            closure_audit_path = root / "external-gate-closure-audit.json"
            decision_matrix_path = root / "release-decision-matrix.json"

            _status, _failures, publication_payload = publication_blocker_audit.audit_publication_blockers()
            _status, _failures, release_payload = release_status_report.build_release_status()
            _status, _failures, github_payload = github_release_preflight.build_github_release_preflight()
            external_payload = release_snapshot_freshness_audit._expected_external_gate_dry_run()
            _status, _failures, prerequisites_payload = external_gate_prerequisite_audit.build_prerequisite_audit()
            _status, _failures, closure_payload = external_gate_closure_audit.build_closure_audit()
            _status, _failures, decision_matrix_payload = release_decision_matrix_report.build_release_decision_matrix()
            publication_payload["open_gates"] = ["old-gate"]
            release_payload["open_gate_count"] = 99
            github_payload["pending_release_scope_gates"] = ["old-gate"]
            external_payload["gates"][0]["command"] = "old command"
            prerequisites_payload["gate_rows"][0]["missing_reports"] = ["old report"]
            closure_payload["gate_rows"][0]["closure_state"] = "old-state"
            decision_matrix_payload["gate_rows"][0]["next_command"] = "old command"
            publication_path.write_text(json.dumps(publication_payload), encoding="utf-8")
            release_status_path.write_text(json.dumps(release_payload), encoding="utf-8")
            github_preflight_path.write_text(json.dumps(github_payload), encoding="utf-8")
            external_gates_path.write_text(json.dumps(external_payload), encoding="utf-8")
            prerequisites_path.write_text(json.dumps(prerequisites_payload), encoding="utf-8")
            closure_audit_path.write_text(json.dumps(closure_payload), encoding="utf-8")
            decision_matrix_path.write_text(json.dumps(decision_matrix_payload), encoding="utf-8")

            status, failures, _payload = release_snapshot_freshness_audit.audit_release_snapshots(
                publication_path,
                release_status_path,
                github_preflight_path,
                external_gates_path,
                prerequisites_path,
                closure_audit_path,
                decision_matrix_path,
            )

        self.assertEqual(status, "failed")
        self.assertTrue(any("publication_report.open_gates differs" in failure for failure in failures))
        self.assertTrue(any("release_status_report.open_gate_count differs" in failure for failure in failures))
        self.assertTrue(
            any("github_preflight_report.pending_release_scope_gates differs" in failure for failure in failures)
        )
        self.assertTrue(any("external_gates_report.gates differs" in failure for failure in failures))
        self.assertTrue(any("prerequisites_report.gate_rows differs" in failure for failure in failures))
        self.assertTrue(any("closure_audit_report.gate_rows differs" in failure for failure in failures))
        self.assertTrue(any("decision_matrix_report.gate_rows differs" in failure for failure in failures))

    def test_cli_uses_default_reports(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "release_snapshot_freshness_audit.py"),
                "--json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["status"], "passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
