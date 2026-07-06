from __future__ import annotations

import argparse
import ctypes
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from core_logic import DictationWorker
from engines.context_capture import VisualContextManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open Notepad and verify OmniDictate's live typing thread against the active window."
    )
    parser.add_argument(
        "--text",
        default="OmniDictate live typing smoke",
        help="Text to type into Notepad.",
    )
    parser.add_argument("--timeout", type=float, default=8.0, help="Seconds to wait for Notepad typing.")
    parser.add_argument("--guard-seconds", type=float, default=1.0, help="Seconds to verify the own-window guard.")
    parser.add_argument("--keep-file", action="store_true", help="Keep the temporary Notepad file.")
    return parser.parse_args()


def _foreground_hwnd() -> int:
    return int(ctypes.windll.user32.GetForegroundWindow())


def _save_notepad_file() -> None:
    from pynput.keyboard import Controller, Key

    keyboard = Controller()
    keyboard.press(Key.ctrl_l)
    keyboard.press("s")
    keyboard.release("s")
    keyboard.release(Key.ctrl_l)
    time.sleep(0.25)


def _find_window_for_process(process_id: int) -> int:
    import win32gui
    import win32process

    matches: list[int] = []

    def _callback(hwnd, _extra):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        _, window_process_id = win32process.GetWindowThreadProcessId(hwnd)
        if window_process_id == process_id:
            matches.append(hwnd)
            return False
        return True

    win32gui.EnumWindows(_callback, None)
    return matches[0] if matches else 0


def _find_window_by_title_token(title_token: str) -> int:
    import win32gui

    token = title_token.lower()
    matches: list[int] = []

    def _callback(hwnd, _extra):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd).lower()
        if token in title:
            matches.append(hwnd)
            return False
        return True

    win32gui.EnumWindows(_callback, None)
    return matches[0] if matches else 0


def _focus_window(hwnd: int) -> None:
    import win32con
    import win32gui

    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.BringWindowToTop(hwnd)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.35)


def _focus_notepad(process_id: int, title_token: str) -> int:
    deadline = time.time() + 10
    hwnd = 0
    while time.time() < deadline:
        hwnd = _find_window_for_process(process_id) or _find_window_by_title_token(title_token)
        if hwnd:
            break
        time.sleep(0.2)
    if not hwnd:
        raise RuntimeError(
            f"Could not find a visible Notepad window for process {process_id} or title token {title_token!r}."
        )

    _focus_window(hwnd)
    return hwnd


def _close_notepad(hwnd: int, process: subprocess.Popen) -> None:
    from pynput.keyboard import Controller, Key

    try:
        _focus_window(hwnd)
        keyboard = Controller()
        keyboard.press(Key.ctrl_l)
        keyboard.press("w")
        keyboard.release("w")
        keyboard.release(Key.ctrl_l)
        time.sleep(0.5)
    except Exception:
        pass

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            process.kill()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-16")


def _build_worker(gui_wid: int) -> DictationWorker:
    QCoreApplication.instance() or QCoreApplication([])
    settings = AppSettings(
        backend="faster-whisper",
        whisper_model="tiny",
        char_delay=0.02,
        screen_context_enabled=False,
        webcam_enabled=False,
    )
    return DictationWorker(
        gui_wid=gui_wid,
        app_settings=settings,
        visual_context_manager=VisualContextManager(settings),
    )


def main() -> int:
    args = parse_args()
    temp_path = Path(tempfile.gettempdir()) / f"omnidictate_live_typing_smoke_{int(time.time())}.txt"
    temp_path.write_text("", encoding="utf-8")

    process = subprocess.Popen(["notepad.exe", str(temp_path)])
    worker: DictationWorker | None = None
    typing_thread: threading.Thread | None = None
    target_hwnd = 0
    try:
        target_hwnd = _focus_notepad(process.pid, temp_path.name)
        if _foreground_hwnd() != target_hwnd:
            target_hwnd = _foreground_hwnd()
        if not target_hwnd:
            raise RuntimeError("Could not resolve the Notepad foreground window handle.")

        worker = _build_worker(gui_wid=target_hwnd)
        worker._is_running = True
        worker.stop_typing_event.clear()
        typing_thread = threading.Thread(target=worker._typing_loop, daemon=True)
        typing_thread.start()

        worker.text_queue.put(args.text)
        time.sleep(args.guard_seconds)
        _save_notepad_file()
        guarded_content = _read_text(temp_path)
        if args.text in guarded_content:
            raise AssertionError("Own-window guard failed: text was typed while the target was marked as OmniDictate.")

        _focus_notepad(process.pid, temp_path.name)
        worker.gui_wid = 0
        deadline = time.time() + args.timeout
        typed_content = guarded_content
        while time.time() < deadline:
            _save_notepad_file()
            typed_content = _read_text(temp_path)
            if args.text in typed_content:
                print(f"Live typing smoke passed: typed into Notepad via worker thread. File={temp_path}")
                return 0
            time.sleep(0.4)

        raise AssertionError(f"Timed out waiting for worker text in Notepad. Last content: {typed_content!r}")
    finally:
        if worker is not None:
            worker._is_running = False
            worker.stop_typing_event.set()
        if typing_thread is not None:
            typing_thread.join(timeout=2.0)
        if target_hwnd:
            _close_notepad(target_hwnd, process)
        elif process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                process.kill()
        if not args.keep_file:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
