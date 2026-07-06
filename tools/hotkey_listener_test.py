from __future__ import annotations

import sys
import unittest
from pathlib import Path

from pynput import keyboard

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hotkey_listener import deserialize_key, mode_switch_for_key, serialize_key


class HotkeyListenerTest(unittest.TestCase):
    def test_serialized_special_key_round_trips(self):
        raw_key = serialize_key(keyboard.Key.shift_r)

        self.assertEqual(deserialize_key(raw_key), keyboard.Key.shift_r)

    def test_mode_switch_accepts_character_keys(self):
        self.assertEqual(mode_switch_for_key(keyboard.KeyCode.from_char("1")), "pure")
        self.assertEqual(mode_switch_for_key(keyboard.KeyCode.from_char("2")), "context")
        self.assertEqual(mode_switch_for_key(keyboard.KeyCode.from_char("3")), "reasoning")

    def test_mode_switch_accepts_windows_virtual_key_codes(self):
        self.assertEqual(mode_switch_for_key(keyboard.KeyCode(vk=49)), "pure")
        self.assertEqual(mode_switch_for_key(keyboard.KeyCode(vk=50)), "context")
        self.assertEqual(mode_switch_for_key(keyboard.KeyCode(vk=51)), "reasoning")

    def test_mode_switch_accepts_numpad_virtual_key_codes(self):
        self.assertEqual(mode_switch_for_key(keyboard.KeyCode(vk=97)), "pure")
        self.assertEqual(mode_switch_for_key(keyboard.KeyCode(vk=98)), "context")
        self.assertEqual(mode_switch_for_key(keyboard.KeyCode(vk=99)), "reasoning")


if __name__ == "__main__":
    unittest.main(verbosity=2)
