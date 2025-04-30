# main_gui.py

import sys
import time
import os
import torch

# PySide6 imports
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout,
                               QWidget, QLabel, QComboBox, QStatusBar, QMessageBox,
                               QSpinBox, QDoubleSpinBox, QHBoxLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QGroupBox, QGridLayout,
                               QCheckBox, QTextEdit, QApplication, QInputDialog, QProgressBar,
                               QSlider, QSizePolicy, QDial, QColorDialog, QVBoxLayout, QDialog, QFileDialog)
from PySide6.QtCore import Qt, QThread, Slot, Signal, QSettings, QTimer
from PySide6.QtGui import QIcon, QFont, QClipboard, QTextCursor, QKeySequence, QShortcut
import shiboken6  # Add this import for Qt object validity checking


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

from ollama_handler import OllamaHandler

# --- Configuration for Settings ---
CONFIG_ORG = "OmniCorp"
CONFIG_APP = "OmniDictate"

# --- Default Settings Constants ---
DEFAULT_MODEL_SIZE = "medium.en"
DEFAULT_LANGUAGE = "en"
DEFAULT_VAD_ENABLED = True
DEFAULT_SILENCE_THRESHOLD = 100
DEFAULT_CHAR_DELAY = 0.02
DEFAULT_PTT_KEY_STR = "keyboard.Key.shift_r"
DEFAULT_STOP_KEY_STR = "keyboard.Key.esc"
DEFAULT_NEW_LINE_COMMANDS = ["new line", "next line"]
DEFAULT_FILTER_WORDS = ["thanks for watching!","For more videos like this, subscribe to our channel.", "I'll see you in the next video.", "Thank you very much. ","thank you.", "thanks for watching", "Thanks for watching.", "thank you", "I'm sorry"," I'm sorry,", "I'm sorry, ", "I'm sorry,", "you ", "Thank you for watching! "]
DEFAULT_USE_GPU = True
DEFAULT_AUDIO_DEVICE = None  # Will be set to system default
DEFAULT_AUDIO_GAIN = 1.0


# --- Main Application Window ---
class OmniDictateApp(QMainWindow):
    ptt_signal = Signal(bool)
    stop_signal_from_hotkey = Signal()
    volume_update = Signal(float)  # New signal for volume updates

    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("OmniDictate")
        self.setGeometry(100, 100, 700, 600)  # Reduced height from 800 to 600
        
        # Initialize status bar first
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
        # Initialize variables
        self.is_dictation_running = False
        self.dictation_thread = None
        self.dictation_worker = None
        self.hotkey_thread = None
        self.hotkey_worker = None
        self.capture_hotkey_thread = None
        self.capture_hotkey_worker = None
        self.setting_key_for = None
        self.original_button_text = ""
        self._is_stopping = False
        
        # Initialize settings
        self.settings = QSettings(CONFIG_ORG, CONFIG_APP)
        self.ollama_handler = OllamaHandler()  # Initialize Ollama handler
        self.load_settings()

        # Setup UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Create UI sections
        self.create_control_section()
        self.create_status_section()
        self.create_transcription_display_section()
        self.create_ollama_section()
        self.create_config_section()
        self.main_layout.addStretch(0)

        # Connect signals after all UI elements are created
        self.dictation_button.clicked.connect(self.toggle_dictation)
        self.hf_login_button.clicked.connect(self.show_hf_login_dialog)
        self.device_toggle_button.clicked.connect(self.toggle_device)
        self.vad_toggle_button.clicked.connect(self.toggle_vad)
        self.copy_button.clicked.connect(self.copy_transcription)
        self.clear_button.clicked.connect(self.clear_transcription)
        self.set_ptt_key_button.clicked.connect(lambda: self.prepare_to_set_key('ptt'))
        self.set_stop_key_button.clicked.connect(lambda: self.prepare_to_set_key('stop'))
        self.stop_signal_from_hotkey.connect(self.stop_dictation)
        self.silence_spinbox.valueChanged.connect(self.update_silence_threshold)
        self.delay_spinbox.valueChanged.connect(self.update_typing_delay)  # Connect delay spinbox to update function

        self.model_combo.currentTextChanged.connect(self.save_settings)
        self.language_combo.currentTextChanged.connect(self.save_settings)
        self.silence_spinbox.valueChanged.connect(self.save_settings)
        self.delay_spinbox.valueChanged.connect(self.save_settings)
        
        # Initialize hotkey listener
        self.start_hotkey_listener()
        print("GUI Initialized.")

    # --- UI Creation Methods ---
    def create_control_section(self):
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout(control_group)  # Changed to QVBoxLayout for vertical stacking
        
        # Create top row for buttons
        button_layout = QHBoxLayout()
        
        # Create single button for dictation control
        self.dictation_button = QPushButton("Start Dictation")
        self.dictation_button.setObjectName("dictationButton")
        self.update_dictation_button_style(False)  # Initialize style
        
        # Add HF Login button
        self.hf_login_button = QPushButton("HF Login")
        self.hf_login_button.setFixedWidth(60)  # Make it compact
        
        # Add GPU/CPU toggle button
        self.device_toggle_button = QPushButton("GPU")
        self.device_toggle_button.setCheckable(True)
        self.device_toggle_button.setFixedWidth(60)
        self.device_toggle_button.setChecked(self.loaded_settings.get("use_gpu", DEFAULT_USE_GPU))
        self.update_device_button_style()

        # Add Audio Device Selector
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.audio_device_combo.setMaximumWidth(300)
        self.audio_device_combo.setToolTip("Select Audio Input Device")
        self.populate_audio_devices()
        
        self.vad_toggle_button = QPushButton("VAD: OFF")
        self.vad_toggle_button.setCheckable(True)
        self.vad_toggle_button.setChecked(self.loaded_settings.get("vad_enabled", False))
        self.update_vad_button_style()
        
        # Add buttons to layout
        button_layout.addWidget(self.dictation_button)
        button_layout.addWidget(self.hf_login_button)
        button_layout.addWidget(self.device_toggle_button)
        button_layout.addWidget(self.audio_device_combo)
        button_layout.addStretch()
        button_layout.addWidget(self.vad_toggle_button)
        
        # Add button layout to main control layout
        control_layout.addLayout(button_layout)

        # Create VU Meter section
        vu_container = QWidget()
        vu_layout = QHBoxLayout(vu_container)
        vu_layout.setContentsMargins(5, 5, 5, 5)
        
        # Add microphone icon and label
        mic_layout = QVBoxLayout()
        mic_label = QLabel("🎤")
        mic_label.setStyleSheet("QLabel { font-size: 16px; }")
        mic_label.setAlignment(Qt.AlignCenter)
        level_label = QLabel("Level")
        level_label.setAlignment(Qt.AlignCenter)
        mic_layout.addWidget(mic_label)
        mic_layout.addWidget(level_label)
        vu_layout.addLayout(mic_layout)
        
        # Create VU meters with labels
        meter_layout = QVBoxLayout()
        
        # Raw meter
        raw_layout = QHBoxLayout()
        raw_label = QLabel("Raw:")
        raw_label.setFixedWidth(35)
        self.raw_volume_meter = QProgressBar()
        self.raw_volume_meter.setMaximum(100)
        self.raw_volume_meter.setTextVisible(False)
        self.raw_volume_meter.setFixedHeight(15)
        self.raw_volume_meter.setStyleSheet("""
            QProgressBar {
                background-color: #333333;
                border: 1px solid #444444;
                border-radius: 7px;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 6px;
            }
        """)
        raw_layout.addWidget(raw_label)
        raw_layout.addWidget(self.raw_volume_meter)
        meter_layout.addLayout(raw_layout)
        
        # Processed meter
        proc_layout = QHBoxLayout()
        proc_label = QLabel("Proc:")
        proc_label.setFixedWidth(35)
        self.processed_volume_meter = QProgressBar()
        self.processed_volume_meter.setMaximum(100)
        self.processed_volume_meter.setTextVisible(False)
        self.processed_volume_meter.setFixedHeight(15)
        self.processed_volume_meter.setStyleSheet("""
            QProgressBar {
                background-color: #333333;
                border: 1px solid #444444;
                border-radius: 7px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 6px;
            }
        """)
        proc_layout.addWidget(proc_label)
        proc_layout.addWidget(self.processed_volume_meter)
        meter_layout.addLayout(proc_layout)
        
        vu_layout.addLayout(meter_layout)
        control_layout.addWidget(vu_container)
        
        self.main_layout.addWidget(control_group)

    def populate_audio_devices(self):
        """Populate the audio device combo box with available input devices."""
        import sounddevice as sd
        self.audio_device_combo.clear()
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:  # Only input devices
                    self.audio_device_combo.addItem(f"{dev['name']} ({dev['max_input_channels']}ch)", i)
            
            # Set the default/saved device
            saved_device = self.loaded_settings.get("audio_device")
            if saved_device is not None:
                index = self.audio_device_combo.findData(saved_device)
                if index >= 0:
                    self.audio_device_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"Error populating audio devices: {e}")
            self.audio_device_combo.addItem("Default Input")

    @Slot(int)
    def on_audio_device_changed(self, index):
        """Handle audio device selection changes."""
        device_id = self.audio_device_combo.itemData(index)
        self.settings.setValue("audio_device", device_id)
        if self.is_dictation_running:
            QMessageBox.information(
                self,
                "Device Changed",
                "The audio device change will take effect after restarting dictation."
            )

    @Slot(float)
    def update_raw_volume_meter(self, volume):
        """Update the raw volume meter with the given volume level."""
        try:
            if hasattr(self, 'raw_volume_meter') and self.raw_volume_meter is not None and not shiboken6.isValid(self.raw_volume_meter):
                return
            self.raw_volume_meter.setValue(int(volume * 100))
        except Exception:
            pass

    @Slot(float)
    def update_processed_volume_meter(self, volume):
        """Update the processed volume meter with the given volume level."""
        try:
            if hasattr(self, 'processed_volume_meter') and self.processed_volume_meter is not None and not shiboken6.isValid(self.processed_volume_meter):
                return
            self.processed_volume_meter.setValue(int(volume * 100))
        except Exception:
            pass

    @Slot(float)
    def update_volume_meter(self, volume):
        """Update the volume meter with smooth animation."""
        if hasattr(self, 'volume_meter') and not shiboken6.isValid(self.volume_meter):
            return
        try:
            # Scale volume to 0-1000 range
            level = min(1000, max(0, int(volume * 1000)))
            
            # Update the meter value
            self.volume_meter.setValue(level)
            
            # Update color based on level for visual feedback
            if level < 300:
                color = "#2ecc71"  # Green for low levels
            elif level < 700:
                color = "#f1c40f"  # Yellow for medium levels
            else:
                color = "#e74c3c"  # Red for high levels
            
            # Apply the color update
            self.volume_meter.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #ffffff;
                    border: none;
                    border-radius: 2px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 2px;
                }}
            """)
        except Exception as e:
            print(f"Error updating volume meter: {e}")

    def create_status_section(self):
        self.status_label = QLabel("Status: Idle")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)

    def create_transcription_display_section(self):
        display_group = QGroupBox("Transcription Output")
        display_layout = QVBoxLayout(display_group)
        self.transcription_display = QTextEdit()
        self.transcription_display.setReadOnly(False)  # Make it editable
        self.transcription_display.setPlaceholderText("Transcribed text will appear here... (You can edit this text)")
        self.transcription_display.setMinimumHeight(100)  # Set minimum height instead of fixed
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Add Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFixedWidth(80)
        self.clear_button.clicked.connect(self.clear_transcription)
        
        # Add Copy button
        self.copy_button = QPushButton("Copy Text")
        self.copy_button.setFixedWidth(100)
        
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.copy_button)
        
        display_layout.addWidget(self.transcription_display)
        display_layout.addLayout(button_layout)
        self.main_layout.addWidget(display_group)

    def create_ollama_section(self):
        """Create the Ollama text reformatting section."""
        # Create main container for Ollama section
        ollama_container = QWidget()
        ollama_container_layout = QVBoxLayout(ollama_container)
        ollama_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create header with toggle button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.ollama_toggle_button = QPushButton("▶")  # Right arrow (collapsed)
        self.ollama_toggle_button.setFixedWidth(30)
        self.ollama_toggle_button.setCheckable(True)
        self.ollama_toggle_button.setToolTip("Toggle Ollama Section (Ctrl+O)")
        
        header_label = QLabel("Ollama Text Reformatting")
        header_label.setStyleSheet("font-weight: bold;")
        
        # Initialize visibility state from settings - default to collapsed
        is_visible = self.loaded_settings.get("ollama_section_visible", False)  # Default to False (collapsed)
        self.ollama_toggle_button.setChecked(is_visible)
        self.ollama_toggle_button.setText("▼" if is_visible else "▶")
        self.ollama_toggle_button.clicked.connect(self.toggle_ollama_section)
        
        # Add keyboard shortcut for toggle
        toggle_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        toggle_shortcut.activated.connect(self.toggle_ollama_section)
        
        header_layout.addWidget(self.ollama_toggle_button)
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        # Create the main Ollama content
        self.ollama_content = QWidget()
        ollama_layout = QVBoxLayout(self.ollama_content)
        self.ollama_content.setVisible(is_visible)
        
        # System Prompt section
        prompt_label = QLabel("System Prompt:")
        self.system_prompt = QTextEdit()
        self.system_prompt.setPlaceholderText("Enter your system prompt here...")
        self.system_prompt.setMinimumHeight(40)
        
        # Reformatted Text section
        reformatted_label = QLabel("Reformatted Text:")
        self.reformatted_text = QTextEdit()
        self.reformatted_text.setReadOnly(False)
        self.reformatted_text.setPlaceholderText("Reformatted text will appear here... (You can edit this text)")
        self.reformatted_text.setMinimumHeight(80)
        
        # Model Selection section
        model_layout = QHBoxLayout()
        model_label = QLabel("Available Ollama Models:")
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Add reformat button
        self.reformat_button = QPushButton("Reformat Text")
        self.reformat_button.setFixedWidth(150)
        self.reformat_button.setToolTip("Reformat selected text (Ctrl+R)")
        self.reformat_button.clicked.connect(self.reformat_text)
        
        # Add keyboard shortcut for reformat
        reformat_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        reformat_shortcut.activated.connect(self.reformat_text)
        
        # Add refresh button for model list
        self.refresh_models_button = QPushButton("Refresh Models")
        self.refresh_models_button.setFixedWidth(150)
        self.refresh_models_button.setToolTip("Refresh Ollama models list (Ctrl+M)")
        self.refresh_models_button.clicked.connect(self.refresh_models)
        
        # Add keyboard shortcut for refresh
        refresh_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        refresh_shortcut.activated.connect(self.refresh_models)
        
        # Add loading indicator (initially hidden)
        self.loading_label = QLabel("Processing...")
        self.loading_label.setStyleSheet("color: blue;")
        self.loading_label.hide()
        
        # Add buttons to layout
        button_layout.addWidget(self.reformat_button)
        button_layout.addWidget(self.refresh_models_button)
        button_layout.addWidget(self.loading_label)
        button_layout.addStretch()
        
        model_layout.addWidget(model_label)
        model_layout.addStretch()
        model_layout.addLayout(button_layout)
        
        self.model_list = QListWidget()
        self.model_list.setMinimumHeight(80)
        self.model_list.setAlternatingRowColors(True)
        self.model_list.itemSelectionChanged.connect(self.on_model_selected)
        self.model_list.setToolTip("Select a model to use for text reformatting")
        
        # Add all components to the Ollama content layout
        ollama_layout.addWidget(prompt_label)
        ollama_layout.addWidget(self.system_prompt)
        ollama_layout.addWidget(reformatted_label)
        ollama_layout.addWidget(self.reformatted_text)
        ollama_layout.addLayout(model_layout)
        ollama_layout.addWidget(self.model_list)
        
        # Add header and content to container
        ollama_container_layout.addWidget(header_widget)
        ollama_container_layout.addWidget(self.ollama_content)
        
        self.main_layout.addWidget(ollama_container)
        
        # Initial model refresh
        self.refresh_models()

    def create_config_section(self):
        config_group = QGroupBox("Configuration")
        config_layout = QGridLayout(config_group)
        config_layout.setSpacing(10)
        row = 0

        # Create a horizontal layout for all controls in one line
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        # Add Whisper Model label with tooltip
        whisper_label = QLabel("Whisper Model:")
        whisper_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # Make it only as wide as needed
        whisper_label.setStyleSheet("""
            QLabel {
                color: #0066cc;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 4px;
                background-color: #e6f2ff;
            }
            QLabel:hover {
                background-color: #cce6ff;
            }
        """)
        whisper_label.setToolTip("""Whisper Model Information:

tiny:
Description: The smallest and fastest multilingual model. Offers the lowest accuracy among the options.
Use Case: Best for resource-constrained environments (low RAM/VRAM, mobile devices) or applications where speed is paramount and high accuracy isn't critical. Suitable for basic commands or near real-time transcription previews.
Size: ~39 Million parameters (~75 MB disk space, requires ~1 GB VRAM).

tiny.en:
Description: English-only version of tiny. Generally faster and potentially slightly more accurate for English than the multilingual tiny model.
Use Case: Same as tiny, but specifically when only English audio is expected.
Size: ~39 Million parameters (~75 MB disk space, requires ~1 GB VRAM).

base:
Description: A step up from tiny, offering a reasonable balance between speed and accuracy. Multilingual.
Use Case: Good starting point for general-purpose transcription on systems with moderate resources.
Size: ~74 Million parameters (~140 MB disk space, requires ~1 GB VRAM).

base.en:
Description: English-only version of base. Faster and potentially more accurate for English than the multilingual base model.
Use Case: Good choice for general-purpose English transcription when tiny.en isn't accurate enough.
Size: ~74 Million parameters (~140 MB disk space, requires ~1 GB VRAM).

small:
Description: Offers significantly better accuracy than base, but is slower and requires more resources. Multilingual.
Use Case: When higher accuracy is needed than base provides, and sufficient computational resources (CPU/GPU) are available.
Size: ~244 Million parameters (~460 MB disk space, requires ~2 GB VRAM).

small.en:
Description: English-only version of small. Faster and potentially more accurate for English transcription compared to the multilingual small model.
Use Case: A strong choice for high-quality English transcription when resources are moderately available.
Size: ~244 Million parameters (~460 MB disk space, requires ~2 GB VRAM).

medium:
Description: Provides high accuracy, approaching the level of the large models, but requires substantial resources. Multilingual.
Use Case: Excellent accuracy for multilingual transcription when computational resources (especially VRAM) are plentiful. Often a good balance before jumping to large.
Size: ~769 Million parameters (~1.4 GB disk space, requires ~5 GB VRAM).

medium.en:
Description: English-only version of medium. Offers high accuracy for English, potentially faster than the multilingual medium.
Use Case: High-accuracy English transcription when GPU resources are available.
Size: ~769 Million parameters (~1.4 GB disk space, requires ~5 GB VRAM).

large (v1, v2, v3):
Description: The largest and most accurate models (v3 generally being the latest and most robust). They are the slowest and most resource-intensive. Multilingual. V2 and V3 offer improvements in accuracy and robustness over V1.
Use Case: Situations requiring the highest possible accuracy, typically offline batch processing on powerful hardware (high-end GPUs with sufficient VRAM).
Size: ~1550 Million (1.55 Billion) parameters (~2.9 GB disk space, requires ~10 GB VRAM). Choose large-v3 if available for best performance.

distil-small.en:
Description: A distilled (compressed) version of small.en. Aims to be significantly faster and smaller than small.en while retaining most of its accuracy for English.
Use Case: When you need accuracy close to small.en but require much faster inference speeds or have slightly more limited resources. Ideal for English-only tasks demanding efficiency.
Size: Parameters significantly less than small.en (exact number varies, but designed for speed/size reduction). Disk size is roughly halved or more.

distil-medium.en:
Description: A distilled version of medium.en. Aims to be significantly faster and smaller than medium.en while retaining most of its accuracy for English.
Use Case: Faster, efficient alternative to medium.en for high-accuracy English transcription, suitable for production environments where speed matters.
Size: Parameters significantly less than medium.en. Disk size is roughly halved or more.

distil-large-v2 / distil-large-v3:
Description: Distilled versions of large-v2 / large-v3 respectively. They offer a substantial speed increase (often cited as ~6x faster) and reduced size (~50% smaller) compared to their parent large models, with only a minor potential decrease in accuracy. Multilingual. distil-large-v3 is distilled from large-v3.
Use Case: Excellent choice for achieving near large model accuracy with significantly better performance and lower resource requirements. Very suitable for production systems needing high-quality multilingual transcription efficiently. Choose v3 if available.
Size: Similar to medium models (~750-760 Million parameters, ~1.5 GB disk space).

General Guidance: Choose the smallest model that meets your accuracy requirements for your specific task and language(s) to maximize speed and minimize resource usage. Use .en models if you only process English audio. Use distilled models for significant speed improvements with minimal accuracy loss compared to their base model, especially for production use cases. large-v3 or distil-large-v3 generally offer the highest quality currently available.""")
        whisper_label.setToolTipDuration(30000)
        controls_layout.addWidget(whisper_label)
        
        # Add Whisper Model combo with appropriate size
        self.model_combo = QComboBox()
        self.model_combo.addItems(["medium.en", "distil-large-v2", "distil-large-v3", "distil-small.en", 
                                  "distil-medium.en", "large-v2", "large-v1", "medium", "base.en", "base", 
                                  "small.en", "small", "tiny.en", "tiny", "large-v3"])
        self.model_combo.setCurrentText(self.loaded_settings.get("model_size", DEFAULT_MODEL_SIZE))
        self.model_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)  # Adjust width to content
        self.model_combo.setMaximumWidth(150)  # Set maximum width
        controls_layout.addWidget(self.model_combo)
        
        controls_layout.addSpacing(20)  # Add some space between sections
        
        # Add theme selector
        theme_label = QLabel("Theme:")
        theme_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        controls_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "Custom"])
        self.theme_combo.setCurrentText(self.loaded_settings.get("theme", "Dark"))
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        self.theme_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.theme_combo.setMaximumWidth(80)
        controls_layout.addWidget(self.theme_combo)
        
        controls_layout.addSpacing(20)  # Add some space between sections
        
        # Add Language selector
        language_label = QLabel("Language:")
        language_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        controls_layout.addWidget(language_label)
        
        self.language_combo = QComboBox()
        self.language_combo.addItem("English (en)", "en")
        current_lang_code = self.loaded_settings.get("language", DEFAULT_LANGUAGE)
        index = self.language_combo.findData(current_lang_code)
        self.language_combo.setCurrentIndex(index if index != -1 else 0)
        self.language_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.language_combo.setMaximumWidth(120)
        controls_layout.addWidget(self.language_combo)
        
        controls_layout.addStretch()  # Add stretch at the end to keep everything left-aligned
        
        # Add the controls layout to the config layout
        config_layout.addLayout(controls_layout, row, 0, 1, 4)
        row += 1

        # Add Audio Processing section
        audio_group = QGroupBox("Audio Processing")
        audio_layout = QHBoxLayout()  # Use horizontal layout for compactness
        audio_layout.setSpacing(8)

        # Microphone Gain label
        gain_label = QLabel("Microphone Gain:")
        gain_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        audio_layout.addWidget(gain_label)

        # Gain QDial (smaller, default +0%)
        self.gain_dial = QDial()
        self.gain_dial.setRange(0, 300)  # 0-300% additional gain
        self.gain_dial.setValue(0)  # Default to +0%
        self.gain_dial.setNotchesVisible(True)
        self.gain_dial.setNotchTarget(10.0)
        self.gain_dial.setWrapping(False)
        self.gain_dial.setSingleStep(1)
        self.gain_dial.valueChanged.connect(self.on_gain_changed)
        self.gain_dial.setFixedSize(36, 36)  # Make dial small and nearly as high as label
        audio_layout.addWidget(self.gain_dial)

        # Gain value label
        self.gain_value_label = QLabel("+0%")
        self.gain_value_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        audio_layout.addWidget(self.gain_value_label)

        # Silence Threshold (compact)
        silence_label = QLabel("Silence Threshold (VAD):")
        silence_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        audio_layout.addWidget(silence_label)
        self.silence_spinbox = QSpinBox()
        self.silence_spinbox.setRange(0, 2000)
        self.silence_spinbox.setSingleStep(1)
        self.silence_spinbox.setValue(self.loaded_settings.get("silence_threshold", DEFAULT_SILENCE_THRESHOLD))
        self.silence_spinbox.setFixedWidth(60)
        audio_layout.addWidget(self.silence_spinbox)

        # Typing Delay (compact)
        delay_label = QLabel("Typing Delay (sec):")
        delay_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        audio_layout.addWidget(delay_label)
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setRange(0.0, 0.1)
        self.delay_spinbox.setSingleStep(0.005)
        self.delay_spinbox.setDecimals(3)
        self.delay_spinbox.setValue(self.loaded_settings.get("char_delay", DEFAULT_CHAR_DELAY))
        self.delay_spinbox.setFixedWidth(60)
        audio_layout.addWidget(self.delay_spinbox)

        audio_group.setLayout(audio_layout)
        config_layout.addWidget(audio_group, row, 0, 1, 4)
        row += 1

        # Create a horizontal layout for hotkey buttons
        hotkey_layout = QHBoxLayout()
        hotkey_layout.setSpacing(10)
        
        # Add PTT hotkey button on the left
        ptt_key = self.loaded_settings.get('ptt_key_str', DEFAULT_PTT_KEY_STR)
        self.set_ptt_key_button = QPushButton(f"PTT Hotkey: {ptt_key}")
        hotkey_layout.addWidget(self.set_ptt_key_button)
        
        # Add stop hotkey button on the right
        stop_key = self.loaded_settings.get('stop_key_str', DEFAULT_STOP_KEY_STR)
        self.set_stop_key_button = QPushButton(f"Stop Hotkey: {stop_key}")
        hotkey_layout.addWidget(self.set_stop_key_button)
        
        # Add the hotkey layout to the grid
        config_layout.addLayout(hotkey_layout, row, 0, 1, 4)
        
        config_layout.setColumnStretch(1, 1)
        config_layout.setColumnStretch(3, 1)
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
            "filter_words": self.settings.value("filter_words", DEFAULT_FILTER_WORDS),
            "hf_token": self.settings.value("hf_token", None),
            "use_gpu": self.settings.value("use_gpu", DEFAULT_USE_GPU, type=bool),
            "ollama_section_visible": self.settings.value("ollama_section_visible", True, type=bool),
            "audio_device": self.settings.value("audio_device", DEFAULT_AUDIO_DEVICE),
            "audio_gain": self.settings.value("audio_gain", DEFAULT_AUDIO_GAIN, type=float)
        }
        if not isinstance(self.loaded_settings["new_line_commands"], list): self.loaded_settings["new_line_commands"] = DEFAULT_NEW_LINE_COMMANDS
        if not isinstance(self.loaded_settings["filter_words"], list): self.loaded_settings["filter_words"] = DEFAULT_FILTER_WORDS
        print("Settings loaded:", self.loaded_settings)
        self.last_theme = self.settings.value("last_theme", "Dark")

    def save_settings(self):
        if self.setting_key_for: return
        print("Saving settings...")
        self.settings.setValue("model_size", self.model_combo.currentText())
        idx = self.language_combo.currentIndex()
        lang_code = self.language_combo.itemData(idx) if idx != -1 else DEFAULT_LANGUAGE
        self.settings.setValue("language", lang_code)
        self.settings.setValue("vad_enabled", self.vad_toggle_button.isChecked())
        self.settings.setValue("silence_threshold", self.silence_spinbox.value())
        self.settings.setValue("char_delay", self.delay_spinbox.value())
        
        # Extract key strings from button text
        ptt_key = self.set_ptt_key_button.text().replace("PTT Hotkey: ", "")
        stop_key = self.set_stop_key_button.text().replace("Stop Hotkey: ", "")
        self.settings.setValue("ptt_key_str", ptt_key)
        self.settings.setValue("stop_key_str", stop_key)
        
        # Keep the default values for removed UI elements
        self.settings.setValue("new_line_commands", DEFAULT_NEW_LINE_COMMANDS)
        self.settings.setValue("filter_words", DEFAULT_FILTER_WORDS)
        
        # Save GPU setting if it exists
        if hasattr(self, 'device_toggle_button'):
            self.settings.setValue("use_gpu", self.device_toggle_button.isChecked())
        
        self.settings.sync()
        print("Settings saved.")
        self.load_settings()
        if not self.is_dictation_running:
            self.restart_hotkey_listener()

    @Slot()
    def restore_default_settings(self):
        print("Restoring default settings...")
        self.model_combo.setCurrentText(DEFAULT_MODEL_SIZE)
        index = self.language_combo.findData(DEFAULT_LANGUAGE); self.language_combo.setCurrentIndex(index if index != -1 else 0)
        self.vad_toggle_button.setChecked(DEFAULT_VAD_ENABLED)
        self.silence_spinbox.setValue(DEFAULT_SILENCE_THRESHOLD)
        self.delay_spinbox.setValue(DEFAULT_CHAR_DELAY)
        self.set_ptt_key_button.setText(DEFAULT_PTT_KEY_STR)
        self.set_stop_key_button.setText(DEFAULT_STOP_KEY_STR)
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
        if self.setting_key_for == 'ptt':
            self.set_ptt_key_button.setText(f"PTT Hotkey: {key_str}")
        elif self.setting_key_for == 'stop':
            self.set_stop_key_button.setText(f"Stop Hotkey: {key_str}")
        self.finish_setting_key()
        self.save_settings()

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

    @Slot()
    def clear_transcription(self):
        """Clear the transcription display text box."""
        self.transcription_display.clear()
        self.statusBar.showMessage("Transcription cleared!", 2000)

    # --- GUI Control Methods ---
    def update_dictation_button_style(self, is_running: bool):
        """Update the dictation button appearance based on state."""
        if is_running:
            self.dictation_button.setText("Stop Dictation")
            self.dictation_button.setStyleSheet("""
                QPushButton#dictationButton {
                    background-color: #ff4444;
                    color: white;
                    padding: 5px 15px;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton#dictationButton:hover {
                    background-color: #ff6666;
                }
                QPushButton#dictationButton:pressed {
                    background-color: #cc0000;
                }
            """)
        else:
            self.dictation_button.setText("Start Dictation")
            self.dictation_button.setStyleSheet("""
                QPushButton#dictationButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 5px 15px;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton#dictationButton:hover {
                    background-color: #45a049;
                }
                QPushButton#dictationButton:pressed {
                    background-color: #388E3C;
                }
            """)

    def toggle_dictation(self):
        """Toggle between starting and stopping dictation."""
        if self.is_dictation_running:
            self.stop_dictation()
        else:
            self.start_dictation()

    def setup_signals(self):
        """Set up signal connections."""
        # This method will be called from start_dictation after worker is created
        if self.dictation_worker:
            self.dictation_worker.volume_level.connect(self.update_raw_volume_meter)
            self.dictation_worker.processed_volume_level.connect(self.update_processed_volume_meter)

    def start_dictation(self):
        if self.is_dictation_running:
            print("Dictation already running.")
            return

        print("Starting dictation...")
        self.update_status("Starting...")

        # Create and configure worker thread
        self.dictation_thread = QThread(self)
        self.dictation_worker = DictationWorker(
            gui_wid=int(self.winId()),
            model_size=self.model_combo.currentText(),
            language=self.language_combo.itemData(self.language_combo.currentIndex()),
            vad_enabled=self.vad_toggle_button.isChecked(),
            silence_threshold=self.silence_spinbox.value(),
            char_delay=self.delay_spinbox.value(),
            filter_words=self.loaded_settings.get("filter_words", []),
            new_line_commands=self.loaded_settings.get("new_line_commands", []),
            hf_token=self.loaded_settings.get("hf_token"),
            use_gpu=self.device_toggle_button.isChecked() if hasattr(self, 'device_toggle_button') else True,
            audio_device=self.audio_device_combo.currentData(),
            audio_gain=self.loaded_settings.get("audio_gain", DEFAULT_AUDIO_GAIN)
        )
        self.dictation_worker.moveToThread(self.dictation_thread)
        
        # Connect all signals
        self.dictation_worker.status_updated.connect(self.update_status)
        self.dictation_worker.transcription_ready.connect(self.handle_transcription)
        self.dictation_worker.error_occurred.connect(self.show_error)
        self.setup_signals()  # Set up volume meter signals
        
        # Connect PTT signal - ensure this happens before thread start
        self.ptt_signal.connect(self.dictation_worker.set_ptt_state)
        
        # Connect thread signals
        self.dictation_thread.started.connect(self.dictation_worker.start_processing)
        self.dictation_thread.finished.connect(self.dictation_worker.deleteLater)
        self.dictation_thread.finished.connect(self.dictation_thread.deleteLater)
        self.dictation_thread.finished.connect(self.on_thread_finished)
        
        # Update UI state
        self.is_dictation_running = True
        self.update_dictation_button_style(True)
        self.set_config_enabled(False)
        
        # Start the thread
        self.dictation_thread.start()
        print("Dictation thread initiated.")

    def stop_dictation(self):
        if not self.is_dictation_running and not self._is_stopping:
            print("Stop called but already stopped.")
            return
        if self._is_stopping:
            return
        self._is_stopping = True
        print("GUI requesting stop...")
        self.update_status("Stopping...")
        self.dictation_button.setEnabled(False)

        if self.dictation_worker:
            try:
                self.ptt_signal.disconnect(self.dictation_worker.set_ptt_state)
            except RuntimeError:
                pass  # Ignore if not connected or already disconnected
        if self.dictation_worker:
            self.dictation_worker.stop_processing()
        if self.dictation_thread and self.dictation_thread.isRunning():
            self.dictation_thread.quit()
            if not self.dictation_thread.wait(1500):
                print("Warning: Dictation thread didn't finish quitting.")
                self.on_thread_finished(force_reset=True)
        else:
            self.on_thread_finished(force_reset=True)
        self._is_stopping = False

    @Slot()
    def on_thread_finished(self, force_reset=False):
        print("Dictation thread finished signal received or stop forced.")
        if self.is_dictation_running or force_reset:
            self.is_dictation_running = False; self.reset_ui_after_stop()
        self.dictation_worker = None; self.dictation_thread = None
        print("Dictation worker/thread references cleared.")

    def reset_ui_after_stop(self):
        """Reset UI elements after stopping dictation."""
        self.dictation_button.setEnabled(True)
        self.update_dictation_button_style(False)
        self.set_config_enabled(True)
        self.update_status("Idle")
        self.update_raw_volume_meter(0.0)
        self.update_processed_volume_meter(0.0)

    def set_config_enabled(self, enabled: bool):
        """Enable or disable configuration controls."""
        self.model_combo.setEnabled(enabled)
        self.language_combo.setEnabled(enabled)
        self.vad_toggle_button.setEnabled(enabled)
        self.delay_spinbox.setEnabled(enabled)
        self.set_ptt_key_button.setEnabled(enabled)
        self.set_stop_key_button.setEnabled(enabled)
        if hasattr(self, 'device_toggle_button'):
            self.device_toggle_button.setEnabled(enabled)
        # Silence spinbox remains enabled for real-time adjustment

    @Slot(int)
    def update_silence_threshold(self, value):
        """Update the silence threshold in real-time if dictation is running."""
        if self.dictation_worker and self.is_dictation_running:
            self.dictation_worker.silence_threshold = value
            print(f"Silence threshold updated to: {value}")
            
    @Slot(float)
    def update_typing_delay(self, value):
        """Update the typing delay in real-time if dictation is running."""
        if self.dictation_worker and self.is_dictation_running:
            self.dictation_worker.char_delay = value
            print(f"Typing delay updated to: {value}")

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

    def show_hf_login_dialog(self):
        token, ok = QInputDialog.getText(
            self,
            "Hugging Face Login",
            "Enter your Hugging Face access token:\n\n"
            "You can find your token at: https://huggingface.co/settings/tokens",
            QLineEdit.Normal
        )
        if ok and token:
            self.settings.setValue("hf_token", token)
            QMessageBox.information(
                self,
                "Token Saved",
                "Your Hugging Face token has been saved successfully.\n"
                "You can now download models that require authentication."
            )

    # --- Cleanup on Close ---
    def closeEvent(self, event):
        """Ensure threads are stopped when the window is closed."""
        print("Close event triggered.")
        self.save_settings()
        self.stop_dictation()
        self.stop_hotkey_listener()
        
        # Clean up volume meters
        if hasattr(self, 'raw_volume_meter'):
            self.raw_volume_meter = None
        if hasattr(self, 'processed_volume_meter'):
            self.processed_volume_meter = None
            
        if isinstance(self.dictation_thread, QThread) and self.dictation_thread.isRunning():
            print("Waiting for dictation thread...")
            start_wait = time.time()
            while self.dictation_thread.isRunning() and (time.time() - start_wait) < 1.5:
                QApplication.processEvents()
                time.sleep(0.05)
            if self.dictation_thread.isRunning():
                print("Warning: Dictation thread still running.")
                
        if isinstance(self.hotkey_thread, QThread) and self.hotkey_thread.isRunning():
            print("Waiting for hotkey thread...")
            start_wait = time.time()
            while self.hotkey_thread.isRunning() and (time.time() - start_wait) < 0.7:
                QApplication.processEvents()
                time.sleep(0.05)
            if self.hotkey_thread.isRunning():
                print("Warning: Hotkey thread still running.")
                
        event.accept()

    @Slot()
    def toggle_device(self):
        """Toggle between GPU and CPU processing."""
        is_gpu = self.device_toggle_button.isChecked()
        print(f"\n[DEVICE] {'Enabling' if is_gpu else 'Disabling'} GPU processing")
        
        if is_gpu:
            print("\n[CUDA] Checking CUDA configuration...")
            try:
                if torch.cuda.is_available():
                    print(f"├── CUDA Version: {torch.version.cuda}")
                    print(f"├── PyTorch Version: {torch.__version__}")
                    print(f"├── GPU Device Count: {torch.cuda.device_count()}")
                    print(f"├── Current Device: {torch.cuda.current_device()}")
                    print(f"├── Device Name: {torch.cuda.get_device_name(0)}")
                    # Try to create a test tensor
                    test_tensor = torch.cuda.FloatTensor([1.])
                    print(f"└── Test tensor created successfully on {test_tensor.device}")
                else:
                    print("└── CUDA is not available. Check NVIDIA drivers and PyTorch installation.")
                    QMessageBox.warning(
                        self,
                        "GPU Not Available",
                        "CUDA is not available. Please check:\n\n"
                        "1. NVIDIA drivers are installed\n"
                        "2. PyTorch is installed with CUDA support\n"
                        "3. CUDA toolkit is properly installed"
                    )
                    self.device_toggle_button.setChecked(False)
                    return
            except Exception as e:
                print(f"└── Error checking CUDA: {str(e)}")
                QMessageBox.warning(
                    self,
                    "CUDA Error",
                    f"Error checking CUDA configuration:\n{str(e)}"
                )
                self.device_toggle_button.setChecked(False)
                return
            
        self.update_device_button_style()
        self.save_settings()
        
        if self.dictation_worker and self.is_dictation_running:
            print("\n[INFO] Device change will take effect after restart")
            QMessageBox.information(
                self,
                "Device Changed",
                "The device change will take effect after restarting dictation."
            )

    def update_device_button_style(self):
        """Update the GPU/CPU toggle button appearance."""
        is_gpu = self.device_toggle_button.isChecked()
        self.device_toggle_button.setText("GPU" if is_gpu else "CPU")
        self.device_toggle_button.setProperty("device_mode", is_gpu)
        self.style().polish(self.device_toggle_button)

    @Slot()
    def refresh_models(self):
        """Refresh the list of available Ollama models."""
        self.model_list.clear()
        models = self.ollama_handler.get_models()
        if models:
            self.model_list.addItems(models)
            self.statusBar.showMessage("Models refreshed successfully!", 2000)
        else:
            self.statusBar.showMessage("Failed to fetch models. Is Ollama running?", 3000)

    @Slot()
    def on_model_selected(self):
        """Handle model selection change."""
        selected_items = self.model_list.selectedItems()
        if selected_items:
            self.reformat_button.setEnabled(True)
        else:
            self.reformat_button.setEnabled(False)

    @Slot()
    def reformat_text(self):
        """Reformat the transcription text using selected Ollama model."""
        selected_items = self.model_list.selectedItems()
        if not selected_items:
            self.statusBar.showMessage("Please select a model first!", 2000)
            return

        model_name = selected_items[0].text()
        system_prompt = self.system_prompt.toPlainText().strip()
        input_text = self.transcription_display.toPlainText().strip()

        if not input_text:
            self.statusBar.showMessage("No text to reformat!", 2000)
            return

        # Show loading indicator and disable buttons
        self.loading_label.show()
        self.reformat_button.setEnabled(False)
        self.refresh_models_button.setEnabled(False)
        self.statusBar.showMessage(f"Reformatting text using {model_name}...")
        
        try:
            reformatted = self.ollama_handler.generate_text(model_name, system_prompt, input_text)
            self.reformatted_text.setPlainText(reformatted)
            self.statusBar.showMessage("Text reformatted!", 2000)
        except Exception as e:
            self.statusBar.showMessage(f"Error reformatting text: {str(e)}", 3000)
        finally:
            # Hide loading indicator and re-enable buttons
            self.loading_label.hide()
            self.reformat_button.setEnabled(True)
            self.refresh_models_button.setEnabled(True)

    @Slot(int)
    def on_gain_changed(self, value):
        """Handle microphone gain dial changes."""
        gain = 1.0 + (value / 100.0 * 3.0)  # 0-300% maps to 1.0-4.0
        self.gain_value_label.setText(f"+{value}%")
        self.settings.setValue("audio_gain", gain)
        if self.dictation_worker and self.is_dictation_running:
            self.dictation_worker.set_audio_gain(gain)

    @Slot(int)
    def on_preprocessing_changed(self, state):
        """Handle audio preprocessing option changes."""
        sender = self.sender()
        if isinstance(sender, QCheckBox):
            setting_name = sender.text().lower().replace(" ", "_")
            self.settings.setValue(setting_name, bool(state))
            if self.is_dictation_running:
                QMessageBox.information(
                    self,
                    "Preprocessing Changed",
                    "Audio preprocessing changes will take effect after restarting dictation."
                )

    def apply_theme(self, theme_name):
        """Apply the selected theme to the application."""
        if theme_name == "Custom":
            # Show color picker dialog for custom theme
            self.show_custom_theme_dialog()
            return

        if theme_name == "Dark":
            theme = {
                "background": "#2d2d2d",
                "text": "#ffffff",
                "button": "#0078d4",
                "button_hover": "#1084d9",
                "button_pressed": "#006cbd",
                "button_text": "#ffffff",
                "input_background": "#3d3d3d",
                "border": "#444444"
            }
        else:  # Light theme
            theme = {
                "background": "#f0f0f0",
                "text": "#000000",
                "button": "#0078d4",
                "button_hover": "#1084d9",
                "button_pressed": "#006cbd",
                "button_text": "#ffffff",
                "input_background": "#ffffff",
                "border": "#cccccc"
            }

        # Apply the theme
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {theme["background"]};
                color: {theme["text"]};
            }}
            
            QPushButton {{
                background-color: {theme["button"]};
                color: {theme["button_text"]};
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
            }}
            
            QPushButton:hover {{
                background-color: {theme["button_hover"]};
            }}
            
            QPushButton:pressed {{
                background-color: {theme["button_pressed"]};
            }}
            
            QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {theme["input_background"]};
                border: 1px solid {theme["border"]};
                border-radius: 4px;
                padding: 2px;
                color: {theme["text"]};
            }}
            
            QTextEdit {{
                background-color: {theme["input_background"]};
                border: 1px solid {theme["border"]};
                border-radius: 4px;
                padding: 4px;
                color: {theme["text"]};
            }}
            
            QGroupBox {{
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
            }}
            
            QGroupBox::title {{
                color: {theme["text"]};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }}
            
            QCheckBox {{
                color: {theme["text"]};
            }}
            
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {theme["border"]};
                border-radius: 3px;
                background-color: {theme["input_background"]};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {theme["button"]};
                border: 1px solid {theme["button"]};
            }}
        """)

        # Save the theme setting
        self.settings.setValue("theme", theme_name)
        self.settings.setValue("last_theme", theme_name)
        self.settings.sync()

    def show_custom_theme_dialog(self):
        """Show dialog for customizing theme colors."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Custom Theme")
        layout = QVBoxLayout(dialog)
        colors = {}
        color_names = ["Background", "Text", "Button", "Button Text", "QGroupBox"]
        color_labels = {}
        for name in color_names:
            btn = QPushButton(f"Select {name} Color")
            label = QLabel(f"{name} Color: Not Set")
            color_labels[name] = label
            def make_color_picker(btn, label, color_key):
                def pick_color():
                    color = QColorDialog.getColor()
                    if color.isValid():
                        colors[color_key] = color.name()
                        label.setText(f"{color_key} Color: {color.name()}")
                        label.setStyleSheet(f"color: {color.name()}")
                        self.apply_custom_colors(colors)  # Apply immediately
                return pick_color
            btn.clicked.connect(make_color_picker(btn, label, name.lower().replace(" ", "_")))
            layout.addWidget(btn)
            layout.addWidget(label)
        def apply_custom_theme():
            if len(colors) == len(color_names):
                self.apply_custom_colors(colors)
                dialog.accept()
        apply_btn = QPushButton("Apply Theme")
        apply_btn.clicked.connect(apply_custom_theme)
        layout.addWidget(apply_btn)
        # Save theme to JSON
        def save_theme_to_json():
            fname, _ = QFileDialog.getSaveFileName(dialog, "Save Theme As", "", "JSON Files (*.json)")
            if fname:
                import json
                with open(fname, "w") as f:
                    json.dump(colors, f, indent=2)
        save_btn = QPushButton("Save Theme to JSON")
        save_btn.clicked.connect(save_theme_to_json)
        layout.addWidget(save_btn)
        dialog.exec()

    def apply_custom_colors(self, colors):
        """Apply custom colors to the application theme."""
        theme = {
            "background": colors.get("background", "#222"),
            "text": colors.get("text", "#fff"),
            "button": colors.get("button", "#0078d4"),
            "button_text": colors.get("button_text", "#fff"),
            "qgroupbox": colors.get("qgroupbox", "#333"),
            "button_hover": self.adjust_color(colors.get("button", "#0078d4"), 1.1),
            "button_pressed": self.adjust_color(colors.get("button", "#0078d4"), 0.9),
            "input_background": self.adjust_color(colors.get("background", "#222"), 1.1),
            "border": self.adjust_color(colors.get("background", "#222"), 0.8)
        }
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {theme["background"]};
                color: {theme["text"]};
            }}
            QPushButton {{
                background-color: {theme["button"]};
                color: {theme["button_text"]};
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {theme["button_hover"]};
            }}
            QPushButton:pressed {{
                background-color: {theme["button_pressed"]};
            }}
            QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {theme["input_background"]};
                border: 1px solid {theme["border"]};
                border-radius: 4px;
                padding: 2px;
                color: {theme["text"]};
            }}
            QTextEdit {{
                background-color: {theme["input_background"]};
                border: 1px solid {theme["border"]};
                border-radius: 4px;
                padding: 4px;
                color: {theme["text"]};
            }}
            QGroupBox {{
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
                background-color: {theme["qgroupbox"]};
            }}
            QGroupBox::title {{
                color: {theme["qgroupbox"]};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }}
            QCheckBox {{
                color: {theme["text"]};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {theme["border"]};
                border-radius: 3px;
                background-color: {theme["input_background"]};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme["button"]};
                border: 1px solid {theme["button"]};
            }}
        """)
        # Save the theme setting and colors
        self.settings.setValue("theme", "Custom")
        for key, value in colors.items():
            self.settings.setValue(f"custom_theme_{key}", value)
        self.settings.sync()
        # Save last selected theme name
        self.settings.setValue("last_theme", "Custom")
        self.settings.sync()

    def adjust_color(self, color, factor):
        """Adjust color brightness by a factor."""
        from PySide6.QtGui import QColor
        c = QColor(color)
        h, s, v, a = c.getHsv()
        v = min(255, int(v * factor))
        c.setHsv(h, s, v, a)
        return c.name()

    def toggle_ollama_section(self):
        """Toggle the visibility of the Ollama section content."""
        is_visible = self.ollama_toggle_button.isChecked()
        self.ollama_content.setVisible(is_visible)
        self.ollama_toggle_button.setText("▼" if is_visible else "▶")  # Down arrow when visible, right arrow when hidden
        
        # Save the state in settings
        self.settings.setValue("ollama_section_visible", is_visible)
        self.settings.sync()
        
        # Adjust window height
        if is_visible:
            # Expand window to show Ollama section
            self.setMinimumHeight(600)  # Base height
            self.resize(self.width(), 1000)  # Expanded height
        else:
            # Collapse window to hide Ollama section
            self.setMinimumHeight(400)  # Reduced minimum height
            self.resize(self.width(), 600)  # Collapsed height

# --- Main Execution ---
if __name__ == "__main__":
    # --- Remove Deprecated High DPI Attributes ---
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling) # Deprecated
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps) # Deprecated

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

    # --- Apply Font (Optional) ---
    # font = QFont("Segoe UI", 10)
    # app.setFont(font)

    window = OmniDictateApp()
    window.show()
    sys.exit(app.exec())