from __future__ import annotations

import unittest
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import handoff_next_action_audit


class HandoffNextActionAuditTest(unittest.TestCase):
    def test_current_handoff_passes(self):
        self.assertEqual(handoff_next_action_audit.audit_handoff_next_action(), [])

    def test_missing_marker_fails(self):
        text = """# OmniDictate Handoff

## Exact Next Action

Run `tools\\open_gate_summary.py --strict`.
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            handoff = Path(temp_dir) / "HANDOFF.md"
            handoff.write_text(text, encoding="utf-8")
            with mock.patch.object(handoff_next_action_audit, "HANDOFF", handoff):
                failures = handoff_next_action_audit.audit_handoff_next_action()

        self.assertTrue(any("publication_blocker_audit.py" in failure for failure in failures))
        self.assertTrue(any("recommended command" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main(verbosity=2)
