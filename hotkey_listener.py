import re

from pynput import keyboard
from PySide6.QtCore import QObject, Signal


def serialize_key(key) -> str:
    if isinstance(key, keyboard.Key):
        return f"key:{key.name}"
    if isinstance(key, keyboard.KeyCode):
        if key.char:
            return f"char:{key.char}"
        if getattr(key, "vk", None) is not None:
            return f"vk:{key.vk}"
    return str(key)


def deserialize_key(raw_key: str | None, default=None):
    if default is None:
        default = keyboard.Key.shift_r
    if not raw_key:
        return default

    try:
        if raw_key.startswith("key:"):
            return getattr(keyboard.Key, raw_key.split(":", 1)[1])
        if raw_key.startswith("char:"):
            return keyboard.KeyCode.from_char(raw_key.split(":", 1)[1])
        if raw_key.startswith("vk:"):
            return keyboard.KeyCode(vk=int(raw_key.split(":", 1)[1]))

        if raw_key.startswith("keyboard.Key."):
            return getattr(keyboard.Key, raw_key.split(".")[-1])
        if raw_key.startswith("keyboard.KeyCode.from_char("):
            char_match = re.search(r"from_char\('(.*)'\)", raw_key)
            if char_match:
                return keyboard.KeyCode.from_char(char_match.group(1))
        if raw_key.startswith("keyboard.KeyCode(vk="):
            vk_match = re.search(r"vk=(\d+)", raw_key)
            if vk_match:
                return keyboard.KeyCode(vk=int(vk_match.group(1)))
        if raw_key.startswith("'") and raw_key.endswith("'") and len(raw_key) == 3:
            return keyboard.KeyCode.from_char(raw_key[1])
    except Exception:
        return default

    return default


def mode_switch_for_key(key) -> str | None:
    char = getattr(key, "char", None)
    if char in {"1", "2", "3"}:
        mode_number = char
    else:
        vk = getattr(key, "vk", None)
        vk_map = {
            49: "1",
            50: "2",
            51: "3",
            97: "1",
            98: "2",
            99: "3",
        }
        mode_number = vk_map.get(vk)

    mode_map = {
        "1": "pure",
        "2": "context",
        "3": "reasoning",
    }
    return mode_map.get(mode_number)


class HotkeyWorker(QObject):
    ptt_pressed_signal = Signal()
    ptt_released_signal = Signal()
    mode_switch_signal = Signal(str)
    error_signal = Signal(str)
    key_captured_signal = Signal(object, str)

    def __init__(self, ptt_key_str=None, capture_mode=False, parent=None):
        super().__init__(parent)
        self._is_running = False
        self.listener = None
        self.ptt_key_str = ptt_key_str
        self.capture_mode = capture_mode
        self.ptt_key = None
        self._ctrl_pressed = False
        if not self.capture_mode:
            self._parse_keys()

    @staticmethod
    def _safe_emit(signal, *args):
        try:
            signal.emit(*args)
        except RuntimeError:
            return

    def _emit_error(self, message: str):
        self._safe_emit(self.error_signal, message)

    def _parse_keys(self):
        default_ptt = keyboard.Key.shift_r
        self.ptt_key = deserialize_key(self.ptt_key_str, default=default_ptt)

    def _on_press(self, key):
        if not self._is_running:
            return False
        if self.capture_mode:
            try:
                self._safe_emit(self.key_captured_signal, key, serialize_key(key))
                return False
            except Exception as exc:
                self._emit_error(f"Error capturing key: {exc}")
                return False

        try:
            if key in {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}:
                self._ctrl_pressed = True

            if self._ctrl_pressed and isinstance(key, keyboard.KeyCode):
                prompt_mode = mode_switch_for_key(key)
                if prompt_mode:
                    self._safe_emit(self.mode_switch_signal, prompt_mode)

            if key == self.ptt_key:
                self._safe_emit(self.ptt_pressed_signal)
        except Exception as exc:
            self._emit_error(f"Hotkey press error: {exc}")
        return None

    def _on_release(self, key):
        if not self._is_running:
            return False
        if self.capture_mode:
            return False
        try:
            if key in {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}:
                self._ctrl_pressed = False
            if key == self.ptt_key:
                self._safe_emit(self.ptt_released_signal)
        except Exception as exc:
            self._emit_error(f"Hotkey release error: {exc}")
        return None

    def start_listening(self):
        if self.listener and self.listener.is_alive():
            return
        self._is_running = True
        if not self.capture_mode:
            self._parse_keys()
        try:
            self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self.listener.daemon = True
            self.listener.start()
        except Exception as exc:
            self._emit_error(f"Failed to start listener: {exc}")
            self._is_running = False
            self.listener = None

    def stop_listening(self):
        if not self._is_running and not self.listener:
            return
        self._is_running = False
        self._ctrl_pressed = False
        listener = self.listener
        self.listener = None
        try:
            if listener:
                listener.stop()
                if listener.is_alive():
                    listener.join(timeout=1.0)
        except Exception as exc:
            self._emit_error(f"Error stopping hotkey listener: {exc}")
