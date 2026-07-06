from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255.0 for index in (0, 2, 4))


def _linear(channel: float) -> float:
    if channel <= 0.03928:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def contrast_ratio(foreground: str, background: str) -> float:
    fg = _hex_to_rgb(foreground)
    bg = _hex_to_rgb(background)
    fg_luminance = 0.2126 * _linear(fg[0]) + 0.7152 * _linear(fg[1]) + 0.0722 * _linear(fg[2])
    bg_luminance = 0.2126 * _linear(bg[0]) + 0.7152 * _linear(bg[1]) + 0.0722 * _linear(bg[2])
    lighter = max(fg_luminance, bg_luminance)
    darker = min(fg_luminance, bg_luminance)
    return (lighter + 0.05) / (darker + 0.05)


class UiContrastStaticTest(unittest.TestCase):
    def test_windows_popups_and_error_dialogs_have_explicit_light_palette(self):
        qss = (ROOT / "style.qss").read_text(encoding="utf-8")
        required_selectors = [
            "QMessageBox",
            "QMessageBox QLabel",
            "QMenu::item:selected",
            "QComboBox QAbstractItemView",
            "QComboBox QAbstractItemView::item:selected",
            "QPushButton#iconButton",
            "QWidget:disabled",
        ]

        for selector in required_selectors:
            self.assertIn(selector, qss)

    def test_key_palette_pairs_clear_accessible_contrast_floor(self):
        pairs = [
            ("#102f45", "#ffffff"),
            ("#ffffff", "#0f6f96"),
            ("#12344c", "#ffffff"),
            ("#63798a", "#eef3f6"),
        ]

        for foreground, background in pairs:
            with self.subTest(foreground=foreground, background=background):
                self.assertGreaterEqual(contrast_ratio(foreground, background), 3.0)

    def test_combobox_popup_does_not_depend_on_translucent_or_native_dark_palette(self):
        qss = (ROOT / "style.qss").read_text(encoding="utf-8")
        popup_block_match = re.search(r"QComboBox QAbstractItemView,\s*QComboBox QAbstractItemView QWidget\s*\{(?P<body>.*?)\}", qss, re.S)

        self.assertIsNotNone(popup_block_match)
        body = popup_block_match.group("body")
        self.assertIn("background-color: #ffffff", body)
        self.assertIn("color: #102f45", body)
        self.assertNotIn("rgba", body)

    def test_settings_rows_have_text_padding_and_readable_weight(self):
        qss = (ROOT / "style.qss").read_text(encoding="utf-8")
        gui_source = (ROOT / "main_gui.py").read_text(encoding="utf-8")

        self.assertIn('font-family: "Segoe UI Variable Text", "Segoe UI"', qss)
        self.assertIn("font-weight: 500", qss)
        self.assertIn("row.setMinimumHeight(76)", gui_source)
        self.assertIn("layout.setContentsMargins(16, 10, 16, 10)", gui_source)

    def test_settings_wheel_events_scroll_page_not_hovered_values(self):
        gui_source = (ROOT / "main_gui.py").read_text(encoding="utf-8")

        self.assertIn("class SettingsWheelGuard", gui_source)
        self.assertIn("event.type() != QEvent.Type.Wheel", gui_source)
        self.assertIn("scrollbar.setValue(scrollbar.value() - delta)", gui_source)
        self.assertIn("wheel_control.installEventFilter(self.settings_wheel_guard)", gui_source)

    def test_transport_buttons_use_stateful_single_accent_styling(self):
        qss = (ROOT / "style.qss").read_text(encoding="utf-8")
        gui_source = (ROOT / "main_gui.py").read_text(encoding="utf-8")

        self.assertIn('QPushButton#startButton[state="primary"]', qss)
        self.assertIn('QPushButton#stopButton[state="active"]', qss)
        self.assertIn('QPushButton#stopButton[state="busy"]', qss)
        self.assertIn('QPushButton#stopButton[state="inactive"]', qss)
        self.assertIn('setProperty("state", "primary")', gui_source)
        self.assertIn('setProperty("state", "inactive")', gui_source)
        self.assertIn("def update_transport_button_state", gui_source)
        self.assertNotIn("#d45258", qss)
        self.assertNotIn("#f0725f", qss)


if __name__ == "__main__":
    unittest.main(verbosity=2)
