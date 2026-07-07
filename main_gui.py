import json
import math
import os
import sys

from PySide6.QtCore import QEvent, QObject, QMetaObject, QSettings, QSize, Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QBrush, QDesktopServices, QIcon, QPainter, QPainterPath, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QDoubleSpinBox,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app_settings import (
    CONFIG_APP,
    CONFIG_ORG,
    AppSettings,
    is_whisper_only_runtime,
    load_app_settings,
    migrate_release_defaults,
    sanitize_app_settings_for_runtime,
)
from app_updates import APP_VERSION, GITHUB_RELEASES_URL, check_latest_release
from core_logic import DictationWorker, create_backend
from engines.base import PreviewPayload, RuntimeDiagnostics
from engines.context_capture import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, VisualContextManager
from engines.runtime_detection import torch_cuda_is_available
from hotkey_listener import HotkeyWorker


class ContextDropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contextDropArea")
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self.title_label = QLabel("Drop images or video here")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.summary_label = QLabel("No attachments")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color: #888;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.summary_label)

    def set_summary(self, text: str):
        self.summary_label.setText(text or "No attachments")


class SettingsWheelGuard(QObject):
    """Keep page scrolling from accidentally changing hovered form controls."""

    def __init__(self, scroll_area: QScrollArea, parent=None):
        super().__init__(parent)
        self.scroll_area = scroll_area

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.Wheel:
            return False
        if isinstance(watched, QComboBox) and watched.view().isVisible():
            return False

        delta = event.pixelDelta().y() or event.angleDelta().y()
        if delta:
            scrollbar = self.scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.value() - delta)
        return True

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if self._filter_paths(paths):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        filtered_paths = self._filter_paths(paths)
        if filtered_paths:
            self.files_dropped.emit(filtered_paths)
            event.acceptProposedAction()
            return
        event.ignore()

    @staticmethod
    def _filter_paths(paths):
        accepted = []
        valid_extensions = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
        for path in paths:
            if os.path.splitext(path)[1].lower() in valid_extensions:
                accepted.append(path)
        return accepted


class ReasoningPreviewDialog(QDialog):
    def __init__(self, payload: PreviewPayload, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reasoning Preview")
        self.resize(640, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        intro = QLabel("Review the proposed text before it is typed into the active application.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(payload.typed_text)
        layout.addWidget(self.text_edit, 1)

        rationale_label = QLabel("Why this was suggested")
        rationale_label.setObjectName("settingLabel")
        layout.addWidget(rationale_label)

        self.rationale_view = QTextEdit()
        self.rationale_view.setReadOnly(True)
        self.rationale_view.setMaximumHeight(110)
        self.rationale_view.setPlainText(payload.rationale or "No rationale provided.")
        layout.addWidget(self.rationale_view)

        suggestions_label = QLabel("Suggestions")
        suggestions_label.setObjectName("settingLabel")
        layout.addWidget(suggestions_label)

        self.suggestions_list = QListWidget()
        self.suggestions_list.setMaximumHeight(90)
        suggestions = payload.suggestions or ["No additional suggestions."]
        for suggestion in suggestions:
            self.suggestions_list.addItem(QListWidgetItem(suggestion))
        layout.addWidget(self.suggestions_list)

        button_row = QHBoxLayout()
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self.copy_text)
        dismiss_button = QPushButton("Dismiss")
        dismiss_button.clicked.connect(self.reject)
        accept_button = QPushButton("Type Text")
        accept_button.clicked.connect(self.accept)
        button_row.addStretch()
        button_row.addWidget(copy_button)
        button_row.addWidget(dismiss_button)
        button_row.addWidget(accept_button)
        layout.addLayout(button_row)

    def typed_text(self) -> str:
        return self.text_edit.toPlainText().strip()

    def copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.typed_text())


class RuntimeDiagnosticsDialog(QDialog):
    def __init__(self, diagnostics: RuntimeDiagnostics, parent=None):
        super().__init__(parent)
        self.diagnostics = diagnostics
        self.setWindowTitle("Performance Check")
        self.resize(620, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        headline = QLabel(diagnostics.headline)
        headline.setObjectName("cardTitle")
        headline.setWordWrap(True)
        layout.addWidget(headline)

        summary = QLabel(diagnostics.summary)
        summary.setObjectName("cardSubtitle")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        if diagnostics.next_steps:
            steps_label = QLabel("What to do next")
            steps_label.setObjectName("settingTitle")
            layout.addWidget(steps_label)

            steps_text = QLabel("\n".join(f"{index}. {step}" for index, step in enumerate(diagnostics.next_steps, start=1)))
            steps_text.setWordWrap(True)
            steps_text.setObjectName("helperText")
            layout.addWidget(steps_text)

        if diagnostics.actions:
            links_label = QLabel("Helpful links")
            links_label.setObjectName("settingTitle")
            layout.addWidget(links_label)

            links_layout = QGridLayout()
            links_layout.setContentsMargins(0, 0, 0, 0)
            links_layout.setHorizontalSpacing(8)
            links_layout.setVerticalSpacing(8)
            for index, action in enumerate(diagnostics.actions):
                button = QPushButton(action.label)
                button.clicked.connect(lambda _checked=False, url=action.url: QDesktopServices.openUrl(QUrl(url)))
                links_layout.addWidget(button, index // 2, index % 2)
            layout.addLayout(links_layout)

        details_label = QLabel("Technical details")
        details_label.setObjectName("settingTitle")
        layout.addWidget(details_label)

        details = QTextEdit()
        details.setReadOnly(True)
        details.setMaximumHeight(120)
        details.setPlainText("\n".join(diagnostics.technical_details) or "No technical details recorded yet.")
        layout.addWidget(details)

        button_row = QHBoxLayout()
        copy_button = QPushButton("Copy diagnostics")
        copy_button.clicked.connect(self.copy_diagnostics)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_row.addStretch()
        button_row.addWidget(copy_button)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

    def copy_diagnostics(self):
        QApplication.clipboard().setText(self.diagnostics.plain_text())


class ModelPreloadWorker(QObject):
    status_updated = Signal(str)
    preload_completed = Signal(str)
    preload_failed = Signal(str)

    def __init__(self, app_settings: AppSettings, parent=None):
        super().__init__(parent)
        self.app_settings = app_settings

    @Slot()
    def run(self):
        backend = None
        try:
            backend = create_backend(self.app_settings)
            self.status_updated.emit(f"Preloading {self.app_settings.model_display_name}...")
            load_result = backend.load()
            for warning in load_result.warnings:
                self.status_updated.emit(warning)
            if load_result.success:
                self.preload_completed.emit(load_result.status_message)
            else:
                self.preload_failed.emit(load_result.status_message)
        except Exception as exc:
            self.preload_failed.emit(str(exc))
        finally:
            if backend is not None:
                try:
                    backend.unload()
                except Exception:
                    pass


class UpdateCheckWorker(QObject):
    update_available = Signal(str, str)
    no_update_available = Signal(str)
    update_check_failed = Signal(str)

    @Slot()
    def run(self):
        try:
            update_info = check_latest_release(current_version=APP_VERSION, timeout=5.0)
        except Exception as exc:
            self.update_check_failed.emit(str(exc))
            return

        if update_info.update_available:
            self.update_available.emit(update_info.latest_version, update_info.release_url)
        else:
            latest = update_info.latest_version or APP_VERSION
            self.no_update_available.emit(latest)


class OmniDictateApp(QMainWindow):
    ptt_signal = Signal(bool)
    manual_type_signal = Signal(str)
    prompt_mode_signal = Signal(str)

    def __init__(self, start_hotkeys: bool = True, enable_preload: bool = True):
        super().__init__()

        self.setWindowTitle("OmniDictate")
        self.resize(900, 680)
        self.setMinimumSize(640, 480)

        self.settings = QSettings(CONFIG_ORG, CONFIG_APP)
        self.whisper_only_runtime = is_whisper_only_runtime()
        defaults_migrated = migrate_release_defaults(self.settings)
        self.app_settings = AppSettings.from_qsettings(self.settings)
        if self.app_settings.language in ["None", ""]:
            self.app_settings.language = None
        self.runtime_profile_notices = sanitize_app_settings_for_runtime(self.app_settings)
        self.runtime_diagnostics: RuntimeDiagnostics | None = None
        if defaults_migrated:
            self.runtime_profile_notices.append(
                "Release defaults applied: large-v3-turbo, English, and active-app typing."
            )
        if self.runtime_profile_notices or defaults_migrated:
            self.app_settings.write_to_qsettings(self.settings)
        self.visual_context_manager = VisualContextManager(self.app_settings)

        self.dictation_thread = None
        self.dictation_worker = None
        self.hotkey_worker = None
        self.capture_hotkey_worker = None
        self.download_thread = None
        self.download_worker = None
        self.download_progress_dialog = None
        self.preload_thread = None
        self.preload_worker = None
        self.update_thread = None
        self.update_worker = None
        self.is_dictation_running = False
        self.setting_key_for = None
        self.original_button_text = ""
        self._is_stopping = False
        self._allow_global_hotkeys = start_hotkeys
        self._enable_preload = enable_preload
        self._suspend_settings_events = False
        self._settings_controls_enabled = True

        self.central_widget = QWidget()
        self.central_widget.setObjectName("appRoot")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        self.page_dictation = QWidget()
        self.page_dictation.setObjectName("pageDictation")
        self.setup_dictation_page()
        self.stack.addWidget(self.page_dictation)

        self.page_settings = QWidget()
        self.page_settings.setObjectName("pageSettings")
        self.setup_settings_page()
        self.stack.addWidget(self.page_settings)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.hide()

        self._hint_restore_timer = QTimer(self)
        self._hint_restore_timer.setSingleShot(True)
        self._hint_restore_timer.timeout.connect(self.update_vad_button_style)

        self.start_button.clicked.connect(self.start_dictation)
        self.stop_button.clicked.connect(self.stop_dictation)
        self.vad_toggle_button.clicked.connect(self.toggle_vad)
        self.settings_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_settings))
        self.back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_dictation))
        self.copy_button.clicked.connect(self.copy_transcription)
        self.filter_add_button.clicked.connect(self.add_filter_word)
        self.filter_remove_button.clicked.connect(self.remove_filter_word)
        self.set_ptt_key_button.clicked.connect(lambda: self.prepare_to_set_key("ptt"))
        self.restore_defaults_button.clicked.connect(self.restore_default_settings)
        self.check_updates_button.clicked.connect(self.check_for_updates)
        self.attach_context_button.clicked.connect(self.select_context_files)
        self.clear_context_button.clicked.connect(self.clear_context_assets)
        self.context_drop_area.files_dropped.connect(self.handle_files_dropped)
        self.model_path_browse_button.clicked.connect(self.browse_model_path)
        self.download_model_button.clicked.connect(self.download_selected_model)
        self.backend_combo.currentIndexChanged.connect(self.on_backend_changed)
        self.gemma_audio_mode_combo.currentIndexChanged.connect(self.on_backend_changed)

        self._connect_auto_save_signals()
        self.apply_settings_to_widgets()
        if self._allow_global_hotkeys:
            self.start_hotkey_listener()
        self.update_vad_button_style()
        self.update_transport_button_state()
        self.update_status_strip()
        if self.runtime_profile_notices:
            QTimer.singleShot(0, self.show_runtime_profile_notice)
        if self._enable_preload and self.app_settings.preload_model_on_launch:
            QTimer.singleShot(0, self.start_model_preload)

    def show_runtime_profile_notice(self):
        notice = "Whisper-only build reset saved experimental settings to Faster-Whisper / Pure transcription."
        self.statusBar.show()
        self.statusBar.showMessage(notice, 8000)

    def _connect_auto_save_signals(self):
        auto_save_widgets = [
            self.backend_combo,
            self.model_combo,
            self.gemma_model_combo,
            self.quantization_combo,
            self.gemma_audio_mode_combo,
            self.language_combo,
            self.prompt_mode_combo,
            self.screen_target_combo,
            self.image_budget_combo,
        ]
        for widget in auto_save_widgets:
            widget.currentIndexChanged.connect(self.save_settings)

        self.silence_spinbox.valueChanged.connect(self.save_settings)
        self.delay_spinbox.valueChanged.connect(self.save_settings)
        self.type_into_active_app_checkbox.toggled.connect(self.save_settings)
        self.min_ptt_duration_spinbox.valueChanged.connect(self.save_settings)
        self.capture_interval_spinbox.valueChanged.connect(self.save_settings)
        self.video_frame_spinbox.valueChanged.connect(self.save_settings)
        self.screen_context_checkbox.toggled.connect(self.save_settings)
        self.webcam_checkbox.toggled.connect(self.save_settings)
        self.preload_model_checkbox.toggled.connect(self.save_settings)
        self.reasoning_preview_checkbox.toggled.connect(self.save_settings)
        self.model_path_edit.editingFinished.connect(self.save_settings)
        self.gguf_server_url_edit.editingFinished.connect(self.save_settings)
        self.gguf_model_name_edit.editingFinished.connect(self.save_settings)
        self.prompt_mode_combo.currentIndexChanged.connect(self.on_backend_changed)
        self.screen_context_checkbox.toggled.connect(self.on_backend_changed)

    def _register_base_tooltip(self, widget, text: str):
        widget.setProperty("baseToolTip", text)
        widget.setToolTip(text)

    def _set_control_enabled(self, widget, enabled: bool, disabled_reason: str | None = None):
        widget.setEnabled(enabled)
        if enabled:
            widget.setToolTip(str(widget.property("baseToolTip") or ""))
            return
        widget.setToolTip(disabled_reason or str(widget.property("baseToolTip") or "Unavailable for this setup."))

    def _set_combo_item_enabled(self, combo: QComboBox, value, enabled: bool, tooltip: str):
        index = combo.findData(value)
        if index == -1:
            return
        combo.setItemData(index, tooltip, Qt.ToolTipRole)
        model = combo.model()
        item = model.item(index) if hasattr(model, "item") else None
        if item is not None:
            item.setEnabled(enabled)

    def _ensure_enabled_combo_selection(self, combo: QComboBox):
        model = combo.model()
        current_index = combo.currentIndex()
        current_item = model.item(current_index) if hasattr(model, "item") and current_index >= 0 else None
        if current_item is None or current_item.isEnabled():
            return
        for index in range(combo.count()):
            item = model.item(index) if hasattr(model, "item") else None
            if item is None or item.isEnabled():
                combo.setCurrentIndex(index)
                return

    def _build_inline_widget(self, *widgets: QWidget) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for widget in widgets:
            layout.addWidget(widget)
        return container

    def _create_info_button(self, help_text: str) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName("infoButton")
        button.setText("i")
        button.setAutoRaise(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setToolTip(help_text)
        return button

    def _create_settings_card(self, title: str, subtitle: str):
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("cardSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        body = QVBoxLayout()
        body.setSpacing(10)
        layout.addLayout(body)
        return card, body

    def _create_settings_row(self, title: str, description: str, help_text: str, *controls: QWidget):
        row = QFrame()
        row.setObjectName("settingsRow")
        row.setMinimumHeight(76)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(16)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)
        title_label = QLabel(title)
        title_label.setObjectName("settingTitle")
        title_row.addWidget(title_label)
        title_row.addWidget(self._create_info_button(help_text))
        title_row.addStretch()

        description_label = QLabel(description)
        description_label.setObjectName("helperText")
        description_label.setWordWrap(True)

        left_layout.addLayout(title_row)
        left_layout.addWidget(description_label)

        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(8)
        for control in controls:
            control_layout.addWidget(control)

        layout.addLayout(left_layout, 5)
        layout.addLayout(control_layout, 4)
        return row

    def _prompt_mode_label(self, prompt_mode: str | None = None) -> str:
        mapping = {
            "pure": "Pure transcription",
            "context": "Context-enhanced",
            "reasoning": "Full reasoning",
        }
        return mapping.get(prompt_mode or self.app_settings.prompt_mode, prompt_mode or self.app_settings.prompt_mode)

    def _supports_visual_features(self, backend: str | None = None, prompt_mode: str | None = None) -> bool:
        if self.whisper_only_runtime:
            return False
        backend = backend or self.app_settings.backend
        prompt_mode = prompt_mode or self.app_settings.prompt_mode
        return backend != "faster-whisper" and prompt_mode in {"context", "reasoning"}

    def _update_settings_summary(self):
        if not hasattr(self, "settings_summary_label"):
            return
        backend = self.backend_combo.currentData() if hasattr(self, "backend_combo") else self.app_settings.backend
        prompt_mode = self.prompt_mode_combo.currentData() if hasattr(self, "prompt_mode_combo") else self.app_settings.prompt_mode
        audio_mode = (
            self.gemma_audio_mode_combo.currentData()
            if hasattr(self, "gemma_audio_mode_combo")
            else self.app_settings.gemma_audio_input_mode
        )

        if self.whisper_only_runtime:
            summary = "Fastest and simplest local dictation. This public build only transcribes speech with Faster-Whisper."
        elif backend == "faster-whisper":
            summary = "Fastest and simplest local dictation. OmniDictate will only transcribe speech, so screen and reasoning controls stay parked until you switch to a Gemma experience."
        elif backend == "gemma-gguf-server":
            summary = "External server mode. OmniDictate drafts the transcript locally with Whisper, then your local GGUF server can refine it with optional visual context."
        elif audio_mode == "native-audio":
            summary = "Experimental direct Gemma listening mode. It can use multimodal audio natively, but it is the slowest path and standard dtype loading is safest today."
        elif prompt_mode == "pure":
            summary = "Hybrid Gemma is selected, but Pure transcription keeps the fast Whisper-only path until you ask for context or reasoning."
        else:
            summary = "Balanced hybrid mode. Whisper handles the first draft, then Gemma can clean up names, numbers, and screen-aware details with better latency than native audio."
        self.settings_summary_label.setText(summary)

    def _uses_gemma_hybrid_audio(self) -> bool:
        backend = self.backend_combo.currentData()
        return backend == "gemma-gguf-server" or (backend == "gemma-4" and self.gemma_audio_mode_combo.currentData() == "hybrid-whisper")

    def _active_whisper_model_setting(self) -> str:
        if self._uses_gemma_hybrid_audio():
            return self.app_settings.gemma_hybrid_whisper_model
        return self.app_settings.whisper_model

    def _format_context_status(self, description: str | None) -> str:
        if self.whisper_only_runtime:
            return "Context: off"
        normalized = (description or "").strip() or "No visual context"
        if self.app_settings.prompt_mode == "pure":
            if normalized == "No visual context":
                return "Context: off"
            return f"Context: saved, but Pure mode ignores it ({normalized})"
        if self.app_settings.backend == "faster-whisper":
            if normalized == "No visual context":
                return "Context: off"
            return f"Context: configured, but Faster-Whisper ignores visual input ({normalized})"
        return f"Context: {normalized}"

    def _has_visual_context(self, description: str | None = None) -> bool:
        normalized = (description or "").strip()
        return bool(normalized and normalized != "No visual context")

    def _estimate_route_label(self, description: str | None = None) -> str:
        backend = self.backend_combo.currentData() if hasattr(self, "backend_combo") else self.app_settings.backend
        prompt_mode = self.prompt_mode_combo.currentData() if hasattr(self, "prompt_mode_combo") else self.app_settings.prompt_mode
        audio_mode = (
            self.gemma_audio_mode_combo.currentData()
            if hasattr(self, "gemma_audio_mode_combo")
            else self.app_settings.gemma_audio_input_mode
        )
        has_visual_context = self._has_visual_context(description)

        if backend == "faster-whisper":
            return "Whisper only"

        if backend == "gemma-gguf-server":
            if prompt_mode == "pure" or (prompt_mode == "context" and not has_visual_context):
                return "Whisper only"
            return "Whisper -> GGUF server"

        if audio_mode == "native-audio":
            return "Native Gemma audio"

        if prompt_mode == "pure" or (prompt_mode == "context" and not has_visual_context):
            return "Whisper only"
        return "Whisper -> Gemma"

    def _set_route_status(self, label: str | None) -> None:
        route_label = (label or "").strip() or self._estimate_route_label()
        self.route_status_label.setText(f"Path: {route_label}")

    def _sync_whisper_model_combo(self) -> None:
        target_model = self._active_whisper_model_setting()
        if not target_model:
            return
        self.model_combo.blockSignals(True)
        self.model_combo.setCurrentText(target_model)
        self.model_combo.blockSignals(False)

    def create_gear_icon(self):
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#12344c")))
        center = size / 2
        outer_radius = size * 0.45
        inner_radius = size * 0.15
        teeth = 8
        gear_path = QPainterPath()
        for index in range(teeth * 2):
            angle = 2 * math.pi * index / (teeth * 2)
            radius = outer_radius if index % 2 == 0 else outer_radius * 0.78
            x = center + radius * math.cos(angle)
            y = center + radius * math.sin(angle)
            if index == 0:
                gear_path.moveTo(x, y)
            else:
                gear_path.lineTo(x, y)
        gear_path.closeSubpath()
        hole = QPainterPath()
        hole.addEllipse(center - inner_radius, center - inner_radius, inner_radius * 2, inner_radius * 2)
        painter.drawPath(gear_path.subtracted(hole))
        painter.end()
        return QIcon(pixmap)

    def format_key_name(self, key_str):
        if not key_str:
            return ""
        key_map = {
            "key:shift_r": "Right Shift",
            "key:shift": "Left Shift",
            "key:ctrl_l": "Left Ctrl",
            "key:ctrl_r": "Right Ctrl",
            "key:alt_l": "Left Alt",
            "key:alt_r": "Right Alt",
            "key:esc": "Escape",
            "key:space": "Space",
            "key:enter": "Enter",
            "key:tab": "Tab",
            "key:caps_lock": "Caps Lock",
            "key:cmd": "Windows/Cmd",
        }
        if key_str.startswith("char:"):
            return key_str.split(":", 1)[1].upper()
        if key_str.startswith("vk:"):
            return f"VK {key_str.split(':', 1)[1]}"
        if key_str in key_map:
            return key_map[key_str]
        if key_str.startswith("keyboard.Key."):
            return key_str.replace("keyboard.Key.", "").replace("_", " ").title()
        return key_str

    def setup_dictation_page(self):
        layout = QVBoxLayout(self.page_dictation)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        title = QLabel("OmniDictate")
        title.setObjectName("headerTitle")

        self.model_display_label = QLabel()
        self.model_display_label.setObjectName("settingLabel")
        self.model_display_label.setStyleSheet("color: #888; font-size: 10pt; margin-right: 10px;")

        self.runtime_status_button = QPushButton("Runtime: Not checked")
        self.runtime_status_button.setObjectName("runtimeStatusButton")
        self.runtime_status_button.setCursor(Qt.PointingHandCursor)
        self.runtime_status_button.clicked.connect(self.show_runtime_diagnostics)

        self.settings_button = QPushButton()
        self.settings_button.setIcon(self.create_gear_icon())
        self.settings_button.setIconSize(QSize(24, 24))
        self.settings_button.setObjectName("iconButton")
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.setFixedSize(40, 40)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.model_display_label)
        header_layout.addWidget(self.runtime_status_button)
        header_layout.addWidget(self.settings_button)
        layout.addLayout(header_layout)

        chip_row = QHBoxLayout()
        self.backend_status_label = QLabel()
        self.backend_status_label.setObjectName("settingLabel")
        self.prompt_status_label = QLabel()
        self.prompt_status_label.setObjectName("settingLabel")
        self.route_status_label = QLabel()
        self.route_status_label.setObjectName("settingLabel")
        self.context_status_label = QLabel()
        self.context_status_label.setObjectName("settingLabel")
        self.context_status_label.setWordWrap(True)
        chip_row.addWidget(self.backend_status_label)
        chip_row.addWidget(self.prompt_status_label)
        chip_row.addWidget(self.route_status_label)
        chip_row.addWidget(self.context_status_label, 1)
        layout.addLayout(chip_row)

        self.transcription_display = QTextEdit()
        self.transcription_display.setObjectName("transcriptionDisplay")
        self.transcription_display.setReadOnly(True)
        self.transcription_display.setPlaceholderText("Ready.")
        layout.addWidget(self.transcription_display, 1)

        self.hint_label = QLabel("")
        self.hint_label.setObjectName("hintLabel")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setFixedHeight(30)
        layout.addWidget(self.hint_label)

        self.visualizer = QProgressBar()
        self.visualizer.setObjectName("audioVisualizer")
        self.visualizer.setFixedHeight(4)
        self.visualizer.setTextVisible(False)
        self.visualizer.setRange(0, 1000)
        self.visualizer.setValue(0)
        layout.addWidget(self.visualizer)

        context_row = QHBoxLayout()
        self.context_drop_area = ContextDropArea()
        self.attach_context_button = QPushButton("Attach Files")
        self.attach_context_button.setCursor(Qt.PointingHandCursor)
        self.clear_context_button = QPushButton("Clear Context")
        self.clear_context_button.setCursor(Qt.PointingHandCursor)
        context_row.addWidget(self.context_drop_area, 1)
        side_buttons = QVBoxLayout()
        side_buttons.addWidget(self.attach_context_button)
        side_buttons.addWidget(self.clear_context_button)
        side_buttons.addStretch()
        context_row.addLayout(side_buttons)
        layout.addLayout(context_row)

        dock_container = QFrame()
        dock_container.setObjectName("controlDock")
        dock_container.setFixedHeight(86)
        dock_layout = QHBoxLayout(dock_container)
        dock_layout.setContentsMargins(20, 12, 20, 12)
        dock_layout.setSpacing(15)

        self.vad_toggle_button = QPushButton()
        self.vad_toggle_button.setObjectName("modeButton")
        self.vad_toggle_button.setCheckable(True)
        self.vad_toggle_button.setFixedSize(120, 45)
        self.vad_toggle_button.setCursor(Qt.PointingHandCursor)

        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("startButton")
        self.start_button.setProperty("state", "primary")
        self.start_button.setFixedSize(100, 45)
        self.start_button.setCursor(Qt.PointingHandCursor)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setProperty("state", "inactive")
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
        layout.setContentsMargins(24, 16, 24, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        self.back_button = QPushButton("← Back")
        self.back_button.setObjectName("backButton")
        self.back_button.setFixedSize(100, 40)
        self.back_button.setCursor(Qt.PointingHandCursor)
        settings_title = QLabel("Settings")
        settings_title.setObjectName("headerTitle")
        settings_title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.back_button)
        header_layout.addStretch()
        header_layout.addWidget(settings_title)
        header_layout.addStretch()
        header_layout.addSpacing(100)
        layout.addLayout(header_layout)

        hero_panel = QFrame()
        hero_panel.setObjectName("settingsHeroPanel")
        hero_layout = QVBoxLayout(hero_panel)
        hero_layout.setContentsMargins(20, 14, 20, 14)
        hero_layout.setSpacing(6)

        hero_eyebrow = QLabel("Guided setup")
        hero_eyebrow.setObjectName("heroEyebrow")
        hero_title = QLabel("Ready for local dictation" if self.whisper_only_runtime else "Choose the experience you want")
        hero_title.setObjectName("cardTitle")
        self.settings_summary_label = QLabel()
        self.settings_summary_label.setObjectName("heroSummary")
        self.settings_summary_label.setWordWrap(True)

        hero_layout.addWidget(hero_eyebrow)
        hero_layout.addWidget(hero_title)
        hero_layout.addWidget(self.settings_summary_label)
        layout.addWidget(hero_panel)

        scroll = QScrollArea()
        self.settings_scroll_area = scroll
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        scroll.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        self.backend_combo = QComboBox()
        self.backend_combo.addItem("Faster-Whisper", "faster-whisper")
        if not self.whisper_only_runtime:
            self.backend_combo.addItem("Gemma 4 (Transformers)", "gemma-4")
            self.backend_combo.addItem("Gemma GGUF (local server)", "gemma-gguf-server")

        self.language_combo = QComboBox()
        for display, code in [
            ("Auto Detect", None),
            ("English", "en"),
            ("Spanish", "es"),
            ("French", "fr"),
            ("German", "de"),
            ("Czech", "cs"),
            ("Italian", "it"),
            ("Portuguese", "pt"),
            ("Dutch", "nl"),
            ("Russian", "ru"),
            ("Chinese", "zh"),
            ("Japanese", "ja"),
        ]:
            self.language_combo.addItem(display, code)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["large-v3-turbo", "large-v3", "medium", "small", "base", "tiny"])

        self.gemma_model_combo = QComboBox()
        self.gemma_model_combo.addItem("Gemma 4 E2B", "google/gemma-4-E2B-it")
        self.gemma_model_combo.addItem("Gemma 4 E4B (unverified)", "google/gemma-4-E4B-it")
        self.gemma_model_combo.setItemData(
            0,
            "Verified locally for hybrid/context and native-audio smoke tests.",
            Qt.ToolTipRole,
        )
        self.gemma_model_combo.setItemData(
            1,
            "Heavier model. Local E4B weights and runtime behavior have not been verified yet.",
            Qt.ToolTipRole,
        )

        self.gguf_server_url_edit = QLineEdit()
        self.gguf_server_url_edit.setPlaceholderText("http://127.0.0.1:8080/v1")

        self.gguf_model_name_edit = QLineEdit()
        self.gguf_model_name_edit.setPlaceholderText("Optional: auto-select first server model if blank")

        self.quantization_combo = QComboBox()
        for label, value in [("4-bit", "4-bit"), ("8-bit", "8-bit"), ("16-bit", "16-bit")]:
            self.quantization_combo.addItem(label, value)

        self.prompt_mode_combo = QComboBox()
        self.prompt_mode_combo.addItem("Pure transcription", "pure")
        if not self.whisper_only_runtime:
            self.prompt_mode_combo.addItem("Context-enhanced", "context")
            self.prompt_mode_combo.addItem("Full reasoning", "reasoning")

        self.gemma_audio_mode_combo = QComboBox()
        self.gemma_audio_mode_combo.addItem("Hybrid (Whisper first, recommended)", "hybrid-whisper")
        self.gemma_audio_mode_combo.addItem("Native Gemma audio (experimental)", "native-audio")

        self.engine_info_label = QLabel()
        self.engine_info_label.setObjectName("helperText")
        self.engine_info_label.setWordWrap(True)

        self.silence_spinbox = QSpinBox()
        self.silence_spinbox.setRange(50, 3000)
        self.silence_spinbox.setSingleStep(50)

        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setRange(0.0, 0.1)
        self.delay_spinbox.setSingleStep(0.005)
        self.delay_spinbox.setDecimals(3)

        self.type_into_active_app_checkbox = QCheckBox("Type into active app")

        self.min_ptt_duration_spinbox = QSpinBox()
        self.min_ptt_duration_spinbox.setRange(0, 2000)
        self.min_ptt_duration_spinbox.setSingleStep(50)
        self.min_ptt_duration_spinbox.setSuffix(" ms")

        self.screen_context_checkbox = QCheckBox("Enable")

        self.screen_target_combo = QComboBox()
        self.screen_target_combo.addItem("Active window", "active-window")
        self.screen_target_combo.addItem("Full screen", "full-screen")

        self.webcam_checkbox = QCheckBox("Enable")

        self.capture_interval_spinbox = QSpinBox()
        self.capture_interval_spinbox.setRange(250, 5000)
        self.capture_interval_spinbox.setSingleStep(250)

        self.image_budget_combo = QComboBox()
        for value in [70, 140, 280]:
            self.image_budget_combo.addItem(str(value), value)

        self.video_frame_spinbox = QSpinBox()
        self.video_frame_spinbox.setRange(1, 12)

        self.model_path_edit = QLineEdit()
        self.model_path_browse_button = QPushButton("Browse")
        self.download_model_button = QPushButton("Download Now")
        model_path_controls = self._build_inline_widget(self.model_path_edit, self.model_path_browse_button, self.download_model_button)

        self.reasoning_preview_checkbox = QCheckBox("Ask before typing")
        self.preload_model_checkbox = QCheckBox("Preload on app launch")

        self.settings_wheel_guard = SettingsWheelGuard(scroll, self)
        for wheel_control in [
            self.backend_combo,
            self.language_combo,
            self.model_combo,
            self.gemma_model_combo,
            self.quantization_combo,
            self.prompt_mode_combo,
            self.gemma_audio_mode_combo,
            self.silence_spinbox,
            self.delay_spinbox,
            self.min_ptt_duration_spinbox,
            self.screen_target_combo,
            self.capture_interval_spinbox,
            self.image_budget_combo,
            self.video_frame_spinbox,
        ]:
            wheel_control.setFocusPolicy(Qt.ClickFocus)
            wheel_control.installEventFilter(self.settings_wheel_guard)

        self.ptt_key_display_label = QLabel()
        self.ptt_key_display_label.setObjectName("settingValue")
        self.set_ptt_key_button = QPushButton("Change")
        self.set_ptt_key_button.setCursor(Qt.PointingHandCursor)
        ptt_controls = self._build_inline_widget(self.ptt_key_display_label, self.set_ptt_key_button)

        self.filter_list = QListWidget()
        self.filter_list.setFixedHeight(110)
        self.filter_add_edit = QLineEdit()
        self.filter_add_edit.setPlaceholderText("Enter phrase...")
        self.filter_add_button = QPushButton("Add")
        self.filter_remove_button = QPushButton("Remove")
        filter_controls = self._build_inline_widget(self.filter_add_edit, self.filter_add_button, self.filter_remove_button)

        self.restore_defaults_button = QPushButton("Restore Defaults")
        self.restore_defaults_button.setObjectName("ghostButton")
        self.check_updates_button = QPushButton("Check for Updates")
        self.check_updates_button.setObjectName("ghostButton")

        if self.whisper_only_runtime:
            self._register_base_tooltip(self.backend_combo, "Faster-Whisper is the only runtime in this public recovery build.")
            self._register_base_tooltip(self.prompt_mode_combo, "Pure transcription is the only output style in this public recovery build.")
        else:
            self._register_base_tooltip(self.backend_combo, "Choose whether OmniDictate stays on fast Whisper only, uses the built-in Gemma runtime, or sends refinements to a local GGUF server.")
            self._register_base_tooltip(self.prompt_mode_combo, "Choose how much AI assistance OmniDictate applies after listening.")
        self._register_base_tooltip(
            self.model_combo,
            (
                "Select the Whisper model used for direct local transcription."
                if self.whisper_only_runtime
                else "Select the Whisper model used for pure transcription or the hybrid draft transcript."
            ),
        )
        self._register_base_tooltip(self.gemma_model_combo, "Choose the built-in Gemma model size. E2B has local smoke coverage; E4B is heavier and still needs live verification.")
        self._register_base_tooltip(self.gemma_audio_mode_combo, "Hybrid mode is the recommended path. Native audio is slower but lets Gemma listen directly.")
        self._register_base_tooltip(self.quantization_combo, "Lower-bit loading reduces VRAM pressure for the hybrid Gemma path when a CUDA GPU is available.")
        self._register_base_tooltip(self.language_combo, "Keep Auto Detect unless you almost always dictate in one language.")
        self._register_base_tooltip(self.gguf_server_url_edit, "Point this at your local OpenAI-compatible endpoint, for example LM Studio or llama-server.")
        self._register_base_tooltip(self.gguf_model_name_edit, "Optional. Leave blank to let OmniDictate use the first model reported by the server.")
        self._register_base_tooltip(self.screen_context_checkbox, "Allow OmniDictate to look at your screen when the selected output style supports context.")
        self._register_base_tooltip(self.screen_target_combo, "Choose whether screen context captures the active window only or the full desktop.")
        self._register_base_tooltip(self.webcam_checkbox, "Include a webcam frame alongside the transcript for context-aware turns.")
        self._register_base_tooltip(self.capture_interval_spinbox, "How often OmniDictate refreshes the current screen snapshot while context is enabled.")
        self._register_base_tooltip(self.image_budget_combo, "Higher image detail helps OCR and small UI text, but costs more latency and memory.")
        self._register_base_tooltip(self.video_frame_spinbox, "How many frames OmniDictate keeps when you attach a video file as context.")
        self._register_base_tooltip(self.model_path_edit, "Folder used for downloaded Gemma model files.")
        self._register_base_tooltip(self.model_path_browse_button, "Pick where downloaded Gemma model files should be stored.")
        self._register_base_tooltip(self.download_model_button, "Download the selected built-in Gemma model now so first use is faster.")
        self._register_base_tooltip(self.reasoning_preview_checkbox, "Ask for approval before OmniDictate types the output from full reasoning mode.")
        self._register_base_tooltip(self.preload_model_checkbox, "Warm the selected built-in Gemma model when the app starts.")
        self._register_base_tooltip(self.set_ptt_key_button, "Capture a new push-to-talk key.")
        self._register_base_tooltip(self.type_into_active_app_checkbox, "Turn this off when you only want the transcript inside OmniDictate.")
        self._register_base_tooltip(self.min_ptt_duration_spinbox, "Ignore very short PTT taps so accidental key brushes do not create junk transcripts.")
        self._register_base_tooltip(self.filter_add_edit, "Phrases added here are removed from the final output when they appear exactly.")
        self._register_base_tooltip(self.check_updates_button, "Check GitHub Releases and open the release page if a newer version is available.")
        self._register_base_tooltip(self.restore_defaults_button, "Restore all settings to the safe default setup.")

        experience_card, experience_body = self._create_settings_card(
            "Experience",
            "Start with how you want OmniDictate to listen and how much AI assistance you want afterward.",
        )
        self.experience_card = experience_card
        self.backend_row = self._create_settings_row(
            "Listening engine",
            (
                "Faster-Whisper is the local dictation runtime for this public recovery build."
                if self.whisper_only_runtime
                else "Pick the main runtime. Faster-Whisper is the safest baseline. Gemma options add cleanup and multimodal understanding."
            ),
            (
                "This build ships only the verified Faster-Whisper dictation path."
                if self.whisper_only_runtime
                else "Choose the speech-to-text experience. Faster-Whisper is the simplest and fastest. Gemma 4 runs in-process. GGUF uses your external local server."
            ),
            self.backend_combo,
        )
        experience_body.addWidget(self.backend_row)
        self.prompt_mode_row = self._create_settings_row(
            "Output style",
            (
                "Pure transcription returns the local speech transcript directly."
                if self.whisper_only_runtime
                else "Pure only transcribes. Context uses screen or image clues to fix ambiguity. Full reasoning can rephrase and suggest polished text."
            ),
            (
                "This build keeps dictation direct and local."
                if self.whisper_only_runtime
                else "Pure transcription is the direct transcript. Context-enhanced resolves visible terms, filenames, and on-screen labels. Full reasoning can rewrite into a more intentional final message."
            ),
            self.prompt_mode_combo,
        )
        experience_body.addWidget(self.prompt_mode_row)
        self.whisper_model_row = self._create_settings_row(
            "Whisper model",
            (
                "This controls the local Faster-Whisper transcription model."
                if self.whisper_only_runtime
                else "This controls the fast audio-first pass used by Faster-Whisper and the Gemma hybrid path."
            ),
            (
                "Smaller Whisper models respond faster. Larger ones can improve transcript accuracy."
                if self.whisper_only_runtime
                else "Smaller Whisper models respond faster. Larger ones can improve draft accuracy before Gemma refines the result."
            ),
            self.model_combo,
        )
        if not self.whisper_only_runtime:
            experience_body.addWidget(self.whisper_model_row)
        self.gemma_model_row = self._create_settings_row(
            "Built-in Gemma model",
            "Use E2B for the currently verified local Gemma path.",
            "E4B may improve correction and reasoning, but it has not passed local live-weight verification yet.",
            self.gemma_model_combo,
        )
        experience_body.addWidget(self.gemma_model_row)
        self.gemma_audio_row = self._create_settings_row(
            "Gemma listening mode",
            "Hybrid is the recommended path today. Native audio is slower and stays experimental.",
            "Hybrid means Whisper hears the audio first and Gemma refines the draft. Native audio sends audio directly into Gemma and works best only when you explicitly need that path.",
            self.gemma_audio_mode_combo,
        )
        experience_body.addWidget(self.gemma_audio_row)
        self.gemma_quantization_row = self._create_settings_row(
            "Gemma load profile",
            "Lower-bit loading saves VRAM on supported CUDA setups. Native audio currently stays on the safer dtype path.",
            "4-bit and 8-bit modes are for the hybrid Transformers Gemma path on CUDA hardware. Native audio falls back to the standard dtype path today.",
            self.quantization_combo,
        )
        experience_body.addWidget(self.gemma_quantization_row)
        self.gguf_server_row = self._create_settings_row(
            "GGUF server address",
            "Only used for the external GGUF path.",
            "Enter the local OpenAI-compatible server URL used by llama-server, LM Studio, or a similar tool.",
            self.gguf_server_url_edit,
        )
        experience_body.addWidget(self.gguf_server_row)
        self.gguf_model_row = self._create_settings_row(
            "GGUF model name",
            "Optional override for the exact model hosted by your local server.",
            "Leave this blank to let OmniDictate use the first model reported by the server.",
            self.gguf_model_name_edit,
        )
        experience_body.addWidget(self.gguf_model_row)
        experience_body.addWidget(self.engine_info_label)
        if not self.whisper_only_runtime:
            content_layout.addWidget(experience_card)

        speech_card, speech_body = self._create_settings_card(
            "Speech And Typing",
            "These controls shape how OmniDictate listens for speech and how quickly it types into the target app.",
        )
        if self.whisper_only_runtime:
            speech_body.addWidget(self.whisper_model_row)
        speech_body.addWidget(self._create_settings_row(
            "Preferred language",
            "Leave Auto Detect on unless you almost always dictate in one language.",
            "Choosing a fixed language can reduce mistakes when you dictate in the same language all day.",
            self.language_combo,
        ))
        speech_body.addWidget(self._create_settings_row(
            "Silence sensitivity",
            "Lower values make voice detection trigger more easily. Higher values make it wait for louder speech.",
            "This affects VAD mode only. If OmniDictate starts too early, raise the number. If it misses quiet speech, lower it.",
            self.silence_spinbox,
        ))
        speech_body.addWidget(self._create_settings_row(
            "Typing pace",
            "Slow this down if the target app drops letters or behaves badly with rapid keystrokes.",
            "Most apps work with the default. Older apps, remote desktops, and web editors may need a slightly slower pace.",
            self.delay_spinbox,
        ))
        speech_body.addWidget(self._create_settings_row(
            "Typing output",
            "Turn typing off when you only want to collect text inside OmniDictate.",
            "When this is off, OmniDictate still transcribes and shows text in the app, but it will not type into other windows.",
            self.type_into_active_app_checkbox,
        ))
        speech_body.addWidget(self._create_settings_row(
            "Minimum PTT hold",
            "Ignore accidental push-to-talk taps shorter than this duration.",
            "A small threshold helps prevent very short audio snippets from producing repeated filler phrases.",
            self.min_ptt_duration_spinbox,
        ))
        self.reasoning_preview_row = self._create_settings_row(
            "Review before typing",
            "Only relevant in Full reasoning mode. OmniDictate can ask for approval before it types the rewritten result.",
            "Turn this on when you want a safety check for reasoning mode before text is inserted into the active app.",
            self.reasoning_preview_checkbox,
        )
        speech_body.addWidget(self.reasoning_preview_row)
        content_layout.addWidget(speech_card)

        context_card, context_body = self._create_settings_card(
            "Visual Context",
            "Use screen, camera, image, or video cues to resolve ambiguity when the chosen engine and output style support it.",
        )
        self.context_settings_card = context_card
        context_body.addWidget(self._create_settings_row(
            "Use current screen",
            "Allow OmniDictate to capture the visible app when context-aware output is enabled.",
            "Useful for filenames, UI labels, spreadsheet headers, chart titles, and on-screen code symbols.",
            self.screen_context_checkbox,
            self.screen_target_combo,
        ))
        context_body.addWidget(self._create_settings_row(
            "Use webcam",
            "Include a webcam frame for context-aware turns.",
            "Useful when the content you are speaking about is in front of the camera rather than on the screen.",
            self.webcam_checkbox,
        ))
        context_body.addWidget(self._create_settings_row(
            "Screen refresh rate",
            "How often OmniDictate refreshes the captured screen snapshot while context is enabled.",
            "Lower values capture changes sooner but cost more work. Higher values are lighter but can lag behind fast screen changes.",
            self.capture_interval_spinbox,
        ))
        context_body.addWidget(self._create_settings_row(
            "Image detail",
            "Controls how much detail Gemma sees when images or screenshots are attached.",
            "Use higher detail for OCR, diagrams, and tiny UI text. Use lower detail for faster turns.",
            self.image_budget_combo,
        ))
        context_body.addWidget(self._create_settings_row(
            "Video frame count",
            "Controls how many frames are sampled from attached videos.",
            "More frames capture more of the clip but raise latency and memory use.",
            self.video_frame_spinbox,
        ))
        content_layout.addWidget(context_card)

        model_card, model_body = self._create_settings_card(
            "Models And Downloads",
            "Choose where built-in Gemma files live and whether they should be warmed on startup.",
        )
        self.model_settings_card = model_card
        model_body.addWidget(self._create_settings_row(
            "Model folder",
            "Built-in Gemma downloads are stored here.",
            "Use Browse to choose a location with enough free space. Download Now only applies to the built-in Transformers Gemma path.",
            model_path_controls,
        ))
        model_body.addWidget(self._create_settings_row(
            "Startup warm-up",
            "Load the selected built-in Gemma model when the app opens.",
            "This makes first use faster but increases startup cost and memory use.",
            self.preload_model_checkbox,
        ))
        content_layout.addWidget(model_card)

        if self.whisper_only_runtime:
            for widget in [
                self.backend_row,
                self.prompt_mode_row,
                self.gemma_model_row,
                self.gemma_audio_row,
                self.gemma_quantization_row,
                self.gguf_server_row,
                self.gguf_model_row,
                self.reasoning_preview_row,
                self.context_settings_card,
                self.model_settings_card,
            ]:
                widget.hide()

        hotkey_card, hotkey_body = self._create_settings_card(
            "Hotkeys",
            "Use one key to push-to-talk and quick shortcuts to change writing style while you work.",
        )
        hotkey_body.addWidget(self._create_settings_row(
            "Push-to-talk key",
            "Hold this key to dictate when PTT mode is active.",
            "Choose a key that does not conflict with your normal workflow. Right Shift is the default.",
            ptt_controls,
        ))
        mode_shortcuts = QLabel(
            "Quick style key: Ctrl+1 returns to Pure transcription."
            if self.whisper_only_runtime
            else "Quick style keys: Ctrl+1 for Pure transcription, Ctrl+2 for Context-enhanced, Ctrl+3 for Full reasoning."
        )
        mode_shortcuts.setObjectName("helperText")
        mode_shortcuts.setWordWrap(True)
        hotkey_body.addWidget(mode_shortcuts)
        content_layout.addWidget(hotkey_card)

        advanced_card, advanced_body = self._create_settings_card(
            "Advanced",
            "Use these controls when you need to filter recurring junk phrases or restore a known-good configuration.",
        )
        advanced_body.addWidget(self._create_settings_row(
            "Blocked phrases",
            "Any exact phrase listed here is removed from the final output.",
            "This is useful for repeated hallucinated sign-offs or phrases that appear in a specific workflow.",
            self.filter_list,
        ))
        advanced_body.addWidget(self._create_settings_row(
            "Manage blocked phrases",
            "Add new exact matches or remove selected ones.",
            "The filter removes exact phrases after transcription. It does not rewrite similar text.",
            filter_controls,
        ))
        advanced_body.addWidget(self._create_settings_row(
            "Updates",
            "Check whether a newer OmniDictate release is available.",
            "This only checks when you click the button. If a newer version exists, OmniDictate can open the GitHub Releases page.",
            self.check_updates_button,
        ))
        advanced_body.addWidget(self.restore_defaults_button)
        content_layout.addWidget(advanced_card)

        content_layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addWidget(scroll)

    def apply_settings_to_widgets(self):
        previous_guard = self._suspend_settings_events
        self._suspend_settings_events = True
        try:
            self.vad_toggle_button.setChecked(self.app_settings.vad_enabled)

            backend_index = self.backend_combo.findData(self.app_settings.backend)
            if backend_index != -1:
                self.backend_combo.setCurrentIndex(backend_index)

            gemma_index = self.gemma_model_combo.findData(self.app_settings.gemma_model)
            if gemma_index != -1:
                self.gemma_model_combo.setCurrentIndex(gemma_index)

            self.gguf_server_url_edit.setText(self.app_settings.gguf_server_url)
            self.gguf_model_name_edit.setText(self.app_settings.gguf_model_name)

            quantization_index = self.quantization_combo.findData(self.app_settings.gemma_quantization)
            if quantization_index != -1:
                self.quantization_combo.setCurrentIndex(quantization_index)

            audio_mode_index = self.gemma_audio_mode_combo.findData(self.app_settings.gemma_audio_input_mode)
            if audio_mode_index != -1:
                self.gemma_audio_mode_combo.setCurrentIndex(audio_mode_index)

            self._sync_whisper_model_combo()

            language_index = self.language_combo.findData(self.app_settings.language)
            if language_index != -1:
                self.language_combo.setCurrentIndex(language_index)
            else:
                self.language_combo.setCurrentIndex(0)

            prompt_index = self.prompt_mode_combo.findData(self.app_settings.prompt_mode)
            if prompt_index != -1:
                self.prompt_mode_combo.setCurrentIndex(prompt_index)

            self.silence_spinbox.setValue(self.app_settings.silence_threshold)
            self.delay_spinbox.setValue(self.app_settings.char_delay)
            self.type_into_active_app_checkbox.setChecked(self.app_settings.type_into_active_app)
            self.min_ptt_duration_spinbox.setValue(self.app_settings.min_ptt_duration_ms)
            self.screen_context_checkbox.setChecked(self.app_settings.screen_context_enabled)
            target_index = self.screen_target_combo.findData(self.app_settings.screen_target)
            if target_index != -1:
                self.screen_target_combo.setCurrentIndex(target_index)
            self.webcam_checkbox.setChecked(self.app_settings.webcam_enabled)
            self.capture_interval_spinbox.setValue(self.app_settings.visual_capture_interval_ms)
            budget_index = self.image_budget_combo.findData(self.app_settings.image_token_budget)
            if budget_index != -1:
                self.image_budget_combo.setCurrentIndex(budget_index)
            self.video_frame_spinbox.setValue(self.app_settings.video_frame_limit)
            self.model_path_edit.setText(self.app_settings.model_storage_path)
            self.preload_model_checkbox.setChecked(self.app_settings.preload_model_on_launch)
            self.reasoning_preview_checkbox.setChecked(self.app_settings.reasoning_requires_preview)
            self.ptt_key_display_label.setText(self.format_key_name(self.app_settings.ptt_key_str))

            self.filter_list.clear()
            for phrase in self.app_settings.filter_words:
                self.filter_list.addItem(QListWidgetItem(phrase))
        finally:
            self._suspend_settings_events = previous_guard

        self.on_backend_changed()
        self.update_context_summary()

    def load_settings(self):
        self.app_settings = load_app_settings(self.settings)
        self.visual_context_manager.update_settings(self.app_settings)

    def save_settings(self):
        if self.setting_key_for or self._suspend_settings_events:
            return

        uses_hybrid_audio = self._uses_gemma_hybrid_audio()

        self.app_settings.backend = self.backend_combo.currentData()
        if uses_hybrid_audio:
            self.app_settings.gemma_hybrid_whisper_model = self.model_combo.currentText()
        else:
            self.app_settings.whisper_model = self.model_combo.currentText()
        self.app_settings.gemma_model = self.gemma_model_combo.currentData()
        self.app_settings.gguf_server_url = self.gguf_server_url_edit.text().strip()
        self.app_settings.gguf_model_name = self.gguf_model_name_edit.text().strip()
        self.app_settings.gemma_quantization = self.quantization_combo.currentData()
        self.app_settings.gemma_audio_input_mode = self.gemma_audio_mode_combo.currentData()
        self.app_settings.language = self.language_combo.currentData()
        self.app_settings.prompt_mode = self.prompt_mode_combo.currentData()
        self.app_settings.vad_enabled = self.vad_toggle_button.isChecked()
        self.app_settings.silence_threshold = self.silence_spinbox.value()
        self.app_settings.char_delay = self.delay_spinbox.value()
        self.app_settings.type_into_active_app = self.type_into_active_app_checkbox.isChecked()
        self.app_settings.min_ptt_duration_ms = self.min_ptt_duration_spinbox.value()
        self.app_settings.screen_context_enabled = self.screen_context_checkbox.isChecked()
        self.app_settings.screen_target = self.screen_target_combo.currentData()
        self.app_settings.webcam_enabled = self.webcam_checkbox.isChecked()
        self.app_settings.visual_capture_interval_ms = self.capture_interval_spinbox.value()
        self.app_settings.image_token_budget = self.image_budget_combo.currentData()
        self.app_settings.video_frame_limit = self.video_frame_spinbox.value()
        self.app_settings.model_storage_path = self.model_path_edit.text().strip()
        self.app_settings.preload_model_on_launch = self.preload_model_checkbox.isChecked()
        self.app_settings.reasoning_requires_preview = self.reasoning_preview_checkbox.isChecked()
        self.app_settings.filter_words = [self.filter_list.item(index).text() for index in range(self.filter_list.count())]
        sanitize_app_settings_for_runtime(self.app_settings)
        self.app_settings.write_to_qsettings(self.settings)
        self.visual_context_manager.update_settings(self.app_settings)
        self.update_vad_button_style()
        self.update_engine_info_label()
        self._update_settings_summary()
        self.update_status_strip()
        if not self.is_dictation_running and self._allow_global_hotkeys:
            self.restart_hotkey_listener()

    @Slot()
    def restore_default_settings(self):
        self.app_settings = AppSettings()
        sanitize_app_settings_for_runtime(self.app_settings)
        self.app_settings.write_to_qsettings(self.settings)
        self.visual_context_manager.update_settings(self.app_settings)
        self.apply_settings_to_widgets()
        self.update_vad_button_style()
        self.update_status_strip()
        QMessageBox.information(self, "Settings Restored", "Default settings restored and saved.")

    def on_backend_changed(self, *_args):
        backend = self.backend_combo.currentData()
        using_transformers_gemma = backend == "gemma-4"
        using_gguf_server = backend == "gemma-gguf-server"
        uses_hybrid_audio = using_gguf_server or (using_transformers_gemma and self.gemma_audio_mode_combo.currentData() == "hybrid-whisper")
        prompt_mode = self.prompt_mode_combo.currentData()
        visual_features_available = self._supports_visual_features(backend, prompt_mode)
        running_lock_reason = None if self._settings_controls_enabled else "Stop dictation to change this setting."
        visual_reason = "Visual context is available only when a Gemma runtime uses Context-enhanced or Full reasoning output."
        screen_target_reason = "Turn on screen context first, then choose what area OmniDictate should capture."
        quantization_reason = "4-bit and 8-bit loading currently work only for the hybrid Gemma path on a CUDA GPU."

        previous_guard = self._suspend_settings_events
        self._suspend_settings_events = True
        try:
            self._set_combo_item_enabled(self.prompt_mode_combo, "pure", True, "Pure transcription works on every runtime.")
            self._set_combo_item_enabled(
                self.prompt_mode_combo,
                "context",
                backend != "faster-whisper",
                "Context-enhanced mode requires a Gemma runtime because Faster-Whisper does not read visual context.",
            )
            self._set_combo_item_enabled(
                self.prompt_mode_combo,
                "reasoning",
                backend != "faster-whisper",
                "Full reasoning requires a Gemma runtime because Faster-Whisper only returns a transcript.",
            )
            self._ensure_enabled_combo_selection(self.prompt_mode_combo)
            prompt_mode = self.prompt_mode_combo.currentData()
            visual_features_available = self._supports_visual_features(backend, prompt_mode)

            quantized_supported = (
                using_transformers_gemma
                and self.gemma_audio_mode_combo.currentData() == "hybrid-whisper"
                and torch_cuda_is_available()
            )
            self._set_combo_item_enabled(self.quantization_combo, "4-bit", quantized_supported, quantization_reason)
            self._set_combo_item_enabled(self.quantization_combo, "8-bit", quantized_supported, quantization_reason)
            self._set_combo_item_enabled(
                self.quantization_combo,
                "16-bit",
                using_transformers_gemma,
                "Standard dtype loading for the built-in Gemma runtime.",
            )
            self._ensure_enabled_combo_selection(self.quantization_combo)

            self._sync_whisper_model_combo()
        finally:
            self._suspend_settings_events = previous_guard

        self._set_control_enabled(self.backend_combo, self._settings_controls_enabled, running_lock_reason)
        self._set_control_enabled(
            self.prompt_mode_combo,
            self._settings_controls_enabled,
            running_lock_reason or "Output style selection is available in settings.",
        )
        self._set_control_enabled(
            self.model_combo,
            self._settings_controls_enabled and (backend == "faster-whisper" or uses_hybrid_audio),
            running_lock_reason or "Whisper model selection only matters for Faster-Whisper and the hybrid Gemma paths.",
        )
        self._set_control_enabled(
            self.gemma_model_combo,
            self._settings_controls_enabled and using_transformers_gemma,
            running_lock_reason or "Built-in Gemma model selection is only used by the Transformers Gemma runtime.",
        )
        self._set_control_enabled(
            self.gemma_audio_mode_combo,
            self._settings_controls_enabled and using_transformers_gemma,
            running_lock_reason or "Gemma listening mode is only used by the built-in Transformers Gemma runtime.",
        )
        self._set_control_enabled(
            self.quantization_combo,
            self._settings_controls_enabled and using_transformers_gemma,
            running_lock_reason or "Gemma load profile is only used by the built-in Transformers Gemma runtime.",
        )
        self._set_control_enabled(
            self.gguf_server_url_edit,
            self._settings_controls_enabled and using_gguf_server,
            running_lock_reason or "This field is only used by the external GGUF server runtime.",
        )
        self._set_control_enabled(
            self.gguf_model_name_edit,
            self._settings_controls_enabled and using_gguf_server,
            running_lock_reason or "This field is only used by the external GGUF server runtime.",
        )
        self._set_control_enabled(self.language_combo, self._settings_controls_enabled, running_lock_reason)
        self._set_control_enabled(self.silence_spinbox, self._settings_controls_enabled, running_lock_reason)
        self._set_control_enabled(self.delay_spinbox, self._settings_controls_enabled, running_lock_reason)
        self._set_control_enabled(self.type_into_active_app_checkbox, self._settings_controls_enabled, running_lock_reason)
        self._set_control_enabled(self.min_ptt_duration_spinbox, self._settings_controls_enabled, running_lock_reason)
        self._set_control_enabled(
            self.screen_context_checkbox,
            self._settings_controls_enabled and visual_features_available,
            running_lock_reason or visual_reason,
        )
        self._set_control_enabled(
            self.screen_target_combo,
            self._settings_controls_enabled and visual_features_available and self.screen_context_checkbox.isChecked(),
            running_lock_reason or (screen_target_reason if visual_features_available else visual_reason),
        )
        self._set_control_enabled(
            self.webcam_checkbox,
            self._settings_controls_enabled and visual_features_available,
            running_lock_reason or visual_reason,
        )
        self._set_control_enabled(
            self.capture_interval_spinbox,
            self._settings_controls_enabled and visual_features_available,
            running_lock_reason or visual_reason,
        )
        self._set_control_enabled(
            self.image_budget_combo,
            self._settings_controls_enabled and visual_features_available,
            running_lock_reason or visual_reason,
        )
        self._set_control_enabled(
            self.video_frame_spinbox,
            self._settings_controls_enabled and visual_features_available,
            running_lock_reason or visual_reason,
        )
        self._set_control_enabled(
            self.model_path_edit,
            self._settings_controls_enabled and using_transformers_gemma,
            running_lock_reason or "The model folder is only used by the built-in Transformers Gemma runtime.",
        )
        self._set_control_enabled(
            self.model_path_browse_button,
            self._settings_controls_enabled and using_transformers_gemma,
            running_lock_reason or "The model folder is only used by the built-in Transformers Gemma runtime.",
        )
        self._set_control_enabled(
            self.download_model_button,
            self._settings_controls_enabled and using_transformers_gemma,
            running_lock_reason or "Download Now only applies to the built-in Transformers Gemma runtime.",
        )
        self._set_control_enabled(
            self.preload_model_checkbox,
            self._settings_controls_enabled and using_transformers_gemma,
            running_lock_reason or "Warm-up at launch only applies to the built-in Transformers Gemma runtime.",
        )
        self._set_control_enabled(
            self.reasoning_preview_checkbox,
            self._settings_controls_enabled and backend != "faster-whisper" and prompt_mode == "reasoning",
            running_lock_reason or "Preview before typing is only used in Full reasoning mode on a Gemma runtime.",
        )

        advanced_enabled = self._settings_controls_enabled
        self._set_control_enabled(self.filter_list, advanced_enabled, running_lock_reason)
        self._set_control_enabled(self.filter_add_edit, advanced_enabled, running_lock_reason)
        self._set_control_enabled(self.filter_add_button, advanced_enabled, running_lock_reason)
        self._set_control_enabled(self.filter_remove_button, advanced_enabled, running_lock_reason)
        self._set_control_enabled(self.set_ptt_key_button, advanced_enabled, running_lock_reason)
        self._set_control_enabled(self.check_updates_button, advanced_enabled, running_lock_reason)
        self._set_control_enabled(self.restore_defaults_button, advanced_enabled, running_lock_reason)

        main_context_reason = "Attachments are not available in the public Whisper-only build." if self.whisper_only_runtime else "Attachments and saved visual context are only used in Context-enhanced or Full reasoning mode on a Gemma runtime."
        self._set_control_enabled(self.attach_context_button, visual_features_available, main_context_reason)
        self._set_control_enabled(self.clear_context_button, visual_features_available, main_context_reason)
        self._set_control_enabled(self.context_drop_area, visual_features_available, main_context_reason)
        for widget in [self.attach_context_button, self.clear_context_button, self.context_drop_area, self.context_status_label]:
            widget.setVisible(not self.whisper_only_runtime)

        self.update_engine_info_label()
        self._update_settings_summary()
        self.update_status_strip()

    def update_engine_info_label(self):
        if not hasattr(self, "engine_info_label"):
            return

        if self.whisper_only_runtime:
            model_name = self.model_combo.currentText() or "Whisper"
            text = f"{model_name} uses the local Faster-Whisper path for direct transcription."
        elif self.backend_combo.currentData() == "gemma-4":
            model_name = self.gemma_model_combo.currentText() or "Gemma 4"
            quantization = self.quantization_combo.currentText() or "Auto"
            audio_mode = self.gemma_audio_mode_combo.currentData()
            if audio_mode == "hybrid-whisper":
                whisper_model = self.model_combo.currentText() or self.app_settings.gemma_hybrid_whisper_model
                if self.prompt_mode_combo.currentData() == "pure":
                    text = (
                        f"{model_name} is configured for hybrid use with Whisper '{whisper_model}', but Pure transcription keeps the fast Whisper-only path until you switch to a context-aware style. "
                        f"When you do switch, {quantization} loading remains available on supported hardware because native Gemma audio is not used."
                    )
                else:
                    text = (
                        f"{model_name} is in the recommended hybrid mode. Faster-Whisper '{whisper_model}' drafts the transcript first, then Gemma refines names, numbers, and optional visual context with lower latency than native audio. "
                        f"Current load profile: {quantization}."
                    )
            else:
                text = (
                    f"{model_name} uses the direct native Gemma audio path with optional screen, image, video, and webcam context. First use may download model files into the selected folder. "
                    f"Selected load profile: {quantization}. In practice the app currently falls back to the standard dtype path here because quantized native-audio generation is still unstable, so treat this as the experimental deep-context mode rather than the daily driver."
                )
        elif self.backend_combo.currentData() == "gemma-gguf-server":
            model_name = self.gguf_model_name_edit.text().strip() or "server auto-select"
            whisper_model = self.model_combo.currentText() or self.app_settings.gemma_hybrid_whisper_model
            server_url = self.gguf_server_url_edit.text().strip() or self.app_settings.gguf_server_url
            text = (
                f"GGUF hybrid mode keeps audio local with Faster-Whisper '{whisper_model}', then sends the transcript plus optional images to your local OpenAI-compatible server at {server_url}. "
                f"Use this when you want llama.cpp or LM Studio to host a multimodal Gemma GGUF model such as '{model_name}'. Raw audio is never sent to the server by OmniDictate."
            )
        else:
            model_name = self.model_combo.currentText() or "Whisper"
            text = (
                f"{model_name} stays on the low-friction Faster-Whisper path. It is the safest choice when you want fast local dictation, but it does not use screen, image, webcam, or reasoning features."
            )

        self.engine_info_label.setText(text)

    def browse_model_path(self):
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Model Storage Directory", self.model_path_edit.text() or os.getcwd())
        if selected_dir:
            self.model_path_edit.setText(selected_dir)
            self.save_settings()

    def download_selected_model(self):
        self.save_settings()
        if self.backend_combo.currentData() == "gemma-gguf-server":
            QMessageBox.information(
                self,
                "External Server Required",
                "The GGUF backend expects llama.cpp, LM Studio, or another OpenAI-compatible local server to be running already with a multimodal model loaded. OmniDictate does not download GGUF or mmproj files for that backend.",
            )
            return
        if self.backend_combo.currentData() != "gemma-4":
            QMessageBox.information(self, "Download Not Required", "Whisper models are loaded on demand through Faster-Whisper. Pre-download is only implemented for the Transformers Gemma backend.")
            return
        if self.download_thread and self.download_thread.isRunning():
            QMessageBox.information(self, "Download In Progress", "A model download is already running.")
            return
        try:
            from model_downloader import ModelDownloadWorker
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Download Unavailable",
                f"Model downloads are unavailable in this build:\n{exc}",
            )
            return

        self.download_progress_dialog = QProgressDialog("Preparing model download...", "Cancel", 0, 100, self)
        self.download_progress_dialog.setWindowTitle("Download Gemma Model")
        self.download_progress_dialog.setWindowModality(Qt.WindowModal)
        self.download_progress_dialog.setMinimumDuration(0)
        self.download_progress_dialog.setValue(0)

        self.download_thread = QThread(self)
        self.download_worker = ModelDownloadWorker(
            model_id=self.gemma_model_combo.currentData(),
            model_storage_path=self.model_path_edit.text().strip(),
        )
        self.download_worker.moveToThread(self.download_thread)
        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.progress_updated.connect(self.handle_model_download_progress)
        self.download_worker.download_completed.connect(self.handle_model_download_success)
        self.download_worker.download_failed.connect(self.handle_model_download_failure)
        self.download_progress_dialog.canceled.connect(self.download_worker.request_cancel)
        self.download_worker.download_completed.connect(self.download_thread.quit)
        self.download_worker.download_failed.connect(self.download_thread.quit)
        self.download_thread.finished.connect(self.download_worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        self.download_thread.finished.connect(self.cleanup_download_worker)
        self.download_thread.start()
        self.download_progress_dialog.show()

    @Slot(int, str)
    def handle_model_download_progress(self, percent, message):
        if self.download_progress_dialog:
            self.download_progress_dialog.setLabelText(message)
            self.download_progress_dialog.setValue(percent)

    @Slot(str)
    def handle_model_download_success(self, downloaded_path):
        if self.download_progress_dialog:
            self.download_progress_dialog.setValue(100)
            self.download_progress_dialog.close()
            self.download_progress_dialog = None
        QMessageBox.information(self, "Download Complete", f"Gemma model files are ready at:\n{downloaded_path}")

    @Slot(str)
    def handle_model_download_failure(self, error_message):
        if self.download_progress_dialog:
            self.download_progress_dialog.close()
            self.download_progress_dialog = None
        QMessageBox.warning(self, "Download Failed", f"Could not complete the model download:\n{error_message}")

    @Slot()
    def cleanup_download_worker(self):
        self.download_worker = None
        self.download_thread = None

    def start_model_preload(self):
        if self.is_dictation_running:
            return
        if self.preload_thread and self.preload_thread.isRunning():
            return

        preload_settings = AppSettings(**self.app_settings.to_dict())
        if preload_settings.backend != "gemma-4":
            self.statusBar.showMessage("Preload skipped: launch warm-up only applies to built-in Gemma.", 3000)
            return

        self.preload_thread = QThread(self)
        self.preload_worker = ModelPreloadWorker(preload_settings)
        self.preload_worker.moveToThread(self.preload_thread)
        self.preload_thread.started.connect(self.preload_worker.run)
        self.preload_worker.status_updated.connect(self.update_status)
        self.preload_worker.preload_completed.connect(self.handle_model_preload_success)
        self.preload_worker.preload_failed.connect(self.handle_model_preload_failure)
        self.preload_worker.preload_completed.connect(self.preload_thread.quit)
        self.preload_worker.preload_failed.connect(self.preload_thread.quit)
        self.preload_thread.finished.connect(self.preload_worker.deleteLater)
        self.preload_thread.finished.connect(self.preload_thread.deleteLater)
        self.preload_thread.finished.connect(self.cleanup_preload_worker)
        self.preload_thread.start()

    @Slot(str)
    def handle_model_preload_success(self, status_message):
        self.statusBar.showMessage(f"Preload complete: {status_message}", 3000)

    @Slot(str)
    def handle_model_preload_failure(self, error_message):
        self.statusBar.showMessage(f"Preload skipped: {error_message}", 5000)

    @Slot()
    def cleanup_preload_worker(self):
        self.preload_worker = None
        self.preload_thread = None

    def check_for_updates(self):
        if self.update_thread and self.update_thread.isRunning():
            QMessageBox.information(self, "Update Check", "An update check is already running.")
            return

        self.check_updates_button.setEnabled(False)
        self.statusBar.show()
        self.statusBar.showMessage("Checking for updates...")
        self.update_thread = QThread(self)
        self.update_worker = UpdateCheckWorker()
        self.update_worker.moveToThread(self.update_thread)
        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.update_available.connect(self.handle_update_available)
        self.update_worker.no_update_available.connect(self.handle_no_update_available)
        self.update_worker.update_check_failed.connect(self.handle_update_check_failed)
        self.update_worker.update_available.connect(self.update_thread.quit)
        self.update_worker.no_update_available.connect(self.update_thread.quit)
        self.update_worker.update_check_failed.connect(self.update_thread.quit)
        self.update_thread.finished.connect(self.update_worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)
        self.update_thread.finished.connect(self.cleanup_update_worker)
        self.update_thread.start()

    @Slot(str, str)
    def handle_update_available(self, latest_version: str, release_url: str):
        self.statusBar.showMessage(f"Update available: {latest_version}", 5000)
        message = (
            f"OmniDictate {latest_version} is available.\n\n"
            f"You are running {APP_VERSION}.\n\n"
            "Open the GitHub Releases page now?"
        )
        open_button = QMessageBox.question(
            self,
            "Update Available",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if open_button == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl(release_url or GITHUB_RELEASES_URL))

    @Slot(str)
    def handle_no_update_available(self, latest_version: str):
        self.statusBar.showMessage("OmniDictate is up to date.", 5000)
        QMessageBox.information(
            self,
            "No Update Available",
            f"You are running OmniDictate {APP_VERSION}.\nLatest release: {latest_version}.",
        )

    @Slot(str)
    def handle_update_check_failed(self, error_message: str):
        self.statusBar.showMessage("Could not check for updates.", 5000)
        QMessageBox.warning(
            self,
            "Update Check Failed",
            f"Could not check GitHub Releases.\n\n{error_message}",
        )

    @Slot(object)
    def handle_runtime_update(self, diagnostics):
        if isinstance(diagnostics, RuntimeDiagnostics):
            self.runtime_diagnostics = diagnostics
        else:
            self.runtime_diagnostics = None
        self.update_runtime_badge()
        if self.runtime_diagnostics and self.runtime_diagnostics.status == "cpu-mode":
            self.statusBar.show()
            self.statusBar.showMessage("CPU mode: transcription may be slower. Click Runtime for setup help.", 8000)
        elif self.runtime_diagnostics and self.runtime_diagnostics.status == "error":
            self.statusBar.show()
            self.statusBar.showMessage("Runtime check needs attention. Click Runtime for setup help.", 8000)

    def _runtime_badge_parts(self) -> tuple[str, str, str]:
        diagnostics = self.runtime_diagnostics
        if diagnostics is None:
            return "Runtime: Not checked", "unknown", "Start dictation to check whether GPU acceleration is available."
        if diagnostics.status == "gpu-ready":
            return "Runtime: GPU ready", "gpu", diagnostics.summary
        if diagnostics.status == "gpu-compat":
            return "Runtime: GPU compatibility", "compat", diagnostics.summary
        if diagnostics.status == "cpu-mode":
            return "Runtime: CPU mode", "cpu", diagnostics.summary
        if diagnostics.status == "error":
            return "Runtime: Check needed", "error", diagnostics.summary
        return "Runtime: Checked", "unknown", diagnostics.summary

    def update_runtime_badge(self):
        if not hasattr(self, "runtime_status_button"):
            return
        text, state, tooltip = self._runtime_badge_parts()
        self.runtime_status_button.setText(text)
        self.runtime_status_button.setToolTip(tooltip)
        if self.runtime_status_button.property("runtimeState") != state:
            self.runtime_status_button.setProperty("runtimeState", state)
            self.runtime_status_button.style().unpolish(self.runtime_status_button)
            self.runtime_status_button.style().polish(self.runtime_status_button)
            self.runtime_status_button.update()

    def show_runtime_diagnostics(self):
        diagnostics = self.runtime_diagnostics
        if diagnostics is None:
            diagnostics = RuntimeDiagnostics(
                status="not-checked",
                headline="Runtime not checked yet",
                summary=(
                    "OmniDictate checks GPU acceleration when the speech model starts. "
                    "Start dictation once to see whether this PC is using GPU or CPU mode."
                ),
                next_steps=[
                    "Click Start on the main screen.",
                    "Wait for the model load message.",
                    "Open this Performance Check again if it shows CPU mode or a runtime error.",
                ],
                technical_details=[
                    f"Selected model: {self.app_settings.model_display_name}",
                    "No model load has been checked in this app session.",
                ],
            )
        RuntimeDiagnosticsDialog(diagnostics, self).exec()

    @Slot()
    def cleanup_update_worker(self):
        self.update_worker = None
        self.update_thread = None
        if hasattr(self, "check_updates_button"):
            self.check_updates_button.setEnabled(self._settings_controls_enabled)

    def add_filter_word(self):
        word = self.filter_add_edit.text().strip()
        if word and not self.filter_list.findItems(word, Qt.MatchFlag.MatchExactly):
            self.filter_list.addItem(QListWidgetItem(word))
            self.filter_add_edit.clear()
            self.save_settings()

    def remove_filter_word(self):
        items = self.filter_list.selectedItems()
        if not items:
            return
        for item in items:
            self.filter_list.takeItem(self.filter_list.row(item))
        self.save_settings()

    def prepare_to_set_key(self, key_type):
        if self.is_dictation_running:
            QMessageBox.warning(self, "Warning", "Stop dictation first.")
            return
        if self.setting_key_for:
            QMessageBox.warning(self, "Warning", f"Already waiting for {self.setting_key_for} key.")
            return

        self.setting_key_for = key_type
        self.original_button_text = self.set_ptt_key_button.text()
        self.set_ptt_key_button.setText("Press Key...")
        self.set_other_controls_enabled(False)
        self.stop_hotkey_listener()

        self.capture_hotkey_worker = HotkeyWorker(capture_mode=True, parent=self)
        self.capture_hotkey_worker.key_captured_signal.connect(self.handle_key_capture)
        self.capture_hotkey_worker.error_signal.connect(self.handle_key_capture_error)
        self.capture_hotkey_worker.start_listening()

    @Slot(object, str)
    def handle_key_capture(self, key_obj, key_str):
        if self.setting_key_for == "ptt":
            self.app_settings.ptt_key_str = key_str
            self.ptt_key_display_label.setText(self.format_key_name(key_str))
        self.finish_setting_key()
        self.save_settings()

    @Slot(str)
    def handle_key_capture_error(self, error_msg):
        QMessageBox.warning(self, "Hotkey Error", f"Could not capture key: {error_msg}")
        self.finish_setting_key()
        self.start_hotkey_listener()

    def finish_setting_key(self):
        if not self.setting_key_for:
            return
        self.set_ptt_key_button.setText(self.original_button_text or "Change")
        self.setting_key_for = None
        self.set_other_controls_enabled(True)
        if self.capture_hotkey_worker:
            try:
                self.capture_hotkey_worker.key_captured_signal.disconnect(self.handle_key_capture)
            except (RuntimeError, TypeError):
                pass
            try:
                self.capture_hotkey_worker.error_signal.disconnect(self.handle_key_capture_error)
            except (RuntimeError, TypeError):
                pass
            self.capture_hotkey_worker.stop_listening()
            self.capture_hotkey_worker.deleteLater()
        self.capture_hotkey_worker = None

    def set_other_controls_enabled(self, enabled):
        self.start_button.setEnabled(enabled and not self.is_dictation_running)
        self.stop_button.setEnabled(enabled and self.is_dictation_running)
        self.set_config_enabled(enabled)
        self.update_transport_button_state()

    def _set_button_state(self, button: QPushButton, state: str) -> None:
        if button.property("state") == state:
            return
        button.setProperty("state", state)
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()

    def update_transport_button_state(self):
        if self._is_stopping:
            self._set_button_state(self.start_button, "inactive")
            self._set_button_state(self.stop_button, "busy")
        elif self.is_dictation_running:
            self._set_button_state(self.start_button, "inactive")
            self._set_button_state(self.stop_button, "active")
        else:
            self._set_button_state(self.start_button, "primary")
            self._set_button_state(self.stop_button, "inactive")

    @Slot()
    def toggle_vad(self):
        self.update_vad_button_style()
        self.save_settings()
        if self.dictation_worker and self.is_dictation_running:
            self.dictation_worker.set_vad_enabled(self.vad_toggle_button.isChecked())

    def update_vad_button_style(self):
        if self.vad_toggle_button.isChecked():
            self.vad_toggle_button.setText("VAD: ON")
        else:
            self.vad_toggle_button.setText("PTT: ON")

        ptt_key_name = self.format_key_name(self.app_settings.ptt_key_str)
        if not self.is_dictation_running:
            self.hint_label.setText("Select PTT or VAD mode and click Start")
            self.hint_label.setStyleSheet("color: #888; font-style: italic;")
        elif self.vad_toggle_button.isChecked():
            self.hint_label.setText("Listening for speech...")
            self.hint_label.setStyleSheet("color: #0A84FF; font-style: italic;")
        else:
            self.hint_label.setText(f"Hold '{ptt_key_name}' to speak")
            self.hint_label.setStyleSheet("color: #0A84FF; font-style: italic;")

    @Slot(str)
    def update_status(self, status_text):
        self.statusBar.showMessage(status_text)
        if "Listening" in status_text:
            self.update_vad_button_style()

    @Slot(str)
    def handle_transcription(self, text):
        current_text = self.transcription_display.toPlainText()
        prefix = "\n" if current_text and not current_text.endswith(("\n", " ")) else ""
        if prefix == "" and current_text and not current_text.endswith(" "):
            prefix = " "
        self.transcription_display.insertPlainText(prefix + text.strip())
        self.transcription_display.moveCursor(QTextCursor.End)

    @Slot(float)
    def update_visualizer(self, amplitude):
        self.visualizer.setValue(min(1000, int(amplitude)))

    @Slot(str)
    def show_error(self, error_text):
        self.update_status("Error")
        if self.is_dictation_running:
            self.stop_dictation()
        else:
            self.reset_ui_after_stop()
        QMessageBox.critical(self, "OmniDictate Error", error_text)

    @Slot(object)
    def handle_reasoning_preview(self, payload):
        if not isinstance(payload, PreviewPayload):
            return
        dialog = ReasoningPreviewDialog(payload, self)
        if dialog.exec() == QDialog.Accepted:
            approved_text = dialog.typed_text()
            if approved_text:
                self.manual_type_signal.emit(approved_text)

    @Slot(str)
    def handle_context_update(self, description):
        self.context_status_label.setText(self._format_context_status(description))
        self.context_drop_area.set_summary(description or "No attachments")
        self._set_route_status(self._estimate_route_label(description))

    @Slot(str)
    def handle_route_update(self, label):
        self._set_route_status(label)

    def _request_dictation_worker_stop(self):
        if not self.dictation_worker:
            return
        try:
            if self.dictation_thread and self.dictation_thread.isRunning():
                QMetaObject.invokeMethod(
                    self.dictation_worker,
                    "stop_processing",
                    Qt.ConnectionType.QueuedConnection,
                )
            else:
                self.dictation_worker.stop_processing()
        except Exception:
            self.dictation_worker.stop_processing()

    def copy_transcription(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.transcription_display.toPlainText())
        self.statusBar.showMessage("Transcription copied to clipboard!", 2000)

    def start_dictation(self):
        if self.is_dictation_running:
            return
        if isinstance(self.dictation_thread, QThread) or isinstance(self.dictation_worker, DictationWorker):
            if self.dictation_thread and self.dictation_thread.isRunning():
                QMessageBox.critical(self, "Error", "Previous dictation process still running. Please wait or restart.")
                return
            self.dictation_worker = None
            self.dictation_thread = None

        self.save_settings()
        worker_settings = AppSettings(**self.app_settings.to_dict())
        self.dictation_thread = QThread(self)
        self.dictation_worker = DictationWorker(
            gui_wid=int(self.winId()),
            app_settings=worker_settings,
            visual_context_manager=self.visual_context_manager,
        )
        self.dictation_worker.moveToThread(self.dictation_thread)
        self.dictation_worker.status_updated.connect(self.update_status)
        self.dictation_worker.transcription_ready.connect(self.handle_transcription)
        self.dictation_worker.preview_requested.connect(self.handle_reasoning_preview)
        self.dictation_worker.error_occurred.connect(self.show_error)
        self.dictation_worker.audio_level.connect(self.update_visualizer)
        self.dictation_worker.context_updated.connect(self.handle_context_update)
        self.dictation_worker.route_updated.connect(self.handle_route_update)
        self.dictation_worker.runtime_updated.connect(self.handle_runtime_update)
        self.dictation_worker.stop_completed.connect(self.dictation_thread.quit)
        self.dictation_thread.started.connect(self.dictation_worker.start_processing)
        self.dictation_thread.finished.connect(self.dictation_worker.deleteLater)
        self.dictation_thread.finished.connect(self.dictation_thread.deleteLater)
        self.dictation_thread.finished.connect(self.on_thread_finished)
        self.ptt_signal.connect(self.dictation_worker.set_ptt_state)
        self.manual_type_signal.connect(self.dictation_worker.queue_manual_text)
        self.prompt_mode_signal.connect(self.dictation_worker.set_prompt_mode)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.runtime_diagnostics = None
        self.runtime_status_button.setText("Runtime: Checking...")
        self.runtime_status_button.setProperty("runtimeState", "checking")
        self.runtime_status_button.style().unpolish(self.runtime_status_button)
        self.runtime_status_button.style().polish(self.runtime_status_button)
        self.runtime_status_button.update()
        self.set_config_enabled(False)
        self.dictation_thread.start()
        self.is_dictation_running = True
        self.update_vad_button_style()
        self.update_transport_button_state()
        self.update_status_strip()

    def stop_dictation(self):
        if (not self.is_dictation_running and self.start_button.isEnabled()) or self._is_stopping:
            return
        self._is_stopping = True
        self.update_status("Stopping...")
        self.stop_button.setEnabled(False)
        self.update_transport_button_state()
        if self.dictation_worker:
            try:
                self.ptt_signal.disconnect(self.dictation_worker.set_ptt_state)
            except RuntimeError:
                pass
            try:
                self.manual_type_signal.disconnect(self.dictation_worker.queue_manual_text)
            except RuntimeError:
                pass
            try:
                self.prompt_mode_signal.disconnect(self.dictation_worker.set_prompt_mode)
            except RuntimeError:
                pass
            self._request_dictation_worker_stop()

        if not (self.dictation_thread and self.dictation_thread.isRunning()):
            self.on_thread_finished(force_reset=True)

    @Slot()
    def on_thread_finished(self, force_reset=False):
        self._is_stopping = False
        if self.is_dictation_running or force_reset:
            self.is_dictation_running = False
            self.reset_ui_after_stop()
        self.dictation_worker = None
        self.dictation_thread = None
        self.visualizer.setValue(0)
        self.update_vad_button_style()
        self.update_status_strip()

    def reset_ui_after_stop(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.set_config_enabled(True)
        self.update_transport_button_state()
        self.update_status("Idle")

    def set_config_enabled(self, enabled: bool):
        self._settings_controls_enabled = enabled
        self.on_backend_changed()

    def restart_hotkey_listener(self):
        if not self._allow_global_hotkeys:
            return
        self.start_hotkey_listener()

    def start_hotkey_listener(self):
        if not self._allow_global_hotkeys or self.setting_key_for:
            return
        self.stop_hotkey_listener()
        self.hotkey_worker = HotkeyWorker(ptt_key_str=self.app_settings.ptt_key_str, capture_mode=False, parent=self)
        self.hotkey_worker.ptt_pressed_signal.connect(self.on_ptt_pressed)
        self.hotkey_worker.ptt_released_signal.connect(self.on_ptt_released)
        self.hotkey_worker.mode_switch_signal.connect(self.on_mode_switch_requested)
        self.hotkey_worker.error_signal.connect(self.handle_hotkey_error)
        self.hotkey_worker.start_listening()

    def stop_hotkey_listener(self):
        if self.hotkey_worker:
            try:
                self.hotkey_worker.ptt_pressed_signal.disconnect(self.on_ptt_pressed)
            except (RuntimeError, TypeError):
                pass
            try:
                self.hotkey_worker.ptt_released_signal.disconnect(self.on_ptt_released)
            except (RuntimeError, TypeError):
                pass
            try:
                self.hotkey_worker.mode_switch_signal.disconnect(self.on_mode_switch_requested)
            except (RuntimeError, TypeError):
                pass
            try:
                self.hotkey_worker.error_signal.disconnect(self.handle_hotkey_error)
            except (RuntimeError, TypeError):
                pass
            self.hotkey_worker.stop_listening()
            self.hotkey_worker.deleteLater()
        self.hotkey_worker = None

    def _show_prompt_mode_hint(self, message: str, color: str = "#0A84FF"):
        self._hint_restore_timer.stop()
        self.hint_label.setText(message)
        self.hint_label.setStyleSheet(f"color: {color}; font-style: italic;")
        self._hint_restore_timer.start(2600)

    @Slot(str)
    def on_mode_switch_requested(self, prompt_mode: str):
        index = self.prompt_mode_combo.findData(prompt_mode)
        if index == -1:
            return

        combo_model = self.prompt_mode_combo.model()
        combo_item = combo_model.item(index) if hasattr(combo_model, "item") else None
        if combo_item is not None and not combo_item.isEnabled():
            message = self.prompt_mode_combo.itemData(index, Qt.ToolTipRole) or "That mode is not available for the current runtime."
            self._show_prompt_mode_hint(message, "#C76B1C")
            return

        if self.prompt_mode_combo.currentData() != prompt_mode:
            self.prompt_mode_combo.setCurrentIndex(index)

        self._set_route_status(self._estimate_route_label())
        self.update_status_strip()

        if self.is_dictation_running and self.dictation_worker:
            self.prompt_mode_signal.emit(prompt_mode)

        self._show_prompt_mode_hint(f"Mode switched to {self._prompt_mode_label(prompt_mode)}")

    @Slot()
    def on_ptt_pressed(self):
        if self.is_dictation_running:
            self.ptt_signal.emit(True)
            if not self.vad_toggle_button.isChecked():
                ptt_key_name = self.format_key_name(self.app_settings.ptt_key_str)
                self.hint_label.setText(f"Recording... release '{ptt_key_name}' to transcribe")
                self.hint_label.setStyleSheet("color: #0A84FF; font-style: italic;")

    @Slot()
    def on_ptt_released(self):
        if self.is_dictation_running:
            self.ptt_signal.emit(False)
            if not self.vad_toggle_button.isChecked():
                self.hint_label.setText("Transcribing...")
                self.hint_label.setStyleSheet("color: #0A84FF; font-style: italic;")

    def handle_hotkey_error(self, error_msg):
        QMessageBox.warning(self, "Hotkey Listener Error", f"Error in hotkey listener: {error_msg}")

    def select_context_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Attach Images or Video",
            os.getcwd(),
            "Media Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.mp4 *.mov *.avi *.mkv *.webm *.m4v)",
        )
        if file_paths:
            self.handle_files_dropped(file_paths)

    @Slot(list)
    def handle_files_dropped(self, paths):
        attached_names = self.visual_context_manager.attach_files(paths)
        if not attached_names:
            QMessageBox.warning(self, "Unsupported Files", "No supported image or video files were attached.")
            return
        self.update_context_summary()
        self.statusBar.showMessage(f"Attached context: {', '.join(attached_names)}", 3000)

    def clear_context_assets(self):
        self.visual_context_manager.clear_assets()
        self.update_context_summary()

    def update_context_summary(self):
        description = self.visual_context_manager.describe()
        self.context_drop_area.set_summary(description)
        self.context_status_label.setText(self._format_context_status(description))
        self._set_route_status(self._estimate_route_label(description))

    def update_status_strip(self):
        backend_label = self.backend_combo.currentText() if hasattr(self, "backend_combo") else self.app_settings.backend
        self.backend_status_label.setText(f"Backend: {backend_label}")
        prompt_text = self.app_settings.prompt_mode_display_name
        self.prompt_status_label.setText(f"Mode: {prompt_text}")
        self.model_display_label.setText(f"Model: {self.app_settings.model_display_name}")
        self.update_runtime_badge()
        self.update_context_summary()

    def closeEvent(self, event):
        self.save_settings()
        self.stop_dictation()
        if self.dictation_thread and self.dictation_thread.isRunning():
            self.dictation_thread.wait(5000)
        if self.capture_hotkey_worker:
            self.capture_hotkey_worker.stop_listening()
            self.capture_hotkey_worker.deleteLater()
            self.capture_hotkey_worker = None
        if self.preload_thread and self.preload_thread.isRunning():
            self.preload_thread.quit()
            self.preload_thread.wait(1000)
        if self.download_worker:
            self.download_worker.request_cancel()
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.quit()
            self.download_thread.wait(1000)
        if self.update_thread and self.update_thread.isRunning():
            self.update_thread.quit()
            self.update_thread.wait(1000)
        self.stop_hotkey_listener()
        event.accept()


def _argument_value(flag: str, default: str = "") -> str:
    try:
        index = sys.argv.index(flag)
    except ValueError:
        return default
    if index + 1 >= len(sys.argv):
        return default
    return sys.argv[index + 1]


def run_package_smoke() -> int:
    report_path = _argument_value("--package-smoke-report")
    model_name = _argument_value("--package-smoke-model", "tiny")
    load_whisper = "--package-smoke-load-whisper" in sys.argv
    payload = {
        "status": "failed",
        "package_profile": os.environ.get("OMNIDICTATE_PACKAGE_PROFILE", ""),
        "checks": {},
        "failures": [],
    }

    def record_failure(message: str) -> None:
        payload["failures"].append(message)

    if payload["package_profile"] in {"whisper", "whisper-only", "baseline"}:
        payload["checks"]["package_profile"] = "passed"
    else:
        payload["checks"]["package_profile"] = "failed"
        record_failure("Packaged runtime is not using the Whisper-only profile.")

    try:
        import av  # noqa: F401

        payload["checks"]["av_import"] = "passed"
    except Exception as exc:
        payload["checks"]["av_import"] = "failed"
        record_failure(f"av import failed: {exc}")

    try:
        import faster_whisper  # noqa: F401

        payload["checks"]["faster_whisper_import"] = "passed"
    except Exception as exc:
        payload["checks"]["faster_whisper_import"] = "failed"
        record_failure(f"faster-whisper import failed: {exc}")

    try:
        settings = AppSettings(backend="faster-whisper", whisper_model=model_name)
        sanitize_app_settings_for_runtime(settings)
        if settings.backend != "faster-whisper" or settings.prompt_mode != "pure":
            raise RuntimeError("Whisper-only runtime settings did not sanitize to Faster-Whisper / Pure.")
        payload["checks"]["runtime_settings"] = "passed"
    except Exception as exc:
        payload["checks"]["runtime_settings"] = "failed"
        record_failure(str(exc))

    if load_whisper:
        backend = None
        try:
            backend = create_backend(AppSettings(backend="faster-whisper", whisper_model=model_name))
            load_result = backend.load()
            payload["checks"]["whisper_load"] = load_result.status_message
            if not load_result.success:
                record_failure(load_result.status_message)
        except Exception as exc:
            payload["checks"]["whisper_load"] = "failed"
            record_failure(f"Whisper load failed: {exc}")
        finally:
            if backend is not None:
                try:
                    backend.unload()
                except Exception:
                    pass

    if not payload["failures"]:
        payload["status"] = "passed"

    if report_path:
        with open(report_path, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2)
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    if "--package-smoke-report" in sys.argv:
        raise SystemExit(run_package_smoke())

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("omnicorp.omnidictate.gui.3.0.1")
    except Exception as exc:
        print(f"Error setting AppUserModelID: {exc}")

    app = QApplication(sys.argv)
    try:
        basedir = os.path.dirname(__file__)
        icon_path = os.path.join(basedir, "icon.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception as exc:
        print(f"Error setting application icon: {exc}")

    try:
        style_path = os.path.join(os.path.dirname(__file__), "style.qss")
        with open(style_path, "r", encoding="utf-8") as file_handle:
            app.setStyleSheet(file_handle.read())
    except Exception as exc:
        print(f"Error loading stylesheet: {exc}")

    window = OmniDictateApp()
    window.show()
    sys.exit(app.exec())
