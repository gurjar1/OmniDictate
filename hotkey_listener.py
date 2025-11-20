# hotkey_listener.py

import threading
from pynput import keyboard
from PySide6.QtCore import QObject, Signal

class HotkeyWorker(QObject):
    """Listens for global hotkeys in a separate thread."""
    ptt_pressed_signal = Signal()
    ptt_released_signal = Signal()
    error_signal = Signal(str)
    key_captured_signal = Signal(object, str)

    def __init__(self, ptt_key_str=None, capture_mode=False, parent=None):
        super().__init__(parent)
        self._is_running = False
        self.listener_thread = None
        self.listener = None
        self.ptt_key_str = ptt_key_str
        self.capture_mode = capture_mode
        self.ptt_key = None
        if not self.capture_mode: self._parse_keys()
        print(f"Hotkey Listener Init: CaptureMode={self.capture_mode}, PTT='{self.ptt_key_str}'")

    def _parse_keys(self):
        default_ptt = keyboard.Key.shift_r
        
        # Parse PTT Key
        if self.ptt_key_str:
            try: 
                self.ptt_key = eval(self.ptt_key_str, {"keyboard": keyboard, "Key": keyboard.Key, "KeyCode": keyboard.KeyCode})
            except Exception as e: 
                error_msg = f"Error parsing PTT key '{self.ptt_key_str}': {e}. Using default."
                print(error_msg); self.error_signal.emit(error_msg); self.ptt_key = default_ptt
        else: 
            self.ptt_key = default_ptt
            
        print(f"Hotkey Listener Parsed: PTT Key = {self.ptt_key}")

    def key_to_string(self, key):
        if isinstance(key, keyboard.Key): return f'keyboard.Key.{key.name}'
        elif isinstance(key, keyboard.KeyCode):
            if key.char:
                if hasattr(key, 'vk') and ( (48 <= key.vk <= 57) or (65 <= key.vk <= 90) ): return f"keyboard.KeyCode.from_char('{key.char}')"
                else: return f"keyboard.KeyCode.from_char('{key.char}')"
            elif hasattr(key, 'vk'): return f'keyboard.KeyCode(vk={key.vk})'
        return str(key)

    def _on_press(self, key):
        if not self._is_running: return False
        if self.capture_mode:
            try: 
                key_str = self.key_to_string(key)
                print(f"Captured Key: {key}, String: {key_str}")
                self.key_captured_signal.emit(key, key_str)
                return False
            except Exception as e: 
                error_msg = f"Error capturing key: {e}"
                print(error_msg); self.error_signal.emit(error_msg); return False
        else:
            try:
                if key == self.ptt_key: self.ptt_pressed_signal.emit()
            except Exception: pass

    def _on_release(self, key):
        if not self._is_running: return False
        if self.capture_mode: return False
        try:
            if key == self.ptt_key: self.ptt_released_signal.emit()
        except Exception as e: print(f"Error in on_release: {e}")

    def start_listening(self):
        if self.listener_thread and self.listener_thread.is_alive(): return
        print(f"Starting hotkey listener (Capture Mode: {self.capture_mode})...")
        self._is_running = True
        if not self.capture_mode: self._parse_keys()
        try:
            self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self.listener_thread = threading.Thread(target=self.listener.run, daemon=True)
            self.listener_thread.start(); print("Hotkey listener started.")
        except Exception as e: 
            error_msg = f"Failed to start listener: {e}"
            print(error_msg); self.error_signal.emit(error_msg); self._is_running = False

    def stop_listening(self):
        if not self._is_running and not self.listener: return
        self._is_running = False
        try:
            if self.listener: keyboard.Listener.stop(self.listener)
            if self.listener_thread and self.listener_thread.is_alive(): self.listener_thread.join(timeout=0.5)
        except Exception as e: print(f"Error stopping hotkey listener: {e}")
        finally: self.listener = None; self.listener_thread = None
