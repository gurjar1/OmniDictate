# main_gui.py

import sys
import time
import os
import math

# PySide6 imports
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                               QWidget, QLabel, QComboBox, QStatusBar, QMessageBox,
                               QSpinBox, QDoubleSpinBox, QHBoxLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QGroupBox, QGridLayout,
                               QCheckBox, QTextEdit, QStackedWidget, QFrame, QProgressBar,
                               QSizePolicy, QScrollArea, QSpacerItem, QStyle)
from PySide6.QtCore import Qt, QThread, Slot, Signal, QSettings, QTimer, QSize, QRectF, QPointF
from PySide6.QtGui import QIcon, QFont, QClipboard, QTextCursor, QColor, QPalette, QPainter, QPen, QBrush, QPainterPath, QPixmap

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
DEFAULT_LANGUAGE = None
DEFAULT_VAD_ENABLED = True
DEFAULT_SILENCE_THRESHOLD = 500
DEFAULT_CHAR_DELAY = 0.02
DEFAULT_PTT_KEY_STR = "keyboard.Key.shift_r"

DEFAULT_FILTER_WORDS = ["thanks for watching!", "thank you.", "thanks for watching", "Thanks for watching.", "thank you", "I'm sorry"," I'm sorry,", "I'm sorry, ", "I'm sorry,"]


# --- Main Application Window ---
class OmniDictateApp(QMainWindow):
    ptt_signal = Signal(bool)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("OmniDictate")
        self.resize(800, 600)
        self.setMinimumSize(500, 400)
        
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

        # --- Main Layout Stack ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        # --- Create Pages ---
        self.page_dictation = QWidget()
        self.setup_dictation_page()
        self.stack.addWidget(self.page_dictation)

        self.page_settings = QWidget()
        self.setup_settings_page()
        self.stack.addWidget(self.page_settings)

        # --- Status Bar ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        self.statusBar.hide() 

        # --- Connect Signals ---
        self.start_button.clicked.connect(self.start_dictation)
        self.stop_button.clicked.connect(self.stop_dictation)
        self.vad_toggle_button.clicked.connect(self.toggle_vad)
        self.settings_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_settings))
        self.back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_dictation))
        
        self.copy_button.clicked.connect(self.copy_transcription)
        
        # Settings Connections
        self.filter_add_button.clicked.connect(self.add_filter_word)
        self.filter_remove_button.clicked.connect(self.remove_filter_word)
        self.set_ptt_key_button.clicked.connect(lambda: self.prepare_to_set_key('ptt'))
        
        self.restore_defaults_button.clicked.connect(self.restore_default_settings)

        # Auto-save connections
        self.model_combo.currentTextChanged.connect(self.save_settings)
        self.language_combo.currentTextChanged.connect(self.save_settings)
        self.silence_spinbox.valueChanged.connect(self.save_settings)
        self.delay_spinbox.valueChanged.connect(self.save_settings)


        self.start_hotkey_listener()
        self.update_vad_button_style() # Initialize button state
        print("GUI Initialized.")

    def create_gear_icon(self):
        """Draws a vector gear icon to ensure visibility."""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Colors
        color = QColor("#ffffff")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        
        center = QPointF(size/2, size/2)
        outer_radius = size * 0.45
        inner_radius = size * 0.25
        teeth = 8
        tooth_depth = size * 0.1
        
        path = QPainterPath()
        path.addEllipse(center, inner_radius, inner_radius)
        path.addEllipse(center, outer_radius, outer_radius) # Ring
        
        # Draw teeth
        for i in range(teeth):
            angle = 2 * math.pi * i / teeth
            pass
            
        # Let's draw a proper gear shape
        gear_path = QPainterPath()
        gear_path.setFillRule(Qt.WindingFill)
        
        r_out = size * 0.45
        r_in = size * 0.35
        r_hole = size * 0.15
        
        points = []
        for i in range(teeth * 2):
            angle = 2 * math.pi * i / (teeth * 2)
            r = r_out if i % 2 == 0 else r_in
            x = center.x() + r * math.cos(angle)
            y = center.y() + r * math.sin(angle)
            if i == 0: gear_path.moveTo(x, y)
            else: gear_path.lineTo(x, y)
        gear_path.closeSubpath()
        
        # Subtract hole
        hole_path = QPainterPath()
        hole_path.addEllipse(center, r_hole, r_hole)
        final_path = gear_path.subtracted(hole_path)
        
        painter.drawPath(final_path)
        painter.end()
        return QIcon(pixmap)

    def format_key_name(self, key_str):
        """Converts raw pynput key strings to user-friendly names."""
        if not key_str: return "" 
        
        key_map = {
            "keyboard.Key.shift_r": "Right Shift",
            "keyboard.Key.shift": "Left Shift",
            "keyboard.Key.ctrl_l": "Left Ctrl",
            "keyboard.Key.ctrl_r": "Right Ctrl",
            "keyboard.Key.alt_l": "Left Alt",
            "keyboard.Key.alt_r": "Right Alt",
            "keyboard.Key.esc": "Escape",
            "keyboard.Key.space": "Space",
            "keyboard.Key.enter": "Enter",
            "keyboard.Key.tab": "Tab",
            "keyboard.Key.caps_lock": "Caps Lock",
            "keyboard.Key.cmd": "Windows/Cmd",
            "keyboard.Key.f1": "F1", "keyboard.Key.f2": "F2", "keyboard.Key.f3": "F3",
            "keyboard.Key.f4": "F4", "keyboard.Key.f5": "F5", "keyboard.Key.f6": "F6",
            "keyboard.Key.f7": "F7", "keyboard.Key.f8": "F8", "keyboard.Key.f9": "F9",
            "keyboard.Key.f10": "F10", "keyboard.Key.f11": "F11", "keyboard.Key.f12": "F12"
        }
        # Handle single characters (e.g., 'a', '1')
        if key_str.startswith("'") and key_str.endswith("'") and len(key_str) == 3:
            return key_str[1].upper()
        
        return key_map.get(key_str, key_str.replace("keyboard.Key.", "").replace("_", " ").title())

    def setup_dictation_page(self):
        layout = QVBoxLayout(self.page_dictation)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- Header ---
        header_layout = QHBoxLayout()
        title = QLabel("OmniDictate")
        title.setObjectName("headerTitle")
        
        self.model_display_label = QLabel(f"Model: {self.loaded_settings.get('model_size', DEFAULT_MODEL_SIZE)}")
        self.model_display_label.setObjectName("settingLabel")
        self.model_display_label.setStyleSheet("color: #888; font-size: 10pt; margin-right: 10px;")

        self.settings_button = QPushButton()
        self.settings_button.setIcon(self.create_gear_icon())
        self.settings_button.setIconSize(QSize(24, 24))
        self.settings_button.setObjectName("iconButton")
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.setFixedSize(40, 40)
        self.settings_button.setToolTip("Settings")

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.model_display_label)
        header_layout.addWidget(self.settings_button)
        layout.addLayout(header_layout)

        # --- Transcription Area ---
        self.transcription_display = QTextEdit()
        self.transcription_display.setObjectName("transcriptionDisplay")
        self.transcription_display.setReadOnly(True)
        self.transcription_display.setPlaceholderText("Ready.")
        layout.addWidget(self.transcription_display)

        # --- Visual Hint Label ---
        self.hint_label = QLabel("")
        self.hint_label.setObjectName("hintLabel")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setFixedHeight(30)
        layout.addWidget(self.hint_label)

        # --- Visualizer ---
        self.visualizer = QProgressBar()
        self.visualizer.setObjectName("audioVisualizer")
        self.visualizer.setFixedHeight(4)
        self.visualizer.setTextVisible(False)
        self.visualizer.setRange(0, 1000) 
        self.visualizer.setValue(0)
        layout.addWidget(self.visualizer)

        # --- Floating Control Dock ---
        dock_container = QFrame()
        dock_container.setObjectName("controlDock")
        dock_container.setFixedHeight(80)
        dock_layout = QHBoxLayout(dock_container)
        dock_layout.setContentsMargins(20, 10, 20, 10)
        dock_layout.setSpacing(15)

        # Mode Toggle (VAD vs PTT) - Combined Button
        self.vad_toggle_button = QPushButton("VAD Mode")
        self.vad_toggle_button.setObjectName("modeButton")
        self.vad_toggle_button.setCheckable(True)
        self.vad_toggle_button.setChecked(self.loaded_settings.get("vad_enabled", DEFAULT_VAD_ENABLED))
        self.vad_toggle_button.setFixedSize(110, 45)
        self.vad_toggle_button.setCursor(Qt.PointingHandCursor)
        self.vad_toggle_button.setToolTip("Toggle between Voice Activity Detection and Push-to-Talk")

        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("startButton")
        self.start_button.setFixedSize(100, 45)
        self.start_button.setCursor(Qt.PointingHandCursor)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setFixedSize(100, 45)
        self.stop_button.setEnabled(False)
        self.stop_button.setCursor(Qt.PointingHandCursor)
        
        self.copy_button = QPushButton("Copy")
        self.copy_button.setFixedSize(80, 45)
        self.copy_button.setCursor(Qt.PointingHandCursor)

        dock_layout.addStretch()
        dock_layout.addWidget(self.vad_toggle_button)
        dock_layout.addWidget(self.start_button)
        dock_layout.addWidget(self.stop_button)
        dock_layout.addStretch()
        dock_layout.addWidget(self.copy_button)

        layout.addWidget(dock_container)

    def setup_settings_page(self):
        layout = QVBoxLayout(self.page_settings)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # --- Header ---
        header_layout = QHBoxLayout()
        self.back_button = QPushButton("← Back")
        self.back_button.setObjectName("backButton") # Specific ID for styling
        self.back_button.setFixedSize(100, 40)
        self.back_button.setCursor(Qt.PointingHandCursor)
        
        settings_title = QLabel("Settings")
        settings_title.setObjectName("headerTitle")
        settings_title.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(self.back_button)
        header_layout.addStretch()
        header_layout.addWidget(settings_title)
        header_layout.addStretch() 
        header_layout.addSpacing(100) # Balance
        layout.addLayout(header_layout)

        # --- Scroll Area for Settings ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        scroll.setWidget(content_widget)
        
        # Grid Layout for Settings Content
        grid = QGridLayout(content_widget)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(20)
        grid.setContentsMargins(10, 10, 20, 10)
        
        row = 0
        
        # --- AI Model Section ---
        grid.addWidget(QLabel("AI Model", objectName="sectionHeader"), row, 0, 1, 2); row += 1
        
        grid.addWidget(QLabel("Whisper Model:", objectName="settingLabel"), row, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["large-v3-turbo", "large-v3", "medium", "small", "base", "tiny"])
        self.model_combo.setCurrentText(self.loaded_settings.get("model_size", DEFAULT_MODEL_SIZE))
        grid.addWidget(self.model_combo, row, 1)
        
        # Language Selection
        grid.addWidget(QLabel("Language:", objectName="settingLabel"), row, 2)
        self.language_combo = QComboBox()
        
        # Populate languages
        languages = [
            ("Auto Detect", None),
            ("English", "en"),
            ("Spanish", "es"),
            ("French", "fr"),
            ("German", "de"),
            ("Italian", "it"),
            ("Portuguese", "pt"),
            ("Dutch", "nl"),
            ("Russian", "ru"),
            ("Chinese", "zh"),
            ("Japanese", "ja")
        ]
        for name, code in languages:
            self.language_combo.addItem(name, code)
            
        # Set current selection
        current_lang_code = self.loaded_settings.get("language", DEFAULT_LANGUAGE)
        index = self.language_combo.findData(current_lang_code)
        if index != -1:
            self.language_combo.setCurrentIndex(index)
        else:
            self.language_combo.setCurrentIndex(0) # Default to Auto Detect if unknown
        grid.addWidget(self.language_combo, row, 3); row += 1
        
        grid.addWidget(QLabel("Silence Threshold:", objectName="settingLabel"), row, 0)
        self.silence_spinbox = QSpinBox()
        self.silence_spinbox.setRange(50, 3000); self.silence_spinbox.setSingleStep(50)
        self.silence_spinbox.setValue(self.loaded_settings.get("silence_threshold", DEFAULT_SILENCE_THRESHOLD))
        grid.addWidget(self.silence_spinbox, row, 1)
        
        grid.addWidget(QLabel("Typing Delay (s):", objectName="settingLabel"), row, 2)
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setRange(0.0, 0.5); self.delay_spinbox.setSingleStep(0.005); self.delay_spinbox.setDecimals(3)
        self.delay_spinbox.setValue(self.loaded_settings.get("char_delay", DEFAULT_CHAR_DELAY))
        grid.addWidget(self.delay_spinbox, row, 3); row += 1

        # --- Hotkeys Section ---
        grid.addWidget(QLabel("Hotkeys", objectName="sectionHeader"), row, 0, 1, 2); row += 1
        
        grid.addWidget(QLabel("PTT Hotkey:", objectName="settingLabel"), row, 0)
        self.ptt_key_display_label = QLabel(self.format_key_name(self.loaded_settings.get('ptt_key_str', DEFAULT_PTT_KEY_STR)))
        self.ptt_key_display_label.setStyleSheet("color: #0A84FF; font-weight: bold;")
        self.set_ptt_key_button = QPushButton("Change")
        self.set_ptt_key_button.setCursor(Qt.PointingHandCursor)
        grid.addWidget(self.ptt_key_display_label, row, 1)
        grid.addWidget(self.set_ptt_key_button, row, 2); row += 1
        
        # --- Advanced Section ---
        grid.addWidget(QLabel("Advanced", objectName="sectionHeader"), row, 0, 1, 2); row += 1
        


        grid.addWidget(QLabel("Filter Words:", objectName="settingLabel"), row, 0, 1, 4); row += 1
        self.filter_list = QListWidget()
        self.filter_list.addItems(self.loaded_settings.get("filter_words", DEFAULT_FILTER_WORDS))
        self.filter_list.setFixedHeight(100)
        grid.addWidget(self.filter_list, row, 0, 1, 4); row += 1
        
        filter_controls = QHBoxLayout()
        self.filter_add_edit = QLineEdit()
        self.filter_add_edit.setPlaceholderText("Enter phrase...")
        self.filter_add_button = QPushButton("Add")
        self.filter_remove_button = QPushButton("Remove")
        filter_controls.addWidget(self.filter_add_edit)
        filter_controls.addWidget(self.filter_add_button)
        filter_controls.addWidget(self.filter_remove_button)
        grid.addLayout(filter_controls, row, 0, 1, 4); row += 1

        grid.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding), row, 0) # Spacer

        self.restore_defaults_button = QPushButton("Restore Defaults")
        self.restore_defaults_button.setStyleSheet("color: #888; background: transparent; border: 1px solid #444;")
        grid.addWidget(self.restore_defaults_button, row + 1, 0, 1, 4)

        layout.addWidget(scroll)


    # --- Settings Management ---
    def load_settings(self):
        self.loaded_settings = {
            "model_size": self.settings.value("model_size", DEFAULT_MODEL_SIZE),
            "language": self.settings.value("language", DEFAULT_LANGUAGE),
            "vad_enabled": self.settings.value("vad_enabled", DEFAULT_VAD_ENABLED, type=bool),
            "silence_threshold": self.settings.value("silence_threshold", DEFAULT_SILENCE_THRESHOLD, type=int),
            "char_delay": self.settings.value("char_delay", DEFAULT_CHAR_DELAY, type=float),
            "ptt_key_str": self.settings.value("ptt_key_str", DEFAULT_PTT_KEY_STR),

            "filter_words": self.settings.value("filter_words", DEFAULT_FILTER_WORDS)
        }


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
        self.settings.setValue("ptt_key_str", self.loaded_settings.get('ptt_key_str', DEFAULT_PTT_KEY_STR)) # Keep internal string
        

        filter_words = [self.filter_list.item(i).text() for i in range(self.filter_list.count())]
        self.settings.setValue("filter_words", filter_words)
        self.settings.sync(); print("Settings saved.")
        self.load_settings()
        self.model_display_label.setText(f"Model: {self.loaded_settings['model_size']}") 
        if not self.is_dictation_running: self.restart_hotkey_listener()

    @Slot()
    def restore_default_settings(self):
        print("Restoring default settings...")
        self.model_combo.setCurrentText(DEFAULT_MODEL_SIZE)
        index = self.language_combo.findData(DEFAULT_LANGUAGE); self.language_combo.setCurrentIndex(index if index != -1 else 0)
        self.vad_toggle_button.setChecked(DEFAULT_VAD_ENABLED)
        self.silence_spinbox.setValue(DEFAULT_SILENCE_THRESHOLD)
        self.delay_spinbox.setValue(DEFAULT_CHAR_DELAY)
        self.settings.setValue("ptt_key_str", DEFAULT_PTT_KEY_STR)
        
        self.ptt_key_display_label.setText(self.format_key_name(DEFAULT_PTT_KEY_STR))
        

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
        
        button = self.set_ptt_key_button
        self.original_button_text = button.text()
        button.setText("Press Key..."); button.setProperty("waitingInput", True); self.style().polish(button)
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
        # Update the internal setting string
        if self.setting_key_for == 'ptt': 
            self.loaded_settings["ptt_key_str"] = key_str # Update local cache
            self.ptt_key_display_label.setText(self.format_key_name(key_str))
        
        self.finish_setting_key(); self.save_settings()

    @Slot(str)
    def handle_key_capture_error(self, error_msg):
        QMessageBox.warning(self, "Hotkey Error", f"Could not capture key: {error_msg}")
        self.finish_setting_key(); self.start_hotkey_listener()

    def finish_setting_key(self):
        if not self.setting_key_for: return
        button = self.set_ptt_key_button
        button.setText(self.original_button_text if hasattr(self, 'original_button_text') and self.original_button_text else "Change")
        button.setProperty("waitingInput", False); self.style().polish(button)
        self.setting_key_for = None; self.set_other_controls_enabled(True)
        if self.capture_hotkey_worker: self.capture_hotkey_worker.stop_listening()
        if self.capture_hotkey_thread and self.capture_hotkey_thread.isRunning(): self.capture_hotkey_thread.quit(); self.capture_hotkey_thread.wait(500)
        self.capture_hotkey_worker = None; self.capture_hotkey_thread = None

    def set_other_controls_enabled(self, enabled):
        self.start_button.setEnabled(enabled and not self.is_dictation_running)
        self.stop_button.setEnabled(enabled and self.is_dictation_running)
        self.set_config_enabled(enabled)
        self.set_ptt_key_button.setEnabled(enabled)

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
        ptt_key_name = self.format_key_name(self.loaded_settings.get('ptt_key_str', DEFAULT_PTT_KEY_STR))
        
        if is_checked:
            self.vad_toggle_button.setText("VAD: ON")
        else:
            self.vad_toggle_button.setText("PTT: ON")
            
        # Update hint based on running state
        if not self.is_dictation_running:
            self.hint_label.setText("Select PTT or VAD mode and click Start")
            self.hint_label.setStyleSheet("color: #888; font-style: italic;")
        else:
            if is_checked:
                self.hint_label.setText("Listening for speech...")
                self.hint_label.setStyleSheet("color: #0A84FF; font-style: italic;")
            else:
                self.hint_label.setText(f"Hold '{ptt_key_name}' to speak")
                self.hint_label.setStyleSheet("color: #0A84FF; font-style: italic;")
        
        # Force style update
        self.vad_toggle_button.style().unpolish(self.vad_toggle_button)
        self.vad_toggle_button.style().polish(self.vad_toggle_button)

    # --- Slots for Worker Signals ---
    @Slot(str)
    def update_status(self, status_text):
        self.statusBar.showMessage(status_text)
        # Update hint label based on status if needed
        if "Listening" in status_text:
             self.update_vad_button_style() # Refresh hint text logic

    @Slot(str)
    def handle_transcription(self, text):
        current_text = self.transcription_display.toPlainText()
        prefix = "\n" if current_text and not current_text.endswith(('\n', ' ')) else ""
        if prefix == "" and current_text and not current_text.endswith(' '): prefix = " "
        self.transcription_display.insertPlainText(prefix + text.strip())
        self.transcription_display.moveCursor(QTextCursor.End)

    @Slot(float)
    def update_visualizer(self, amplitude):
        # Map amplitude (approx 0-2000) to progress bar (0-1000)
        val = int(amplitude)
        if val > 1000: val = 1000
        self.visualizer.setValue(val)

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
            char_delay=self.loaded_settings['char_delay'], filter_words=self.loaded_settings['filter_words']
        )
        self.dictation_worker.moveToThread(self.dictation_thread)
        self.dictation_worker.status_updated.connect(self.update_status)
        self.dictation_worker.transcription_ready.connect(self.handle_transcription)
        self.dictation_worker.error_occurred.connect(self.show_error)
        self.dictation_worker.audio_level.connect(self.update_visualizer) 
        self.dictation_thread.started.connect(self.dictation_worker.start_processing)
        self.dictation_thread.finished.connect(self.dictation_worker.deleteLater)
        self.dictation_thread.finished.connect(self.dictation_thread.deleteLater)
        self.dictation_thread.finished.connect(self.on_thread_finished)
        self.ptt_signal.connect(self.dictation_worker.set_ptt_state)
        self.update_status("Initializing..."); self.start_button.setEnabled(False); self.stop_button.setEnabled(True)
        self.set_config_enabled(False)
        self.dictation_thread.start(); self.is_dictation_running = True
        self.update_vad_button_style() # Update hint
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
                pass 
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
        self.visualizer.setValue(0)
        self.update_vad_button_style() # Reset hint
        print("Dictation worker/thread references cleared.")

    def reset_ui_after_stop(self):
        self.start_button.setEnabled(True); self.stop_button.setEnabled(False)
        self.set_config_enabled(True); self.update_status("Idle")

    def set_config_enabled(self, enabled: bool):
        self.model_combo.setEnabled(enabled); self.language_combo.setEnabled(enabled)
        # self.vad_toggle_button.setEnabled(enabled); # VAD toggle can be active during dictation
        self.silence_spinbox.setEnabled(enabled)
        self.delay_spinbox.setEnabled(enabled)
        self.filter_list.setEnabled(enabled); self.filter_add_edit.setEnabled(enabled)
        self.filter_add_button.setEnabled(enabled); self.filter_remove_button.setEnabled(enabled)
        self.set_ptt_key_button.setEnabled(enabled); 
        self.restore_defaults_button.setEnabled(enabled)

    # --- Hotkey Handling ---
    def start_hotkey_listener(self):
        self.stop_hotkey_listener()
        print("Starting hotkey listener thread...")
        self.hotkey_thread = QThread(self)
        self.hotkey_worker = HotkeyWorker(
            ptt_key_str=self.loaded_settings.get('ptt_key_str', DEFAULT_PTT_KEY_STR),
            capture_mode=False
        )
        self.hotkey_worker.moveToThread(self.hotkey_thread)
        self.hotkey_worker.ptt_pressed_signal.connect(self.on_ptt_pressed)
        self.hotkey_worker.ptt_released_signal.connect(self.on_ptt_released)
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
        if self.is_dictation_running: 
            self.ptt_signal.emit(True)
            # Visual feedback for PTT press
            if not self.vad_toggle_button.isChecked():
                self.hint_label.setText("Listening...")
                self.hint_label.setStyleSheet("color: #30D158; font-style: italic; font-weight: bold;")

    @Slot()
    def on_ptt_released(self):
        if self.is_dictation_running: 
            self.ptt_signal.emit(False)
            # Revert visual feedback
            if not self.vad_toggle_button.isChecked():
                ptt_key_name = self.format_key_name(self.loaded_settings.get('ptt_key_str', DEFAULT_PTT_KEY_STR))
                self.hint_label.setText(f"Hold '{ptt_key_name}' to speak")
                self.hint_label.setStyleSheet("color: #0A84FF; font-style: italic;")

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
    # --- Set AppUserModelID for Taskbar Icon ---
    try:
        import ctypes
        myappid = 'omnicorp.omnidictate.gui.2.0.1' # Arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"Error setting AppUserModelID: {e}")

    app = QApplication(sys.argv)

 # --- Set App Icon EARLY ---
    try:
        basedir = os.path.dirname(__file__)
        icon_path = os.path.join(basedir, "icon.ico")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            app.setWindowIcon(app_icon) # Set for the whole application
            print(f"Application icon set from: {icon_path}")
        else:
            print(f"Warning: Icon file not found at {icon_path}")
    except Exception as e:
        print(f"Error setting application icon: {e}")
    # --- End Set App Icon ---

    # --- Apply Stylesheet ---
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
