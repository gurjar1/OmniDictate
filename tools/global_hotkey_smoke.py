from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, Slot

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hotkey_listener import HotkeyWorker


class _HotkeyEventSink(QObject):
    def __init__(self):
        super().__init__()
        self.events: list[object] = []

    @Slot()
    def on_ptt_pressed(self) -> None:
        self.events.append("ptt-pressed")

    @Slot()
    def on_ptt_released(self) -> None:
        self.events.append("ptt-released")

    @Slot(str)
    def on_mode_switch(self, mode: str) -> None:
        self.events.append(("mode", mode))

    @Slot(str)
    def on_error(self, message: str) -> None:
        self.events.append(("error", message))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify real global key events reach OmniDictate's hotkey worker.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for each expected event.")
    return parser.parse_args()


def _wait_for(predicate, timeout: float, app: QCoreApplication, label: str) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {label}.")


def _press_key(key) -> None:
    from pynput.keyboard import Controller

    keyboard = Controller()
    keyboard.press(key)
    time.sleep(0.15)
    keyboard.release(key)
    time.sleep(0.15)


def _press_ctrl_number(number: str) -> None:
    from pynput.keyboard import Controller, Key

    keyboard = Controller()
    keyboard.press(Key.ctrl_l)
    time.sleep(0.05)
    keyboard.press(number)
    time.sleep(0.05)
    keyboard.release(number)
    time.sleep(0.05)
    keyboard.release(Key.ctrl_l)
    time.sleep(0.15)


def main() -> int:
    args = parse_args()
    app = QCoreApplication.instance() or QCoreApplication([])

    sink = _HotkeyEventSink()
    worker = HotkeyWorker(ptt_key_str="key:shift_r")
    worker.ptt_pressed_signal.connect(sink.on_ptt_pressed)
    worker.ptt_released_signal.connect(sink.on_ptt_released)
    worker.mode_switch_signal.connect(sink.on_mode_switch)
    worker.error_signal.connect(sink.on_error)

    try:
        worker.start_listening()
        _wait_for(lambda: worker.listener is not None and worker.listener.is_alive(), args.timeout, app, "listener start")
        time.sleep(0.5)

        from pynput.keyboard import Key

        _press_key(Key.shift_r)
        _wait_for(lambda: "ptt-pressed" in sink.events, args.timeout, app, "PTT press")
        _wait_for(lambda: "ptt-released" in sink.events, args.timeout, app, "PTT release")

        _press_ctrl_number("1")
        _press_ctrl_number("2")
        _press_ctrl_number("3")
        _wait_for(lambda: ("mode", "pure") in sink.events, args.timeout, app, "Ctrl+1 mode switch")
        _wait_for(lambda: ("mode", "context") in sink.events, args.timeout, app, "Ctrl+2 mode switch")
        _wait_for(lambda: ("mode", "reasoning") in sink.events, args.timeout, app, "Ctrl+3 mode switch")

        errors = [event for event in sink.events if isinstance(event, tuple) and event[0] == "error"]
        if errors:
            raise AssertionError(f"Hotkey worker reported errors: {errors}")

        print("Global hotkey smoke passed: PTT and Ctrl+1/2/3 events reached HotkeyWorker.")
        return 0
    finally:
        worker.stop_listening()
        app.processEvents()


if __name__ == "__main__":
    raise SystemExit(main())
