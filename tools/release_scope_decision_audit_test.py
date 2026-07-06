from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import release_scope_decision_audit


VALID_DOC = """# Scope Decisions

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


class ReleaseScopeDecisionAuditTest(unittest.TestCase):
    def test_current_scope_decision_doc_passes(self):
        status, failures, payload = release_scope_decision_audit.audit_scope_decisions()

        self.assertEqual(status, "passed")
        self.assertEqual(failures, [])
        self.assertEqual(
            payload["gate_statuses"],
            {
                "physical-microphone": "proven",
                "gemma-e4b-live": "scoped-out",
                "gguf-real-server": "scoped-out",
            },
        )

    def test_scoped_out_without_authorization_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            doc = Path(temp_dir) / "scope.md"
            doc.write_text(VALID_DOC.replace("`pending` | `smoke_test_assets\\gemma", "`scoped-out` | `smoke_test_assets\\gemma"), encoding="utf-8")

            status, failures, _payload = release_scope_decision_audit.audit_scope_decisions(doc)

        self.assertEqual(status, "failed")
        self.assertTrue(any("without explicit dated user authorization" in failure for failure in failures))
        self.assertTrue(any("without a dated release note/checklist update marker" in failure for failure in failures))

    def test_scoped_out_requires_dated_markers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            doc = Path(temp_dir) / "scope.md"
            text = VALID_DOC.replace(
                "| `gemma-e4b-live` | `pending` | `smoke_test_assets\\gemma-e4b-gate-report.json` with `status: passed` | still open | Not applicable while pending | Not applicable while pending |",
                "| `gemma-e4b-live` | `scoped-out` | `smoke_test_assets\\gemma-e4b-gate-report.json` with `status: passed` | intentionally deferred | User approved scoped-out release | Release notes updated |",
            )
            doc.write_text(text, encoding="utf-8")

            status, failures, _payload = release_scope_decision_audit.audit_scope_decisions(doc)

        self.assertEqual(status, "failed")
        self.assertTrue(any("gemma-e4b-live is scoped-out without explicit dated user authorization" in failure for failure in failures))
        self.assertTrue(any("gemma-e4b-live is scoped-out without a dated release note/checklist update marker" in failure for failure in failures))

    def test_scoped_out_with_dated_markers_passes_scope_audit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            doc = Path(temp_dir) / "scope.md"
            text = VALID_DOC.replace(
                "| `gemma-e4b-live` | `pending` | `smoke_test_assets\\gemma-e4b-gate-report.json` with `status: passed` | still open | Not applicable while pending | Not applicable while pending |",
                "| `gemma-e4b-live` | `scoped-out` | `smoke_test_assets\\gemma-e4b-gate-report.json` with `status: passed` | intentionally deferred | User authorized scope-out on 2026-07-05 | Updated release notes/checklist on 2026-07-05 |",
            )
            doc.write_text(text, encoding="utf-8")

            status, failures, payload = release_scope_decision_audit.audit_scope_decisions(doc)

        self.assertEqual(status, "passed")
        self.assertEqual(failures, [])
        self.assertEqual(payload["gate_statuses"]["gemma-e4b-live"], "scoped-out")

    def test_unknown_or_missing_rows_fail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            doc = Path(temp_dir) / "scope.md"
            text = VALID_DOC.replace("| `gguf-real-server` |", "| `surprise-gate` |")
            doc.write_text(text, encoding="utf-8")

            status, failures, _payload = release_scope_decision_audit.audit_scope_decisions(doc)

        self.assertEqual(status, "failed")
        self.assertTrue(any("missing release scope decision row: gguf-real-server" in failure for failure in failures))
        self.assertTrue(any("unknown release scope decision row: surprise-gate" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main(verbosity=2)
