from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from app_settings import AppSettings
from engines.base import RuntimeDiagnostics
from main_gui import OmniDictateApp


class UiTransportStateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = OmniDictateApp(
            start_hotkeys=False,
            enable_preload=False,
            enable_auto_update_check=False,
        )

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_idle_state_makes_start_primary_and_stop_inactive(self):
        self.window.is_dictation_running = False
        self.window._is_stopping = False
        self.window.update_transport_button_state()

        self.assertEqual(self.window.start_button.property("state"), "primary")
        self.assertEqual(self.window.stop_button.property("state"), "inactive")

    def test_running_state_makes_stop_active(self):
        self.window.is_dictation_running = True
        self.window._is_stopping = False
        self.window.update_transport_button_state()

        self.assertEqual(self.window.start_button.property("state"), "inactive")
        self.assertEqual(self.window.stop_button.property("state"), "active")

    def test_stopping_state_makes_stop_busy(self):
        self.window.is_dictation_running = True
        self.window._is_stopping = True
        self.window.update_transport_button_state()

        self.assertEqual(self.window.start_button.property("state"), "inactive")
        self.assertEqual(self.window.stop_button.property("state"), "busy")

    def test_release_polish_controls_are_present(self):
        self.assertNotEqual(self.window.language_combo.findData("cs"), -1)
        self.assertEqual(self.window.model_combo.itemText(0), "large-v3-turbo")
        self.assertEqual(AppSettings().whisper_model, "large-v3-turbo")
        self.assertEqual(AppSettings().language, "en")
        self.assertTrue(AppSettings().type_into_active_app)
        self.assertTrue(hasattr(self.window, "type_into_active_app_checkbox"))
        self.assertTrue(hasattr(self.window, "min_ptt_duration_spinbox"))
        self.assertEqual(AppSettings().min_ptt_duration_ms, 250)
        self.assertEqual(self.window.check_updates_button.text(), "Check for Updates")
        self.assertTrue(hasattr(self.window, "auto_update_checkbox"))
        self.assertTrue(AppSettings().auto_check_updates)
        self.assertTrue(hasattr(self.window, "runtime_status_button"))

    def test_runtime_badge_uses_plain_language_states(self):
        self.window.handle_runtime_update(RuntimeDiagnostics(
            status="gpu-ready",
            headline="GPU acceleration is working",
            summary="OmniDictate is using your NVIDIA GPU.",
        ))
        self.assertEqual(self.window.runtime_status_button.text(), "Runtime: GPU ready")
        self.assertEqual(self.window.runtime_status_button.property("runtimeState"), "gpu")

        self.window.handle_runtime_update(RuntimeDiagnostics(
            status="cpu-mode",
            headline="CPU mode",
            summary="OmniDictate is working, but transcription can be slower.",
        ))
        self.assertEqual(self.window.runtime_status_button.text(), "Runtime: CPU mode")
        self.assertEqual(self.window.runtime_status_button.property("runtimeState"), "cpu")

        self.window.handle_runtime_update(RuntimeDiagnostics(
            status="checked",
            headline="Runtime loaded",
            summary="The selected runtime loaded.",
        ))
        self.assertEqual(self.window.runtime_status_button.text(), "Runtime: Checked")
        self.assertEqual(self.window.runtime_status_button.property("runtimeState"), "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
