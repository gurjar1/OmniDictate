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

from tools import final_public_release_gate, open_gate_summary


class FinalPublicReleaseGateTest(unittest.TestCase):
    def test_build_commands_include_final_release_chain(self):
        args = final_public_release_gate.parse_args([])

        commands, paths = final_public_release_gate.build_commands(args)
        joined = "\n".join(subprocess.list2cmdline(item["command"]) for item in commands)

        self.assertEqual(len(commands), 8)
        self.assertIn("final_release_preflight.py", joined)
        self.assertIn("pyinstaller.exe", joined)
        self.assertEqual(commands[1]["env"], {"OMNIDICTATE_PACKAGE_PROFILE": "whisper-only"})
        self.assertIn("ISCC.exe", joined)
        self.assertIn("packaged_app_smoke.py", joined)
        self.assertNotIn("--package-profile", joined)
        self.assertIn("--package-smoke-load-whisper", joined)
        self.assertIn("large-v3-turbo", joined)
        self.assertIn("installer_smoke.ps1", joined)
        self.assertIn(str(final_public_release_gate.FINAL_INSTALL_DIR), joined)
        self.assertNotIn("$env:LOCALAPPDATA", joined)
        self.assertIn("-AllowRemoveExisting", joined)
        self.assertIn("package_size_audit.py", joined)
        self.assertIn("file_sha256.py", joined)
        self.assertNotIn("Get-FileHash", joined)
        self.assertIn("final_release_gate_audit.py", joined)
        self.assertEqual(paths["installer"], r"smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe")
        self.assertEqual(paths["bundle"], r"smoke_test_assets\packaging\dist-whisper-final\OmniDictate")

    def test_dry_run_writes_summary_without_building(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "final-public-release-dry-run.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "final_public_release_gate.py"),
                    "--report-json",
                    str(report),
                    "--dry-run",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["status"], "dry-run")
        self.assertEqual(len(payload["commands"]), 8)
        self.assertEqual(payload["results"], [])
        self.assertTrue(any(command["env"] == {"OMNIDICTATE_PACKAGE_PROFILE": "whisper-only"} for command in payload["commands"]))
        self.assertFalse(any("--package-profile" in command["command"] for command in payload["commands"]))

    def test_final_gate_is_no_longer_an_open_external_blocker(self):
        self.assertNotIn("final-public-release", {gate.key for gate in open_gate_summary.OPEN_GATES})


if __name__ == "__main__":
    unittest.main(verbosity=2)
