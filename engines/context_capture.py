from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from PIL import Image, ImageGrab

from .base import TargetAppContext, VisualContextSnapshot, VisualSource

try:
    import win32gui
    import win32process
except Exception:
    win32gui = None
    win32process = None

try:
    import psutil
except Exception:
    psutil = None


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def is_image_path(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def is_video_path(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def get_foreground_app_context() -> TargetAppContext:
    if win32gui is None:
        return TargetAppContext()
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        process_name = ""
        executable = ""
        if win32process is not None:
            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            if psutil is not None:
                try:
                    process = psutil.Process(process_id)
                    process_name = process.name()
                    executable = process.exe()
                except Exception:
                    process_name = str(process_id)
            else:
                process_name = str(process_id)
        return TargetAppContext(title=title, process_name=process_name, executable=executable)
    except Exception:
        return TargetAppContext()


class VisualContextManager:
    def __init__(self, app_settings):
        self._lock = threading.Lock()
        self.app_settings = app_settings
        self.attached_images: list[Image.Image] = []
        self.attached_image_names: list[str] = []
        self.attached_video_frames: list[Image.Image] = []
        self.attached_video_names: list[str] = []
        self._camera = None
        self._last_screen_capture = 0.0
        self._last_screen_image = None

    def update_settings(self, app_settings) -> None:
        with self._lock:
            self.app_settings = app_settings

    def clear_assets(self) -> None:
        with self._lock:
            self.attached_images.clear()
            self.attached_image_names.clear()
            self.attached_video_frames.clear()
            self.attached_video_names.clear()

    def attach_files(self, paths: list[str]) -> list[str]:
        attached_names: list[str] = []
        with self._lock:
            for raw_path in paths:
                path = str(raw_path)
                if is_image_path(path):
                    image = Image.open(path).convert("RGB")
                    self.attached_images.append(image)
                    self.attached_image_names.append(os.path.basename(path))
                    attached_names.append(os.path.basename(path))
                elif is_video_path(path):
                    frames = self._sample_video_frames(path)
                    if frames:
                        self.attached_video_frames.extend(frames)
                        self.attached_video_names.append(os.path.basename(path))
                        attached_names.append(os.path.basename(path))
        return attached_names

    def describe(self) -> str:
        with self._lock:
            app_context = get_foreground_app_context() if self.app_settings.screen_context_enabled else TargetAppContext()
            return self._build_description_locked(app_context)

    def capture_snapshot(self) -> VisualContextSnapshot:
        with self._lock:
            images = list(self.attached_images)
            video_frames = list(self.attached_video_frames)
            app_context = TargetAppContext()
            metadata = {
                "attachment_names": ", ".join(self.attached_image_names + self.attached_video_names),
                "screen_target": self.app_settings.screen_target,
            }
            source = VisualSource.NONE

            if self.app_settings.screen_context_enabled:
                screen_image, app_context = self._capture_screen_locked()
                if screen_image is not None:
                    images.insert(0, screen_image)
                    metadata["window_title"] = app_context.title
                    metadata["process_name"] = app_context.process_name
                    source = (
                        VisualSource.SCREEN_ACTIVE_WINDOW
                        if self.app_settings.screen_target == "active-window"
                        else VisualSource.SCREEN_FULL
                    )

            if self.app_settings.webcam_enabled:
                webcam_frame = self._capture_webcam_locked()
                if webcam_frame is not None:
                    images.append(webcam_frame)
                    source = VisualSource.WEBCAM if source == VisualSource.NONE else VisualSource.MIXED

            if self.attached_images:
                source = VisualSource.ATTACHED_IMAGE if source == VisualSource.NONE else VisualSource.MIXED
            if self.attached_video_frames:
                source = VisualSource.ATTACHED_VIDEO if source == VisualSource.NONE else VisualSource.MIXED

            return VisualContextSnapshot(
                source=source,
                images=images,
                video_frames=video_frames,
                metadata=metadata,
                description=self._build_description_locked(app_context),
            )

    def _build_description_locked(self, app_context: TargetAppContext | None = None) -> str:
        parts: list[str] = []
        if self.app_settings.screen_context_enabled:
            target = "Active window capture" if self.app_settings.screen_target == "active-window" else "Full screen capture"
            window_label = (app_context.title or "").strip() if app_context else ""
            process_label = (app_context.process_name or "").strip() if app_context else ""
            if window_label:
                target = f"{target}: {window_label}"
                if process_label:
                    target += f" ({process_label})"
            elif process_label:
                target = f"{target}: {process_label}"
            else:
                target += " enabled"
            parts.append(target)
        if self.attached_image_names:
            parts.append(f"Images: {', '.join(self.attached_image_names)}")
        if self.attached_video_names:
            parts.append(f"Videos: {', '.join(self.attached_video_names)}")
        if self.app_settings.webcam_enabled:
            parts.append("Webcam enabled")
        return " | ".join(parts) if parts else "No visual context"

    def _capture_screen_locked(self):
        now = time.time()
        min_interval = max(self.app_settings.visual_capture_interval_ms, 100) / 1000.0
        if self._last_screen_image is not None and (now - self._last_screen_capture) < min_interval:
            return self._last_screen_image, get_foreground_app_context()

        app_context = get_foreground_app_context()
        try:
            if self.app_settings.screen_target == "active-window" and win32gui is not None:
                hwnd = win32gui.GetForegroundWindow()
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                image = ImageGrab.grab(bbox=(left, top, right, bottom)).convert("RGB")
            else:
                image = ImageGrab.grab().convert("RGB")
            self._last_screen_image = image
            self._last_screen_capture = now
            return image, app_context
        except Exception:
            return None, app_context

    def _capture_webcam_locked(self):
        try:
            import cv2
        except Exception:
            return None
        try:
            if self._camera is None:
                self._camera = cv2.VideoCapture(0)
            success, frame = self._camera.read()
            if not success:
                return None
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return Image.fromarray(frame)
        except Exception:
            return None

    def _sample_video_frames(self, path: str) -> list[Image.Image]:
        try:
            import av
        except Exception:
            return []
        try:
            container = av.open(path)
            video_stream = next((stream for stream in container.streams if stream.type == "video"), None)
            if video_stream is None:
                return []

            max_frames = max(1, self.app_settings.video_frame_limit)
            frames: list[Image.Image] = []
            total_collected = 0
            for frame in container.decode(video_stream):
                image = frame.to_image().convert("RGB")
                frames.append(image)
                total_collected += 1
                if total_collected >= max_frames:
                    break
            container.close()
            return frames
        except Exception:
            return []
