from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class PromptMode(str, Enum):
    PURE = "pure"
    CONTEXT = "context"
    REASONING = "reasoning"


class ExecutionRoute(str, Enum):
    WHISPER_ONLY = "whisper-only"
    ALTERNATIVE_STT = "alternative-stt"
    GEMMA_HYBRID_REFINEMENT = "gemma-hybrid-refinement"
    GEMMA_NATIVE_AUDIO = "gemma-native-audio"
    GGUF_SERVER_REFINEMENT = "gguf-server-refinement"


EXECUTION_ROUTE_LABELS = {
    ExecutionRoute.WHISPER_ONLY: "Whisper only",
    ExecutionRoute.ALTERNATIVE_STT: "Alternative STT",
    ExecutionRoute.GEMMA_HYBRID_REFINEMENT: "Whisper -> Gemma",
    ExecutionRoute.GEMMA_NATIVE_AUDIO: "Native Gemma audio",
    ExecutionRoute.GGUF_SERVER_REFINEMENT: "Whisper -> GGUF server",
}


class VisualSource(str, Enum):
    NONE = "none"
    SCREEN_ACTIVE_WINDOW = "screen-active-window"
    SCREEN_FULL = "screen-full"
    ATTACHED_IMAGE = "attached-image"
    ATTACHED_VIDEO = "attached-video"
    WEBCAM = "webcam"
    MIXED = "mixed"


@dataclass(slots=True)
class TargetAppContext:
    title: str = ""
    process_name: str = ""
    executable: str = ""


@dataclass(slots=True)
class VisualContextSnapshot:
    source: VisualSource = VisualSource.NONE
    timestamp: float = field(default_factory=time.time)
    images: list[Any] = field(default_factory=list)
    video_frames: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.images and not self.video_frames and self.source == VisualSource.NONE


@dataclass(slots=True)
class TranscriptionRequest:
    audio: np.ndarray
    sample_rate: int
    language: str | None
    prompt_mode: PromptMode
    visual_context: VisualContextSnapshot
    target_app: TargetAppContext
    transcript_text: str | None = None
    enable_thinking: bool = False
    max_new_tokens: int = 96


@dataclass(slots=True)
class PreviewPayload:
    typed_text: str
    suggestions: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    raw_text: str
    prompt_mode: PromptMode
    used_visual_context: bool
    latency_seconds: float
    execution_route: ExecutionRoute = ExecutionRoute.WHISPER_ONLY
    warnings: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    preview: PreviewPayload | None = None

    @property
    def execution_label(self) -> str:
        return EXECUTION_ROUTE_LABELS.get(self.execution_route, str(self.execution_route))


@dataclass(slots=True)
class BackendLoadResult:
    success: bool
    status_message: str
    warnings: list[str] = field(default_factory=list)
    runtime_diagnostics: "RuntimeDiagnostics | None" = None


@dataclass(slots=True)
class RuntimeAction:
    label: str
    url: str


@dataclass(slots=True)
class RuntimeDiagnostics:
    status: str
    headline: str
    summary: str
    device: str = ""
    compute_type: str = ""
    next_steps: list[str] = field(default_factory=list)
    technical_details: list[str] = field(default_factory=list)
    actions: list[RuntimeAction] = field(default_factory=list)

    def plain_text(self) -> str:
        lines = [self.headline, "", self.summary]
        if self.next_steps:
            lines.extend(["", "Recommended next steps:"])
            lines.extend(f"{index}. {step}" for index, step in enumerate(self.next_steps, start=1))
        if self.technical_details:
            lines.extend(["", "Technical details:"])
            lines.extend(f"- {detail}" for detail in self.technical_details)
        if self.actions:
            lines.extend(["", "Links:"])
            lines.extend(f"- {action.label}: {action.url}" for action in self.actions)
        return "\n".join(lines).strip()


class TranscriptionBackend(ABC):
    def __init__(self, app_settings):
        self.app_settings = app_settings
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @abstractmethod
    def load(self) -> BackendLoadResult:
        raise NotImplementedError

    @abstractmethod
    def unload(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        raise NotImplementedError
