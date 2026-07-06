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

from tools import publication_blocker_audit


SCOPE_DOC = """# Scope Decisions

Allowed statuses:

- `pending`: the gate remains a publication blocker.
- `proven`: the gate has a passing report
- `scoped-out`: the user explicitly moved the gate

For a `scoped-out` row, `User authorization` must include
`User authorized ... on YYYY-MM-DD`, and `Release note/checklist update` must
include `Updated ... on YYYY-MM-DD`.

| Gate key | Release scope status | Required evidence | Current evidence | User authorization | Release note/checklist update |
| --- | --- | --- | --- | --- | --- |
| `physical-microphone` | `pending` | `smoke_test_assets\\microphone\\physical-gate-report.json` with `status: passed` | still open | Not applicable while pending | Not applicable while pending |
| `gemma-e4b-live` | `pending` | `smoke_test_assets\\gemma-e4b-gate-report.json` with `status: passed` | still open | Not applicable while pending | Not applicable while pending |
| `gguf-real-server` | `pending` | `smoke_test_assets\\gguf\\real-server-gate-report.json` with `status: passed` | still open | Not applicable while pending | Not applicable while pending |

Current decision: publication remains blocked
"""


class PublicationBlockerAuditTest(unittest.TestCase):
    def test_pending_scope_gate_blocks_publication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            final_public = root / "final-public.json"
            final_audit = root / "final-audit.json"
            scope_doc = root / "scope.md"
            final_public.write_text(json.dumps({"status": "passed"}), encoding="utf-8")
            final_audit.write_text(
                json.dumps({"status": "ready", "installer_sha256": "ABC123"}),
                encoding="utf-8",
            )
            scope_doc.write_text(SCOPE_DOC, encoding="utf-8")

            status, failures, payload = publication_blocker_audit.audit_publication_blockers(
                final_public,
                final_audit,
                scope_doc,
            )

        self.assertEqual(status, "blocked")
        self.assertEqual(failures, [])
        self.assertEqual(payload["open_gate_count"], 3)
        self.assertEqual(payload["scope_decision_status"], "passed")
        self.assertEqual(payload["schema_version"], 1)
        self.assertRegex(payload["generated_at_utc"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertEqual(
            payload["open_gates"],
            ["physical-microphone", "gemma-e4b-live", "gguf-real-server"],
        )
        self.assertEqual(
            [gate["key"] for gate in payload["open_gate_details"]],
            ["physical-microphone", "gemma-e4b-live", "gguf-real-server"],
        )
        self.assertEqual(payload["open_gate_details"][0]["release_scope_status"], "pending")
        self.assertIn("physical_microphone_gate.py", payload["open_gate_details"][0]["next_commands"][0])
        self.assertIn("--device 1 --report-json", payload["open_gate_details"][0]["next_commands"][0])
        self.assertEqual(payload["final_public_status"], "passed")
        self.assertEqual(payload["final_artifact_status"], "ready")
        self.assertEqual(payload["installer_sha256"], "ABC123")

    def test_missing_or_failed_final_reports_are_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            final_public = root / "final-public.json"
            final_audit = root / "final-audit.json"
            final_public.write_text(json.dumps({"status": "failed"}), encoding="utf-8")
            final_audit.write_text(json.dumps({"status": "not-ready"}), encoding="utf-8")

            status, failures, _payload = publication_blocker_audit.audit_publication_blockers(final_public, final_audit)

        self.assertEqual(status, "invalid")
        self.assertTrue(any("not passed" in failure for failure in failures))
        self.assertTrue(any("not ready" in failure for failure in failures))
        self.assertTrue(any("missing installer SHA256" in failure for failure in failures))

    def test_authorized_scoped_out_decisions_make_publication_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            final_public = root / "final-public.json"
            final_audit = root / "final-audit.json"
            scope_doc = root / "scope.md"
            final_public.write_text(json.dumps({"status": "passed"}), encoding="utf-8")
            final_audit.write_text(
                json.dumps({"status": "ready", "installer_sha256": "ABC123"}),
                encoding="utf-8",
            )
            scope_doc.write_text(
                SCOPE_DOC.replace("| `pending` |", "| `scoped-out` |").replace(
                    "Not applicable while pending | Not applicable while pending",
                    "User authorized scope-out on 2026-07-05 | Updated release notes/checklist on 2026-07-05",
                ),
                encoding="utf-8",
            )

            status, failures, payload = publication_blocker_audit.audit_publication_blockers(
                final_public,
                final_audit,
                scope_doc,
            )

        self.assertEqual(status, "ready")
        self.assertEqual(failures, [])
        self.assertEqual(payload["open_gate_count"], 0)
        self.assertEqual(payload["open_gates"], [])

    def test_cli_writes_json_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "publication-blockers.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "publication_blocker_audit.py"),
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
        self.assertEqual(payload["open_gate_count"], 0)
        self.assertIn("open_gate_details", payload)
        self.assertIn("installer_sha256", payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
