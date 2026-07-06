from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSettings

from app_settings import AppSettings, RELEASE_DEFAULTS_VERSION, migrate_release_defaults, sanitize_app_settings_for_runtime


class RuntimeProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_profile = os.environ.get("OMNIDICTATE_PACKAGE_PROFILE")

    def tearDown(self) -> None:
        if self.original_profile is None:
            os.environ.pop("OMNIDICTATE_PACKAGE_PROFILE", None)
        else:
            os.environ["OMNIDICTATE_PACKAGE_PROFILE"] = self.original_profile

    def test_whisper_only_runtime_sanitizes_experimental_settings(self):
        os.environ["OMNIDICTATE_PACKAGE_PROFILE"] = "whisper-only"
        settings = AppSettings(
            backend="gemma-gguf-server",
            prompt_mode="reasoning",
            screen_context_enabled=True,
            webcam_enabled=True,
            preload_model_on_launch=True,
        )

        notices = sanitize_app_settings_for_runtime(settings)

        self.assertGreaterEqual(len(notices), 2)
        self.assertEqual(settings.backend, "faster-whisper")
        self.assertEqual(settings.prompt_mode, "pure")
        self.assertFalse(settings.screen_context_enabled)
        self.assertFalse(settings.webcam_enabled)
        self.assertFalse(settings.preload_model_on_launch)

    def test_full_runtime_leaves_experimental_settings_available(self):
        os.environ.pop("OMNIDICTATE_PACKAGE_PROFILE", None)
        settings = AppSettings(
            backend="gemma-4",
            prompt_mode="context",
            screen_context_enabled=True,
            preload_model_on_launch=True,
        )

        notices = sanitize_app_settings_for_runtime(settings)

        self.assertEqual(notices, [])
        self.assertEqual(settings.backend, "gemma-4")
        self.assertEqual(settings.prompt_mode, "context")
        self.assertTrue(settings.screen_context_enabled)
        self.assertTrue(settings.preload_model_on_launch)

    def test_whisper_only_ui_hides_experimental_surface_and_repairs_stale_settings(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "ui_smoke_test.py"),
                "--package-profile",
                "whisper-only",
                "--seed-stale-gemma-settings",
                "--assert-whisper-only-ui",
                "--page",
                "settings",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_release_default_migration_repairs_pre_release_saved_values(self):
        with TemporaryDirectory() as temp_dir:
            settings = QSettings(str(Path(temp_dir) / "settings.ini"), QSettings.IniFormat)
            settings.setValue("whisper_model", "base")
            settings.setValue("language", "es")
            settings.setValue("type_into_active_app", False)
            settings.sync()

            self.assertTrue(migrate_release_defaults(settings))
            migrated = AppSettings.from_qsettings(settings)

            self.assertEqual(migrated.whisper_model, "large-v3-turbo")
            self.assertEqual(migrated.language, "en")
            self.assertTrue(migrated.type_into_active_app)
            self.assertEqual(settings.value("release_defaults_version"), RELEASE_DEFAULTS_VERSION)

    def test_release_default_migration_does_not_overwrite_current_user_choices(self):
        with TemporaryDirectory() as temp_dir:
            settings = QSettings(str(Path(temp_dir) / "settings.ini"), QSettings.IniFormat)
            settings.setValue("release_defaults_version", RELEASE_DEFAULTS_VERSION)
            settings.setValue("whisper_model", "tiny")
            settings.setValue("language", "cs")
            settings.setValue("type_into_active_app", False)
            settings.sync()

            self.assertFalse(migrate_release_defaults(settings))
            current = AppSettings.from_qsettings(settings)

            self.assertEqual(current.whisper_model, "tiny")
            self.assertEqual(current.language, "cs")
            self.assertFalse(current.type_into_active_app)


if __name__ == "__main__":
    unittest.main(verbosity=2)
