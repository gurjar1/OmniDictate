from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.base import VisualSource
from engines.context_capture import VisualContextManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exercise visual context capture and attachment paths.")
    parser.add_argument(
        "--asset-dir",
        default=str(ROOT / "smoke_test_assets" / "visual_context"),
        help="Directory for generated smoke assets.",
    )
    return parser.parse_args()


def _make_image(path: Path, label: str) -> None:
    image = Image.new("RGB", (180, 96), (32, 48, 64))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 170, 86), outline=(236, 240, 244), width=2)
    draw.text((20, 38), label, fill=(255, 255, 255))
    image.save(path)


def _make_video(path: Path) -> bool:
    try:
        import av
    except Exception as exc:
        print(f"SKIP: PyAV unavailable for generated video fixture: {exc}")
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    container = av.open(str(path), mode="w")
    try:
        stream = container.add_stream("mpeg4", rate=1)
        stream.width = 96
        stream.height = 64
        stream.pix_fmt = "yuv420p"
        for index, color in enumerate([(96, 32, 32), (32, 96, 48), (32, 48, 112)]):
            image = Image.new("RGB", (96, 64), color)
            draw = ImageDraw.Draw(image)
            draw.text((10, 24), f"frame {index + 1}", fill=(255, 255, 255))
            frame = av.VideoFrame.from_image(image)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    finally:
        container.close()
    return True


def _assert_image_attachment(asset_dir: Path) -> None:
    image_path = asset_dir / "visual-context-image.png"
    _make_image(image_path, "OmniDictate image")

    settings = AppSettings(prompt_mode="context")
    manager = VisualContextManager(settings)
    attached = manager.attach_files([str(image_path)])
    if attached != [image_path.name]:
        raise AssertionError(f"Image attachment failed: {attached}")
    snapshot = manager.capture_snapshot()
    if snapshot.source != VisualSource.ATTACHED_IMAGE:
        raise AssertionError(f"Expected attached image source, got {snapshot.source}")
    if len(snapshot.images) != 1:
        raise AssertionError(f"Expected one attached image, got {len(snapshot.images)}")
    print(f"Image attachment smoke passed: {snapshot.description}")


def _assert_video_attachment(asset_dir: Path) -> None:
    video_path = asset_dir / "visual-context-video.mp4"
    if not _make_video(video_path):
        return

    settings = AppSettings(prompt_mode="context", video_frame_limit=2)
    manager = VisualContextManager(settings)
    attached = manager.attach_files([str(video_path)])
    if attached != [video_path.name]:
        raise AssertionError(f"Video attachment failed: {attached}")
    snapshot = manager.capture_snapshot()
    if snapshot.source != VisualSource.ATTACHED_VIDEO:
        raise AssertionError(f"Expected attached video source, got {snapshot.source}")
    if not (1 <= len(snapshot.video_frames) <= 2):
        raise AssertionError(f"Expected 1-2 sampled video frames, got {len(snapshot.video_frames)}")
    print(f"Video attachment smoke passed: frames={len(snapshot.video_frames)} {snapshot.description}")


def _assert_screen_capture_fail_soft(screen_target: str) -> None:
    settings = AppSettings(
        prompt_mode="context",
        screen_context_enabled=True,
        screen_target=screen_target,
        visual_capture_interval_ms=100,
    )
    manager = VisualContextManager(settings)
    snapshot = manager.capture_snapshot()
    if snapshot.source not in {
        VisualSource.NONE,
        VisualSource.SCREEN_ACTIVE_WINDOW,
        VisualSource.SCREEN_FULL,
    }:
        raise AssertionError(f"Unexpected screen source for {screen_target}: {snapshot.source}")
    print(
        "Screen context smoke passed: "
        f"target={screen_target} source={snapshot.source.value} images={len(snapshot.images)}"
    )


def _assert_webcam_fail_soft() -> None:
    settings = AppSettings(prompt_mode="context", webcam_enabled=True)
    manager = VisualContextManager(settings)
    snapshot = manager.capture_snapshot()
    if snapshot.source not in {VisualSource.NONE, VisualSource.WEBCAM}:
        raise AssertionError(f"Unexpected webcam source: {snapshot.source}")
    print(f"Webcam fail-soft smoke passed: source={snapshot.source.value} images={len(snapshot.images)}")


def main() -> int:
    args = parse_args()
    asset_dir = Path(args.asset_dir)
    asset_dir.mkdir(parents=True, exist_ok=True)

    _assert_image_attachment(asset_dir)
    _assert_video_attachment(asset_dir)
    _assert_screen_capture_fail_soft("active-window")
    _assert_screen_capture_fail_soft("full-screen")
    _assert_webcam_fail_soft()
    print("Visual context smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
