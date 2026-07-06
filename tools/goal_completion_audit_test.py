from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import goal_completion_audit


class GoalCompletionAuditTest(unittest.TestCase):
    def test_current_goal_completion_audit_passes(self):
        self.assertEqual(goal_completion_audit.main(), 0)

    def test_tampered_decision_matrix_keeps_goal_incomplete_audit_failing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            matrix = Path(temp_dir) / "release-decision-matrix.json"
            matrix.write_text(
                json.dumps(
                    {
                        "status": "ready",
                        "publish_ready": True,
                        "summary": {
                            "final_artifact_status": "ready",
                            "open_gate_count": 0,
                        },
                        "gate_rows": [],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(goal_completion_audit, "DECISION_MATRIX", matrix):
                self.assertEqual(goal_completion_audit.main(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
