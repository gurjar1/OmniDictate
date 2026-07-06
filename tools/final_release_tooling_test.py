from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import final_release_preflight, open_gate_summary


class FinalReleaseToolingTest(unittest.TestCase):
    def test_preflight_commands_use_final_public_paths(self):
        commands = final_release_preflight._final_commands()
        joined = "\n".join(commands)

        self.assertEqual(commands[0], "$env:OMNIDICTATE_PACKAGE_PROFILE='whisper-only'")
        self.assertIn("dist-whisper-final", joined)
        self.assertIn("installer-whisper-final", joined)
        self.assertIn("OmniDictate_Setup_v3.0.0.exe", joined)
        self.assertNotIn("whisper-release-smoke", joined)
        self.assertNotIn("OmniDictate_Setup_v3.0.0-whisper", joined)
        self.assertNotIn("--package-profile", joined)

    def test_preflight_json_shape(self):
        output = io.StringIO()
        original_argv = sys.argv
        sys.argv = ["final_release_preflight.py", "--json"]
        try:
            with redirect_stdout(output):
                rc = final_release_preflight.main()
        finally:
            sys.argv = original_argv

        payload = json.loads(output.getvalue())
        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "ready-to-run")
        self.assertEqual(payload["final_installer"], r"smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe")
        self.assertEqual(payload["final_bundle"], r"smoke_test_assets\packaging\dist-whisper-final\OmniDictate")
        self.assertEqual(payload["final_dist"], r"smoke_test_assets\packaging\dist-whisper-final")
        self.assertEqual(payload["final_installer_dir"], r"smoke_test_assets\packaging\installer-whisper-final")
        self.assertEqual(payload["failures"], [])
        self.assertGreaterEqual(len(payload["commands"]), 6)
        self.assertTrue(any("Do not run the final build" in warning for warning in payload["warnings"]))

    def test_final_release_is_not_an_open_external_gate_after_artifact_pass(self):
        gate_commands = "\n".join(command for gate in open_gate_summary.OPEN_GATES for command in gate.next_command)
        preflight_commands = "\n".join(final_release_preflight._final_commands())

        self.assertNotIn("final_public_release_gate.py", gate_commands)
        self.assertNotIn("final-public-release-gate-report.json", gate_commands)
        self.assertIn("OmniDictate_Setup_v3.0.0.exe", preflight_commands)
        self.assertNotIn("dist-whisper\\OmniDictate", gate_commands)


if __name__ == "__main__":
    unittest.main(verbosity=2)
