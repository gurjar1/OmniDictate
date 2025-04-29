# main_gui.py

import sys
import time
import os

# PySide6 imports
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                               QWidget, QLabel, QComboBox, QStatusBar, QMessageBox,
                               QSpinBox, QDoubleSpinBox, QHBoxLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QGroupBox, QGridLayout,
                               QCheckBox, QTextEdit, QApplication)
from PySide6.QtCore import Qt, QThread, Slot, Signal, QSettings, QTimer
from PySide6.QtGui import QIcon, QFont, QClipboard, QTextCursor


# Import workers
try:
    from core_logic import DictationWorker
except ImportError as e:
    print(f"Error: Could not import from core_logic.py: {e}")
    sys.exit(1)

try:
    from hotkey_listener import HotkeyWorker
except ImportError as e:
    print(f"Error: Could not import from hotkey_listener.py: {e}")
    sys.exit(1)

# --- Configuration for Settings ---
CONFIG_ORG = "OmniCorp"
CONFIG_APP = "OmniDictate"

# --- Default Settings Constants ---
DEFAULT_MODEL_SIZE = "large-v3"
DEFAULT_LANGUAGE = "en"
DEFAULT_VAD_ENABLED = True
DEFAULT_SILENCE_THRESHOLD = 500
DEFAULT_CHAR_DELAY = 0.02
DEFAULT_PTT_KEY_STR = "keyboard.Key.shift_r"
DEFAULT_STOP_KEY_STR = "keyboard.Key.esc"
DEFAULT_NEW_LINE_COMMANDS = ["new line", "next line"]
DEFAULT_FILTER_WORDS = ["thanks for watching!", "thank you.", "thanks for watching", "Thanks for watching.", "thank you", "I'm sorry"," I'm sorry,", "I'm sorry, ", "I'm sorry,"]


# --- Main Application Window ---
class OmniDictateApp(QMainWindow):
    ptt_signal = Signal(bool)
    stop_signal_from_hotkey = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("OmniDictate")
        self.setGeometry(100, 100, 700, 750)

        self.settings = QSettings(CONFIG_ORG, CONFIG_APP)
        self.dictation_thread = None
        self.dictation_worker = None
        self.hotkey_thread = None
        self.hotkey_worker = None
        self.capture_hotkey_thread = None
        self.capture_hotkey_worker = None
        self.is_dictation_running = False
        self.setting_key_for = None
        self.original_button_text = ""
        self._is_stopping = False

        self.load_settings()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.create_control_section()
        self.create_status_section()
        self.create_transcription_display_section()
        self.create_config_section()
        self.main_layout.addStretch(0)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        self.start_button.clicked.connect(self.start_dictation)
        self.stop_button.clicked.connect(self.stop_dictation)
        self.vad_toggle_button.clicked.connect(self.toggle_vad)
        self.copy_button.clicked.connect(self.copy_transcription)
        self.filter_add_button.clicked.connect(self.add_filter_word)
        self.filter_remove_button.clicked.connect(self.remove_filter_word)
        self.set_ptt_key_button.clicked.connect(lambda: self.prepare_to_set_key('ptt'))
        self.set_stop_key_button.clicked.connect(lambda: self.prepare_to_set_key('stop'))
        self.restore_defaults_button.clicked.connect(self.restore_default_settings)
        self.stop_signal_from_hotkey.connect(self.stop_dictation)

        self.model_combo.currentTextChanged.connect(self.save_settings)
        self.language_combo.currentTextChanged.connect(self.save_settings)
        self.silence_spinbox.valueChanged.connect(self.save_settings)
        self.delay_spinbox.valueChanged.connect(self.save_settings)
        self.newline_edit.editingFinished.connect(self.save_settings)

        self.start_hotkey_listener()
        print("GUI Initialized.")

    # --- UI Creation Methods ---
    def create_control_section(self):
        control_group = QGroupBox("Controls")
        control_layout = QHBoxLayout(control_group)
        self.start_button = QPushButton(" Start Dictation ")
        self.stop_button = QPushButton(" Stop Dictation ")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        self.vad_toggle_button = QPushButton("VAD: ON")
        self.vad_toggle_button.setCheckable(True)
        self.vad_toggle_button.setChecked(self.loaded_settings.get("vad_enabled", DEFAULT_VAD_ENABLED))
        self.update_vad_button_style()
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addStretch()
        control_layout.addWidget(self.vad_toggle_button)
        self.main_layout.addWidget(control_group)

    def create_status_section(self):
        self.status_label = QLabel("Status: Idle")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)

    def create_transcription_display_section(self):
        display_group = QGroupBox("Transcription Output")
        display_layout = QVBoxLayout(display_group)
        self.transcription_display = QTextEdit()
        self.transcription_display.setReadOnly(True)
        self.transcription_display.setPlaceholderText("Transcribed text will appear here...")
        self.transcription_display.setFixedHeight(100)

        # --- Button Creation ---
        self.clear_button = QPushButton("Clear Text")
        self.clear_button.setFixedWidth(100)
        self.copy_button = QPushButton("Copy Text")
        self.copy_button.setFixedWidth(100)

        # --- Layout for Buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.copy_button)

        # --- Connect Clear Button Signal ---
        self.clear_button.clicked.connect(self.transcription_display.clear)
        display_layout.addWidget(self.transcription_display)
        display_layout.addLayout(button_layout)
        self.main_layout.addWidget(display_group)

    def create_config_section(self):
        config_group = QGroupBox("Configuration")
        config_layout = QGridLayout(config_group); config_layout.setSpacing(10)
        row = 0
        config_layout.addWidget(QLabel("Whisper Model:"), row, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["medium.en", "distil-large-v2", "distil-large-v3", "distil-small.en", "distil-medium.en", "large-v2", "large-v1", "medium", "base.en", "base", "small.en", "small", "tiny.en", "tiny", "large-v3"])
        self.model_combo.setCurrentText(self.loaded_settings.get("model_size", DEFAULT_MODEL_SIZE))
        config_layout.addWidget(self.model_combo, row, 1)
        config_layout.addWidget(QLabel("Language:"), row, 2)
        self.language_combo = QComboBox()
        self.language_combo.addItem("English (en)", "en")
        current_lang_code = self.loaded_settings.get("language", DEFAULT_LANGUAGE)
        index = self.language_combo.findData(current_lang_code); self.language_combo.setCurrentIndex(index if index != -1 else 0)
        config_layout.addWidget(self.language_combo, row, 3); row += 1
        config_layout.addWidget(QLabel("Silence Threshold (VAD):"), row, 0)
        self.silence_spinbox = QSpinBox()
        self.silence_spinbox.setRange(50, 2000); self.silence_spinbox.setSingleStep(50)
        self.silence_spinbox.setValue(self.loaded_settings.get("silence_threshold", DEFAULT_SILENCE_THRESHOLD))
        config_layout.addWidget(self.silence_spinbox, row, 1)
        config_layout.addWidget(QLabel("Typing Delay (sec):"), row, 2)
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setRange(0.0, 0.1); self.delay_spinbox.setSingleStep(0.005); self.delay_spinbox.setDecimals(3)
        self.delay_spinbox.setValue(self.loaded_settings.get("char_delay", DEFAULT_CHAR_DELAY))
        config_layout.addWidget(self.delay_spinbox, row, 3); row += 1
        config_layout.addWidget(QLabel("PTT Hotkey:"), row, 0)
        self.ptt_key_display_label = QLabel(self.loaded_settings.get('ptt_key_str', DEFAULT_PTT_KEY_STR))
        self.ptt_key_display_label.setObjectName("pttKeyDisplayLabel"); self.ptt_key_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_ptt_key_button = QPushButton("Set")
        config_layout.addWidget(self.ptt_key_display_label, row, 1); config_layout.addWidget(self.set_ptt_key_button, row, 2, 1, 2); row += 1
        config_layout.addWidget(QLabel("Stop Hotkey:"), row, 0)
        self.stop_key_display_label = QLabel(self.loaded_settings.get('stop_key_str', DEFAULT_STOP_KEY_STR))
        self.stop_key_display_label.setObjectName("stopKeyDisplayLabel"); self.stop_key_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_stop_key_button = QPushButton("Set")
        config_layout.addWidget(self.stop_key_display_label, row, 1); config_layout.addWidget(self.set_stop_key_button, row, 2, 1, 2); row += 1
        config_layout.addWidget(QLabel("New Line Commands (comma-separated):"), row, 0)
        self.newline_edit = QLineEdit(); self.newline_edit.setText(", ".join(self.loaded_settings.get("new_line_commands", DEFAULT_NEW_LINE_COMMANDS)))
        config_layout.addWidget(self.newline_edit, row, 1, 1, 3); row += 1
        config_layout.addWidget(QLabel("Filter Words (Remove exact matches):"), row, 0, 1, 4)
        self.filter_list = QListWidget(); self.filter_list.setAlternatingRowColors(True)
        self.filter_list.addItems(self.loaded_settings.get("filter_words", DEFAULT_FILTER_WORDS))
        config_layout.addWidget(self.filter_list, row + 1, 0, 1, 4)
        filter_controls_layout = QHBoxLayout()
        self.filter_add_edit = QLineEdit(); self.filter_add_button = QPushButton("Add"); self.filter_remove_button = QPushButton("Remove Selected")
        filter_controls_layout.addWidget(self.filter_add_edit); filter_controls_layout.addWidget(self.filter_add_button); filter_controls_layout.addWidget(self.filter_remove_button)
        config_layout.addLayout(filter_controls_layout, row + 2, 0, 1, 4); row += 3
        self.restore_defaults_button = QPushButton("Restore Default Settings"); self.restore_defaults_button.setObjectName("restoreDefaultsButton")
        config_layout.addWidget(self.restore_defaults_button, row, 0, 1, 4)
        config_layout.setColumnStretch(1, 1); config_layout.setColumnStretch(3, 1)
        self.main_layout.addWidget(config_group)

    # --- Settings Management ---
    def load_settings(self):
        self.loaded_settings = {
            "model_size": self.settings.value("model_size", DEFAULT_MODEL_SIZE),
            "language": self.settings.value("language", DEFAULT_LANGUAGE),
            "vad_enabled": self.settings.value("vad_enabled", DEFAULT_VAD_ENABLED, type=bool),
            "silence_threshold": self.settings.value("silence_threshold", DEFAULT_SILENCE_THRESHOLD, type=int),
            "char_delay": self.settings.value("char_delay", DEFAULT_CHAR_DELAY, type=float),
            "ptt_key_str": self.settings.value("ptt_key_str", DEFAULT_PTT_KEY_STR),
            "stop_key_str": self.settings.value("stop_key_str", DEFAULT_STOP_KEY_STR),
            "new_line_commands": self.settings.value("new_line_commands", DEFAULT_NEW_LINE_COMMANDS),
            "filter_words": self.settings.value("filter_words", DEFAULT_FILTER_WORDS)
        }
        if not isinstance(self.loaded_settings["new_line_commands"], list): self.loaded_settings["new_line_commands"] = DEFAULT_NEW_LINE_COMMANDS
        if not isinstance(self.loaded_settings["filter_words"], list): self.loaded_settings["filter_words"] = DEFAULT_FILTER_WORDS
        print("Settings loaded:", self.loaded_settings)

    def save_settings(self):
        if self.setting_key_for: return
        print("Saving settings...")
        self.settings.setValue("model_size", self.model_combo.currentText())
        idx = self.language_combo.currentIndex(); lang_code = self.language_combo.itemData(idx) if idx != -1 else DEFAULT_LANGUAGE
        self.settings.setValue("language", lang_code)
        self.settings.setValue("vad_enabled", self.vad_toggle_button.isChecked())
        self.settings.setValue("silence_threshold", self.silence_spinbox.value())
        self.settings.setValue("char_delay", self.delay_spinbox.value())
        self.settings.setValue("ptt_key_str", self.ptt_key_display_label.text())
        self.settings.setValue("stop_key_str", self.stop_key_display_label.text())
        newline_cmds = [cmd.strip() for cmd in self.newline_edit.text().split(',') if cmd.strip()]
        self.settings.setValue("new_line_commands", newline_cmds)
        filter_words = [self.filter_list.item(i).text() for i in range(self.filter_list.count())]
        self.settings.setValue("filter_words", filter_words)
        self.settings.sync(); print("Settings saved.")
        self.load_settings()
        if not self.is_dictation_running: self.restart_hotkey_listener()

    @Slot()
    def restore_default_settings(self):
        print("Restoring default settings...")
        self.model_combo.setCurrentText(DEFAULT_MODEL_SIZE)
        index = self.language_combo.findData(DEFAULT_LANGUAGE); self.language_combo.setCurrentIndex(index if index != -1 else 0)
        self.vad_toggle_button.setChecked(DEFAULT_VAD_ENABLED)
        self.silence_spinbox.setValue(DEFAULT_SILENCE_THRESHOLD)
        self.delay_spinbox.setValue(DEFAULT_CHAR_DELAY)
        self.ptt_key_display_label.setText(DEFAULT_PTT_KEY_STR)
        self.stop_key_display_label.setText(DEFAULT_STOP_KEY_STR)
        self.newline_edit.setText(", ".join(DEFAULT_NEW_LINE_COMMANDS))
        self.filter_list.clear(); self.filter_list.addItems(DEFAULT_FILTER_WORDS)
        self.update_vad_button_style()
        self.save_settings()
        QMessageBox.information(self, "Settings Restored", "Default settings restored and saved.")

    # --- Filter Word Management ---
    def add_filter_word(self):
        word = self.filter_add_edit.text().strip()
        if word and not self.filter_list.findItems(word, Qt.MatchFlag.MatchExactly):
            self.filter_list.addItem(QListWidgetItem(word)); self.filter_add_edit.clear(); self.save_settings()

    def remove_filter_word(self):
        items = self.filter_list.selectedItems()
        if not items: return
        for item in items: self.filter_list.takeItem(self.filter_list.row(item))
        self.save_settings()

    # --- Hotkey Setting Logic ---
    def prepare_to_set_key(self, key_type):
        if self.is_dictation_running: QMessageBox.warning(self, "Warning", "Stop dictation first."); return
        if self.setting_key_for: QMessageBox.warning(self, "Warning", f"Already waiting for {self.setting_key_for} key."); return
        self.setting_key_for = key_type
        button = self.set_ptt_key_button if key_type == 'ptt' else self.set_stop_key_button
        self.original_button_text = button.text()
        button.setText("Press New Key..."); button.setProperty("waitingInput", True); self.style().polish(button)
        self.set_other_controls_enabled(False); self.stop_hotkey_listener()
        self.capture_hotkey_thread = QThread(self)
        self.capture_hotkey_worker = HotkeyWorker(capture_mode=True)
        self.capture_hotkey_worker.moveToThread(self.capture_hotkey_thread)
        self.capture_hotkey_worker.key_captured_signal.connect(self.handle_key_capture)
        self.capture_hotkey_worker.error_signal.connect(self.handle_key_capture_error)
        self.capture_hotkey_thread.finished.connect(self.capture_hotkey_worker.deleteLater)
        self.capture_hotkey_thread.finished.connect(self.capture_hotkey_thread.deleteLater)
        self.capture_hotkey_thread.started.connect(self.capture_hotkey_worker.start_listening)
        self.capture_hotkey_thread.start()

    @Slot(object, str)
    def handle_key_capture(self, key_obj, key_str):
        print(f"Captured {self.setting_key_for} key: {key_str}")
        if self.setting_key_for == 'ptt': self.ptt_key_display_label.setText(key_str)
        elif self.setting_key_for == 'stop': self.stop_key_display_label.setText(key_str)
        self.finish_setting_key(); self.save_settings()

    @Slot(str)
    def handle_key_capture_error(self, error_msg):
        QMessageBox.warning(self, "Hotkey Error", f"Could not capture key: {error_msg}")
        self.finish_setting_key(); self.start_hotkey_listener()

    def finish_setting_key(self):
        if not self.setting_key_for: return
        button = self.set_ptt_key_button if self.setting_key_for == 'ptt' else self.set_stop_key_button
        button.setText(self.original_button_text if hasattr(self, 'original_button_text') and self.original_button_text else "Set")
        button.setProperty("waitingInput", False); self.style().polish(button)
        self.setting_key_for = None; self.set_other_controls_enabled(True)
        if self.capture_hotkey_worker: self.capture_hotkey_worker.stop_listening()
        if self.capture_hotkey_thread and self.capture_hotkey_thread.isRunning(): self.capture_hotkey_thread.quit(); self.capture_hotkey_thread.wait(500)
        self.capture_hotkey_worker = None; self.capture_hotkey_thread = None

    def set_other_controls_enabled(self, enabled):
        is_setting_ptt = self.setting_key_for == 'ptt'; is_setting_stop = self.setting_key_for == 'stop'
        self.start_button.setEnabled(enabled and not self.is_dictation_running)
        self.stop_button.setEnabled(enabled and self.is_dictation_running)
        self.set_config_enabled(enabled)
        self.set_ptt_key_button.setEnabled(enabled and not is_setting_stop)
        self.set_stop_key_button.setEnabled(enabled and not is_setting_ptt)

    # --- VAD Toggle Logic ---
    @Slot()
    def toggle_vad(self):
        is_checked = self.vad_toggle_button.isChecked()
        self.update_vad_button_style()
        self.save_settings()
        if self.dictation_worker and self.is_dictation_running:
             self.dictation_worker.set_vad_enabled(is_checked)

    def update_vad_button_style(self):
        is_checked = self.vad_toggle_button.isChecked()
        self.vad_toggle_button.setText("VAD: ON" if is_checked else "VAD: OFF")
        self.vad_toggle_button.setProperty("vad_on", is_checked); self.style().polish(self.vad_toggle_button)

    # --- Slots for Worker Signals ---
    @Slot(str)
    def update_status(self, status_text):
        self.status_label.setText(f"Status: {status_text}")
        self.statusBar.showMessage(status_text)

    @Slot(str)
    def handle_transcription(self, text):
        current_text = self.transcription_display.toPlainText()
        prefix = "\n" if current_text and not current_text.endswith(('\n', ' ')) else ""
        if prefix == "" and current_text and not current_text.endswith(' '): prefix = " "
        self.transcription_display.insertPlainText(prefix + text.strip())
        self.transcription_display.moveCursor(QTextCursor.End)

    @Slot(str)
    def show_error(self, error_text):
        print(f"GUI Error: {error_text}")
        self.update_status("Error")
        QMessageBox.critical(self, "OmniDictate Error", error_text)
        if self.is_dictation_running: self.stop_dictation()
        else: self.reset_ui_after_stop()

    # --- Copy Transcription ---
    @Slot()
    def copy_transcription(self):
        clipboard = QApplication.clipboard()
        text_to_copy = self.transcription_display.toPlainText()
        clipboard.setText(text_to_copy)
        self.statusBar.showMessage("Transcription copied to clipboard!", 2000)

    # --- GUI Control Methods ---
    def start_dictation(self):
        if self.is_dictation_running: print("Dictation is already running."); return
        if isinstance(self.dictation_thread, QThread) or isinstance(self.dictation_worker, DictationWorker):
            print("Warning: Remnants of previous thread/worker found.")
            if self.dictation_thread and self.dictation_thread.isRunning():
                 print("Error: Previous thread still running. Aborting start.")
                 QMessageBox.critical(self, "Error", "Previous dictation process still running. Please wait or restart.")
                 return
            else: self.dictation_worker = None; self.dictation_thread = None
        self.save_settings()
        print(f"Attempting to start dictation with model: {self.loaded_settings['model_size']}")
        self.dictation_thread = QThread(self)
        self.dictation_worker = DictationWorker(
            gui_wid=int(self.winId()), model_size=self.loaded_settings['model_size'],
            language=self.loaded_settings['language'], vad_enabled=self.loaded_settings['vad_enabled'],
            silence_threshold=self.loaded_settings['silence_threshold'], silence_duration=0.5,
            char_delay=self.loaded_settings['char_delay'], filter_words=self.loaded_settings['filter_words'],
            new_line_commands=self.loaded_settings['new_line_commands']
        )
        self.dictation_worker.moveToThread(self.dictation_thread)
        self.dictation_worker.status_updated.connect(self.update_status)
        self.dictation_worker.transcription_ready.connect(self.handle_transcription)
        self.dictation_worker.error_occurred.connect(self.show_error)
        self.dictation_thread.started.connect(self.dictation_worker.start_processing)
        self.dictation_thread.finished.connect(self.dictation_worker.deleteLater)
        self.dictation_thread.finished.connect(self.dictation_thread.deleteLater)
        self.dictation_thread.finished.connect(self.on_thread_finished)
        self.ptt_signal.connect(self.dictation_worker.set_ptt_state)
        self.update_status("Initializing..."); self.start_button.setEnabled(False); self.stop_button.setEnabled(True)
        self.set_config_enabled(False)
        self.dictation_thread.start(); self.is_dictation_running = True
        print("Dictation thread initiated.")

    def stop_dictation(self):
        if not self.is_dictation_running and self.start_button.isEnabled(): print("Stop called but already stopped."); return
        if self._is_stopping: return
        self._is_stopping = True
        print("GUI requesting stop..."); self.update_status("Stopping...")
        self.stop_button.setEnabled(False)
        if self.dictation_worker:
            try:
                self.ptt_signal.disconnect(self.dictation_worker.set_ptt_state)
            except RuntimeError:
                pass # Ignore if not connected or already disconnected
        if self.dictation_worker: self.dictation_worker.stop_processing()
        if self.dictation_thread and self.dictation_thread.isRunning():
            self.dictation_thread.quit()
            if not self.dictation_thread.wait(1500): print("Warning: Dictation thread didn't finish quitting."); self.on_thread_finished(force_reset=True)
        else: self.on_thread_finished(force_reset=True)
        self._is_stopping = False

    @Slot()
    def on_thread_finished(self, force_reset=False):
        print("Dictation thread finished signal received or stop forced.")
        if self.is_dictation_running or force_reset:
            self.is_dictation_running = False; self.reset_ui_after_stop()
        self.dictation_worker = None; self.dictation_thread = None
        print("Dictation worker/thread references cleared.")

    def reset_ui_after_stop(self):
        self.start_button.setEnabled(True); self.stop_button.setEnabled(False)
        self.set_config_enabled(True); self.update_status("Idle")

    def set_config_enabled(self, enabled: bool):
        self.model_combo.setEnabled(enabled); self.language_combo.setEnabled(enabled)
        self.vad_toggle_button.setEnabled(enabled); self.silence_spinbox.setEnabled(enabled)
        self.delay_spinbox.setEnabled(enabled); self.newline_edit.setEnabled(enabled)
        self.filter_list.setEnabled(enabled); self.filter_add_edit.setEnabled(enabled)
        self.filter_add_button.setEnabled(enabled); self.filter_remove_button.setEnabled(enabled)
        self.set_ptt_key_button.setEnabled(enabled); self.set_stop_key_button.setEnabled(enabled)
        self.restore_defaults_button.setEnabled(enabled)

    # --- Hotkey Handling ---
    def start_hotkey_listener(self):
        self.stop_hotkey_listener()
        print("Starting hotkey listener thread...")
        self.hotkey_thread = QThread(self)
        self.hotkey_worker = HotkeyWorker(
            ptt_key_str=self.loaded_settings.get('ptt_key_str', DEFAULT_PTT_KEY_STR),
            stop_key_str=self.loaded_settings.get('stop_key_str', DEFAULT_STOP_KEY_STR),
            capture_mode=False
        )
        self.hotkey_worker.moveToThread(self.hotkey_thread)
        self.hotkey_worker.ptt_pressed_signal.connect(self.on_ptt_pressed)
        self.hotkey_worker.ptt_released_signal.connect(self.on_ptt_released)
        self.hotkey_worker.stop_signal.connect(self.stop_signal_from_hotkey.emit)
        self.hotkey_worker.error_signal.connect(self.handle_hotkey_error)
        self.hotkey_thread.started.connect(self.hotkey_worker.start_listening)
        self.hotkey_thread.finished.connect(self.hotkey_worker.deleteLater)
        self.hotkey_thread.finished.connect(self.hotkey_thread.deleteLater)
        self.hotkey_thread.start()

    def stop_hotkey_listener(self):
        if self.hotkey_worker: self.hotkey_worker.stop_listening()
        if self.hotkey_thread and self.hotkey_thread.isRunning():
            self.hotkey_thread.quit()
            if not self.hotkey_thread.wait(1000): print("Warning: Hotkey thread did not stop gracefully.")
        self.hotkey_worker = None; self.hotkey_thread = None

    def restart_hotkey_listener(self):
        print("Restarting hotkey listener with updated keys...")
        self.start_hotkey_listener()

    @Slot()
    def on_ptt_pressed(self):
        if self.is_dictation_running: self.ptt_signal.emit(True)

    @Slot()
    def on_ptt_released(self):
        if self.is_dictation_running: self.ptt_signal.emit(False)

    @Slot(str)
    def handle_hotkey_error(self, error_msg):
         QMessageBox.warning(self, "Hotkey Listener Error", f"Error in hotkey listener: {error_msg}\nListener might need restarting.")

    # --- Cleanup on Close ---
    def closeEvent(self, event):
        """Ensure threads are stopped when the window is closed."""
        print("Close event triggered.")
        self.save_settings()
        self.stop_dictation()
        self.stop_hotkey_listener()
        if isinstance(self.dictation_thread, QThread) and self.dictation_thread.isRunning():
             print("Waiting for dictation thread...")
             start_wait = time.time()
             while self.dictation_thread.isRunning() and (time.time() - start_wait) < 1.5:
                 QApplication.processEvents()
                 time.sleep(0.05)
             if self.dictation_thread.isRunning(): print("Warning: Dictation thread still running.")
        if isinstance(self.hotkey_thread, QThread) and self.hotkey_thread.isRunning():
             print("Waiting for hotkey thread...")
             start_wait = time.time()
             while self.hotkey_thread.isRunning() and (time.time() - start_wait) < 0.7:
                 QApplication.processEvents()
                 time.sleep(0.05)
             if self.hotkey_thread.isRunning(): print("Warning: Hotkey thread still running.")
        event.accept()

# --- Main Execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        basedir = os.path.dirname(__file__)
        icon_path = os.path.join(basedir, "icon.ico")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            app.setWindowIcon(app_icon)
            print(f"Application icon set from: {icon_path}")
        else:
            print(f"Warning: Icon file not found at {icon_path}")
    except Exception as e:
        print(f"Error setting application icon: {e}")

    try:
        basedir = os.path.dirname(__file__)
        style_path = os.path.join(basedir, "style.qss")
        with open(style_path, "r") as f: _style = f.read(); app.setStyleSheet(_style)
        print("Stylesheet applied.")
    except FileNotFoundError: print(f"Stylesheet '{style_path}' not found.")
    except Exception as e: print(f"Error loading stylesheet: {e}")

    window = OmniDictateApp()
    window.show()
    sys.exit(app.exec())
