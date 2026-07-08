from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construct the OmniDictate UI without global hotkeys.")
    parser.add_argument("--screenshot", default="", help="Optional path to save a window grab.")
    parser.add_argument(
        "--platform",
        choices=["offscreen", "native"],
        default="offscreen",
        help="Qt platform mode. Use native for real Windows visual QA screenshots.",
    )
    parser.add_argument("--page", choices=["dictation", "settings"], default="dictation")
    parser.add_argument(
        "--backend",
        choices=["current", "faster-whisper", "gemma-4", "gemma-gguf-server"],
        default="current",
        help="Temporarily select a backend for screenshot QA without saving it.",
    )
    parser.add_argument(
        "--prompt-mode",
        choices=["current", "pure", "context", "reasoning"],
        default="current",
        help="Temporarily select an output style for screenshot QA without saving it.",
    )
    parser.add_argument(
        "--gemma-audio-mode",
        choices=["current", "hybrid-whisper", "native-audio"],
        default="current",
        help="Temporarily select a Gemma audio mode for screenshot QA without saving it.",
    )
    parser.add_argument("--package-profile", default="", help="Set OMNIDICTATE_PACKAGE_PROFILE before importing the app.")
    parser.add_argument(
        "--assert-whisper-only-ui",
        action="store_true",
        help="Assert that the public Whisper-only profile hides experimental UI and sanitizes settings.",
    )
    parser.add_argument(
        "--seed-stale-gemma-settings",
        action="store_true",
        help="Seed isolated QSettings with stale Gemma selections before constructing the window.",
    )
    return parser.parse_args()


def _set_combo_by_data(combo, value: str) -> None:
    index = combo.findData(value)
    if index == -1:
        raise AssertionError(f"Could not find combo data {value!r}.")
    combo.setCurrentIndex(index)


def main() -> int:
    args = parse_args()
    if args.platform == "offscreen":
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if args.package_profile:
        os.environ["OMNIDICTATE_PACKAGE_PROFILE"] = args.package_profile
    if args.seed_stale_gemma_settings:
        os.environ.setdefault("OMNIDICTATE_SETTINGS_ORG", "OmniCorp")
        os.environ["OMNIDICTATE_SETTINGS_APP"] = f"OmniDictateUiSmoke{uuid.uuid4().hex}"

    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication, QLabel
    from app_settings import CONFIG_APP, CONFIG_ORG
    from main_gui import OmniDictateApp

    if args.seed_stale_gemma_settings:
        stale_settings = QSettings(CONFIG_ORG, CONFIG_APP)
        stale_settings.setValue("backend", "gemma-gguf-server")
        stale_settings.setValue("prompt_mode", "reasoning")
        stale_settings.setValue("screen_context_enabled", True)
        stale_settings.setValue("webcam_enabled", True)
        stale_settings.sync()

    app = QApplication.instance() or QApplication([])
    style_path = ROOT / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))

    window = OmniDictateApp(start_hotkeys=False, enable_preload=False, enable_auto_update_check=False)
    window.resize(1180, 780)
    window._suspend_settings_events = True
    if args.backend != "current":
        _set_combo_by_data(window.backend_combo, args.backend)
    if args.prompt_mode != "current":
        _set_combo_by_data(window.prompt_mode_combo, args.prompt_mode)
    if args.gemma_audio_mode != "current":
        _set_combo_by_data(window.gemma_audio_mode_combo, args.gemma_audio_mode)
    window.on_backend_changed()
    if args.page == "settings":
        window.stack.setCurrentWidget(window.page_settings)
    else:
        window.stack.setCurrentWidget(window.page_dictation)
    window.show()
    app.processEvents()

    if window.stack.count() != 2:
        raise AssertionError(f"Expected 2 app pages, got {window.stack.count()}.")

    if args.assert_whisper_only_ui:
        backend_values = [window.backend_combo.itemData(index) for index in range(window.backend_combo.count())]
        prompt_values = [window.prompt_mode_combo.itemData(index) for index in range(window.prompt_mode_combo.count())]
        if backend_values != ["faster-whisper"]:
            raise AssertionError(f"Whisper-only backend choices leaked unsupported values: {backend_values!r}")
        if prompt_values != ["pure"]:
            raise AssertionError(f"Whisper-only output choices leaked unsupported values: {prompt_values!r}")
        if window.app_settings.backend != "faster-whisper":
            raise AssertionError(f"Stale backend was not sanitized: {window.app_settings.backend!r}")
        if window.app_settings.prompt_mode != "pure":
            raise AssertionError(f"Stale prompt mode was not sanitized: {window.app_settings.prompt_mode!r}")
        hidden_widgets = [
            window.context_drop_area,
            window.attach_context_button,
            window.clear_context_button,
            window.backend_row,
            window.prompt_mode_row,
            window.context_settings_card,
            window.model_settings_card,
            window.gemma_model_row,
            window.gemma_audio_row,
            window.gemma_quantization_row,
            window.gguf_server_row,
            window.gguf_model_row,
            window.reasoning_preview_row,
        ]
        leaked = [type(widget).__name__ for widget in hidden_widgets if widget.isVisible()]
        if leaked:
            raise AssertionError(f"Whisper-only UI left experimental widgets visible: {leaked!r}")
        visible_label_text = [
            label.text()
            for label in window.findChildren(QLabel)
            if label.isVisible() and not label.objectName().startswith("qt_")
        ]
        visible_text = " ".join(
            [
                window.backend_combo.currentText(),
                window.prompt_mode_combo.currentText(),
                window.settings_summary_label.text(),
                window.engine_info_label.text(),
                *visible_label_text,
            ]
        )
        forbidden_visible = ["Gemma", "GGUF", "Review before typing", "Full reasoning", "Context-enhanced"]
        leaked_terms = [term for term in forbidden_visible if term in visible_text]
        if leaked_terms:
            raise AssertionError(f"Whisper-only visible copy leaked hidden labels {leaked_terms!r}: {visible_text!r}")

    if args.screenshot:
        output_path = Path(args.screenshot)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(output_path))
        print(f"Saved screenshot: {output_path.resolve()}")

    print(f"UI smoke passed: {window.windowTitle()} pages={window.stack.count()}")
    window._suspend_settings_events = True
    window.close()
    if args.seed_stale_gemma_settings:
        QSettings(CONFIG_ORG, CONFIG_APP).clear()
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
