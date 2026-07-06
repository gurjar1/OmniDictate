from __future__ import annotations

import unittest
from unittest import mock

import release_readiness_audit


class ReleaseReadinessAuditTest(unittest.TestCase):
    def test_current_release_readiness_audit_passes(self):
        self.assertEqual(release_readiness_audit.main(), 0)

    def test_canonical_report_references_are_required(self):
        audit = release_readiness_audit.Audit()

        with mock.patch.object(release_readiness_audit, "_read", return_value="missing canonical reports"):
            release_readiness_audit.check_canonical_release_report_references(audit)

        self.assertTrue(
            any("Canonical release report is not referenced" in failure for failure in audit.failures)
        )
        self.assertTrue(
            any("HANDOFF.md Exact Next Action must keep report refresh visible" in failure for failure in audit.failures)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
