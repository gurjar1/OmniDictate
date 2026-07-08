from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any

from PySide6.QtCore import QSettings


CONFIG_ORG = os.environ.get("OMNIDICTATE_SETTINGS_ORG", "OmniCorp")
CONFIG_APP = os.environ.get("OMNIDICTATE_SETTINGS_APP", "OmniDictate")
RELEASE_DEFAULTS_VERSION = "3.0.1-public-defaults"

DEFAULT_FILTER_WORDS = [
    "thanks for watching!",
    "thank you.",
    "thanks for watching",
    "Thanks for watching.",
    "thank you",
    "I'm sorry",
    " I'm sorry,",
    "I'm sorry, ",
    "I'm sorry,",
]

WHISPER_ONLY_PACKAGE_PROFILES = {"whisper", "whisper-only", "baseline"}
WHISPER_ONLY_UNSUPPORTED_BACKENDS = {
    "gemma-4",
    "gemma-gguf-server",
    "transformers-asr",
}


def package_profile() -> str:
    return os.environ.get("OMNIDICTATE_PACKAGE_PROFILE", "").strip().lower()


def is_whisper_only_runtime() -> bool:
    return package_profile() in WHISPER_ONLY_PACKAGE_PROFILES


@dataclass(slots=True)
class AppSettings:
    backend: str = "faster-whisper"
    whisper_model: str = "large-v3-turbo"
    alternative_stt_model: str = "UsefulSensors/moonshine-tiny"
    gemma_hybrid_whisper_model: str = "small"
    gemma_model: str = "google/gemma-4-E2B-it"
    gguf_server_url: str = "http://127.0.0.1:8080/v1"
    gguf_model_name: str = ""
    gemma_quantization: str = "4-bit"
    gemma_audio_input_mode: str = "hybrid-whisper"
    language: str | None = "en"
    vad_enabled: bool = True
    silence_threshold: int = 500
    char_delay: float = 0.02
    type_into_active_app: bool = True
    min_ptt_duration_ms: int = 250
    ptt_key_str: str = "key:shift_r"
    filter_words: list[str] = field(default_factory=lambda: list(DEFAULT_FILTER_WORDS))
    prompt_mode: str = "pure"
    screen_context_enabled: bool = False
    screen_target: str = "active-window"
    webcam_enabled: bool = False
    visual_capture_interval_ms: int = 1500
    image_token_budget: int = 140
    video_frame_limit: int = 4
    model_storage_path: str = field(
        default_factory=lambda: os.path.join(
            os.environ.get("LOCALAPPDATA", os.getcwd()),
            "OmniDictate",
            "models",
        )
    )
    preload_model_on_launch: bool = False
    auto_check_updates: bool = True
    reasoning_requires_preview: bool = True

    @classmethod
    def from_qsettings(cls, settings: QSettings) -> "AppSettings":
        defaults = cls()
        raw_filter_words = settings.value("filter_words", DEFAULT_FILTER_WORDS)
        if not isinstance(raw_filter_words, list):
            raw_filter_words = list(DEFAULT_FILTER_WORDS)

        return cls(
            backend=settings.value("backend", defaults.backend),
            whisper_model=settings.value("whisper_model", defaults.whisper_model),
            alternative_stt_model=settings.value("alternative_stt_model", defaults.alternative_stt_model),
            gemma_hybrid_whisper_model=settings.value(
                "gemma_hybrid_whisper_model",
                defaults.gemma_hybrid_whisper_model,
            ),
            gemma_model=settings.value("gemma_model", defaults.gemma_model),
            gguf_server_url=settings.value("gguf_server_url", defaults.gguf_server_url),
            gguf_model_name=settings.value("gguf_model_name", defaults.gguf_model_name),
            gemma_quantization=settings.value("gemma_quantization", defaults.gemma_quantization),
            gemma_audio_input_mode=settings.value("gemma_audio_input_mode", defaults.gemma_audio_input_mode),
            language=settings.value("language", defaults.language),
            vad_enabled=settings.value("vad_enabled", defaults.vad_enabled, type=bool),
            silence_threshold=settings.value("silence_threshold", defaults.silence_threshold, type=int),
            char_delay=settings.value("char_delay", defaults.char_delay, type=float),
            type_into_active_app=settings.value(
                "type_into_active_app",
                defaults.type_into_active_app,
                type=bool,
            ),
            min_ptt_duration_ms=settings.value(
                "min_ptt_duration_ms",
                defaults.min_ptt_duration_ms,
                type=int,
            ),
            ptt_key_str=settings.value("ptt_key_str", defaults.ptt_key_str),
            filter_words=raw_filter_words,
            prompt_mode=settings.value("prompt_mode", defaults.prompt_mode),
            screen_context_enabled=settings.value(
                "screen_context_enabled",
                defaults.screen_context_enabled,
                type=bool,
            ),
            screen_target=settings.value("screen_target", defaults.screen_target),
            webcam_enabled=settings.value("webcam_enabled", defaults.webcam_enabled, type=bool),
            visual_capture_interval_ms=settings.value(
                "visual_capture_interval_ms",
                defaults.visual_capture_interval_ms,
                type=int,
            ),
            image_token_budget=settings.value("image_token_budget", defaults.image_token_budget, type=int),
            video_frame_limit=settings.value("video_frame_limit", defaults.video_frame_limit, type=int),
            model_storage_path=settings.value("model_storage_path", defaults.model_storage_path),
            preload_model_on_launch=settings.value(
                "preload_model_on_launch",
                defaults.preload_model_on_launch,
                type=bool,
            ),
            auto_check_updates=settings.value(
                "auto_check_updates",
                defaults.auto_check_updates,
                type=bool,
            ),
            reasoning_requires_preview=settings.value(
                "reasoning_requires_preview",
                defaults.reasoning_requires_preview,
                type=bool,
            ),
        )

    def write_to_qsettings(self, settings: QSettings) -> None:
        for key, value in asdict(self).items():
            settings.setValue(key, value)
        settings.sync()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def model_display_name(self) -> str:
        if self.backend == "gemma-4":
            return self.gemma_model.rsplit("/", 1)[-1]
        if self.backend == "gemma-gguf-server":
            return self.gguf_model_name or "GGUF server"
        if self.backend == "transformers-asr":
            return self.alternative_stt_model.rsplit("/", 1)[-1]
        return self.whisper_model

    @property
    def prompt_mode_display_name(self) -> str:
        mapping = {
            "pure": "Pure transcription",
            "context": "Context-enhanced",
            "reasoning": "Full reasoning",
        }
        return mapping.get(self.prompt_mode, self.prompt_mode)


def sanitize_app_settings_for_runtime(app_settings: AppSettings) -> list[str]:
    notices: list[str] = []
    if not is_whisper_only_runtime():
        return notices

    if app_settings.backend in WHISPER_ONLY_UNSUPPORTED_BACKENDS:
        notices.append(
            f"Saved backend '{app_settings.backend}' is not available in this Whisper-only build. "
            "Using Faster-Whisper."
        )
        app_settings.backend = "faster-whisper"
    elif app_settings.backend != "faster-whisper":
        notices.append("Saved backend is not available in this Whisper-only build. Using Faster-Whisper.")
        app_settings.backend = "faster-whisper"

    if app_settings.prompt_mode != "pure":
        notices.append("Saved output style uses experimental context/reasoning. Using Pure transcription.")
        app_settings.prompt_mode = "pure"

    if app_settings.screen_context_enabled or app_settings.webcam_enabled:
        notices.append("Saved visual-context options are disabled in the Whisper-only build.")
    app_settings.screen_context_enabled = False
    app_settings.webcam_enabled = False
    app_settings.preload_model_on_launch = False
    return notices


def migrate_release_defaults(settings: QSettings) -> bool:
    if settings.value("release_defaults_version", "") == RELEASE_DEFAULTS_VERSION:
        return False
    defaults = AppSettings()
    settings.setValue("whisper_model", defaults.whisper_model)
    settings.setValue("language", defaults.language)
    settings.setValue("type_into_active_app", defaults.type_into_active_app)
    settings.setValue("release_defaults_version", RELEASE_DEFAULTS_VERSION)
    settings.sync()
    return True


def load_app_settings(settings: QSettings | None = None) -> AppSettings:
    settings = settings or QSettings(CONFIG_ORG, CONFIG_APP)
    migrate_release_defaults(settings)
    app_settings = AppSettings.from_qsettings(settings)
    if app_settings.language in ["None", ""]:
        app_settings.language = None
    sanitize_app_settings_for_runtime(app_settings)
    return app_settings
