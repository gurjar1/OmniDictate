from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import github_release_preflight
from app_updates import APP_VERSION


CURRENT_TAG = f"v{APP_VERSION}"
LAST_TAG = "v3.0.1"


def _git_result(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["git"], returncode=returncode, stdout=stdout, stderr=stderr)


class GitHubReleasePreflightTest(unittest.TestCase):
    def test_current_blocked_state_is_not_publish_ready(self):
        def fake_git(args: list[str]) -> subprocess.CompletedProcess[str]:
            if args == ["remote", "get-url", "origin"]:
                return _git_result("https://github.com/gurjar1/OmniDictate.git\n")
            if args == ["ls-remote", "--tags", "origin", f"refs/tags/{CURRENT_TAG}"]:
                return _git_result("")
            if args == ["ls-remote", "--tags", "origin", f"refs/tags/{LAST_TAG}"]:
                return _git_result(f"abc123\trefs/tags/{LAST_TAG}\n")
            raise AssertionError(f"unexpected git args: {args}")

        release_payload = {
            "status": "blocked",
            "publication": {
                "status": "blocked",
                "final_artifact_status": "ready",
                "final_public_status": "passed",
                "scope_decisions_doc": "docs\\release\\RELEASE_SCOPE_DECISIONS_3.0.0.md",
                "scope_gate_statuses": {
                    "physical-microphone": "pending",
                    "gemma-e4b-live": "pending",
                    "gguf-real-server": "pending",
                },
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            installer = Path(temp_dir) / f"OmniDictate_Setup_v{APP_VERSION}.exe"
            installer.write_bytes(b"installer")
            with mock.patch.object(github_release_preflight, "INSTALLER", installer), mock.patch.object(
                github_release_preflight, "_git", side_effect=fake_git
            ), mock.patch.object(
                github_release_preflight.release_status_report,
                "build_release_status",
                return_value=("blocked", [], release_payload),
            ):
                status, failures, payload = github_release_preflight.build_github_release_preflight()

        self.assertEqual(status, "blocked")
        self.assertEqual(failures, [])
        self.assertEqual(payload["schema_version"], 1)
        self.assertRegex(payload["generated_at_utc"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertFalse(payload["publish_ready"])
        self.assertFalse(payload["tag_exists"])
        self.assertTrue(payload["last_public_tag_exists"])
        self.assertTrue(payload["installer_exists"])
        self.assertEqual(payload["publication_status"], "blocked")
        self.assertEqual(
            payload["pending_release_scope_gates"],
            ["gemma-e4b-live", "gguf-real-server", "physical-microphone"],
        )
        self.assertEqual(payload["scope_gate_statuses"]["physical-microphone"], "pending")
        self.assertIn("publication is blocked", " ".join(payload["warnings"]))

    def test_existing_remote_release_tag_is_invalid(self):
        def fake_git(args: list[str]) -> subprocess.CompletedProcess[str]:
            if args == ["remote", "get-url", "origin"]:
                return _git_result("https://github.com/gurjar1/OmniDictate.git\n")
            if args == ["ls-remote", "--tags", "origin", f"refs/tags/{CURRENT_TAG}"]:
                return _git_result(f"def456\trefs/tags/{CURRENT_TAG}\n")
            if args == ["ls-remote", "--tags", "origin", f"refs/tags/{LAST_TAG}"]:
                return _git_result(f"abc123\trefs/tags/{LAST_TAG}\n")
            raise AssertionError(f"unexpected git args: {args}")

        with mock.patch.object(github_release_preflight, "_git", side_effect=fake_git), mock.patch.object(
            github_release_preflight.release_status_report,
            "build_release_status",
            return_value=("ready", [], {"status": "ready"}),
        ):
            status, failures, payload = github_release_preflight.build_github_release_preflight()

        self.assertEqual(status, "invalid")
        self.assertTrue(payload["tag_exists"])
        self.assertTrue(any("release tag already exists" in failure for failure in failures))

    def test_remote_query_failure_is_invalid(self):
        def fake_git(args: list[str]) -> subprocess.CompletedProcess[str]:
            if args == ["remote", "get-url", "origin"]:
                return _git_result("https://github.com/gurjar1/OmniDictate.git\n")
            if args == ["ls-remote", "--tags", "origin", f"refs/tags/{CURRENT_TAG}"]:
                return _git_result(stderr="network unavailable", returncode=128)
            if args == ["ls-remote", "--tags", "origin", f"refs/tags/{LAST_TAG}"]:
                return _git_result(f"abc123\trefs/tags/{LAST_TAG}\n")
            raise AssertionError(f"unexpected git args: {args}")

        with mock.patch.object(github_release_preflight, "_git", side_effect=fake_git), mock.patch.object(
            github_release_preflight.release_status_report,
            "build_release_status",
            return_value=("ready", [], {"status": "ready"}),
        ):
            status, failures, _payload = github_release_preflight.build_github_release_preflight()

        self.assertEqual(status, "invalid")
        self.assertTrue(any(f"could not query remote tag {CURRENT_TAG}" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main(verbosity=2)
