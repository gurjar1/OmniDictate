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

from tools.final_release_gate_audit import audit_final_release


def _preflight(bundle: Path, installer: Path, status: str = "ready-to-run") -> dict:
    return {
        "status": status,
        "final_installer": str(installer),
        "final_bundle": str(bundle),
        "final_dist": str(bundle.parent),
        "final_installer_dir": str(installer.parent),
        "commands": [],
        "warnings": [],
        "failures": [],
    }


class FinalReleaseGateAuditTest(unittest.TestCase):
    def test_valid_final_artifacts_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "dist-whisper-final" / "OmniDictate"
            installer = root / "installer-whisper-final" / "OmniDictate_Setup_v3.0.0.exe"
            bundle.mkdir(parents=True)
            installer.parent.mkdir(parents=True)
            (bundle / "OmniDictate.exe").write_bytes(b"bundle")
            (bundle / "_internal").mkdir()
            (bundle / "_internal" / "python311.dll").write_bytes(b"dll")
            (bundle / "_internal" / "av").mkdir()
            installer.write_bytes(b"installer")

            failures, payload = audit_final_release(_preflight(bundle, installer), bundle, installer)

        self.assertEqual(failures, [])
        self.assertEqual(payload["status"], "ready")
        self.assertGreater(payload["bundle_bytes"], 0)
        self.assertGreater(payload["installer_bytes"], 0)
        self.assertEqual(len(payload["installer_sha256"]), 64)

    def test_smoke_named_installer_does_not_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "dist-whisper-final" / "OmniDictate"
            installer = root / "installer-whisper-final" / "OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe"
            bundle.mkdir(parents=True)
            installer.parent.mkdir(parents=True)
            (bundle / "OmniDictate.exe").write_bytes(b"bundle")
            (bundle / "_internal").mkdir()
            (bundle / "_internal" / "python311.dll").write_bytes(b"dll")
            (bundle / "_internal" / "av").mkdir()
            installer.write_bytes(b"installer")

            failures, _payload = audit_final_release(_preflight(bundle, installer), bundle, installer)

        self.assertIn("final installer must be named OmniDictate_Setup_v3.0.0.exe", failures)
        self.assertIn("final installer path must not use smoke artifact naming", failures)

    def test_missing_artifacts_and_failed_preflight_do_not_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "dist-whisper-final" / "OmniDictate"
            installer = root / "installer-whisper-final" / "OmniDictate_Setup_v3.0.0.exe"

            failures, _payload = audit_final_release(_preflight(bundle, installer, status="preflight-failed"), bundle, installer)

        self.assertIn("final release preflight report is not ready-to-run", failures)
        self.assertTrue(any("final bundle directory is missing" in failure for failure in failures))
        self.assertTrue(any("final installer is missing" in failure for failure in failures))

    def test_cli_writes_report_on_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = root / "dist-whisper-final" / "OmniDictate"
            installer = root / "installer-whisper-final" / "OmniDictate_Setup_v3.0.0.exe"
            preflight = root / "preflight.json"
            report = root / "final-report.json"
            bundle.mkdir(parents=True)
            installer.parent.mkdir(parents=True)
            (bundle / "OmniDictate.exe").write_bytes(b"bundle")
            (bundle / "_internal").mkdir()
            (bundle / "_internal" / "python311.dll").write_bytes(b"dll")
            (bundle / "_internal" / "av").mkdir()
            installer.write_bytes(b"installer")
            preflight.write_text(json.dumps(_preflight(bundle, installer)), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "final_release_gate_audit.py"),
                    "--preflight-report",
                    str(preflight),
                    "--bundle",
                    str(bundle),
                    "--installer",
                    str(installer),
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
        self.assertEqual(payload["failures"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
