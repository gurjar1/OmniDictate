from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import open_gate_summary


class OpenGateSummaryTest(unittest.TestCase):
    def test_json_includes_release_scope_statuses(self):
        payloads = open_gate_summary._gate_payloads()

        self.assertEqual(
            [payload["release_scope_status"] for payload in payloads],
            ["proven", "scoped-out", "scoped-out"],
        )

    def test_text_output_prints_scope_status(self):
        previous_argv = sys.argv
        buffer = io.StringIO()
        try:
            sys.argv = ["open_gate_summary.py", "--strict"]
            with contextlib.redirect_stdout(buffer):
                rc = open_gate_summary.main()
        finally:
            sys.argv = previous_argv

        self.assertEqual(rc, 0)
        self.assertIn("Scope: proven", buffer.getvalue())
        self.assertIn("Scope: scoped-out", buffer.getvalue())

    def test_cli_json_shape_has_scope_doc(self):
        previous_argv = sys.argv
        buffer = io.StringIO()
        try:
            sys.argv = ["open_gate_summary.py", "--json", "--strict"]
            with contextlib.redirect_stdout(buffer):
                rc = open_gate_summary.main()
        finally:
            sys.argv = previous_argv
        payload = json.loads(buffer.getvalue())

        self.assertEqual(rc, 0)
        self.assertEqual(payload["scope_decisions_doc"], open_gate_summary.SCOPE_DECISIONS_DOC)
        self.assertEqual(payload["open_gates"][0]["release_scope_status"], "proven")

    def test_physical_gate_uses_recommended_audio_device_when_inventory_exists(self):
        payloads = open_gate_summary._gate_payloads()

        self.assertIn("--device 1 --report-json", payloads[0]["next_command"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
