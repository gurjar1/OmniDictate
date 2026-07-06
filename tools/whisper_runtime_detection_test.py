from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines import runtime_detection


class WhisperRuntimeDetectionTest(unittest.TestCase):
    def test_ctranslate2_cuda_detection_does_not_require_torch(self):
        fake_ctranslate2 = SimpleNamespace(
            get_cuda_device_count=lambda: 1,
            get_supported_compute_types=lambda device: {"float16", "int8"} if device == "cuda" else {"int8"},
        )

        with patch.dict(sys.modules, {"ctranslate2": fake_ctranslate2, "torch": None}):
            self.assertTrue(runtime_detection.ctranslate2_cuda_is_available())
            self.assertTrue(runtime_detection.whisper_cuda_is_available())
            self.assertEqual(runtime_detection.ctranslate2_supported_compute_types("cuda"), {"float16", "int8"})

    def test_whisper_cuda_detection_falls_back_to_torch_probe(self):
        fake_ctranslate2 = SimpleNamespace(get_cuda_device_count=lambda: 0)
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True))

        with patch.dict(sys.modules, {"ctranslate2": fake_ctranslate2, "torch": fake_torch}):
            self.assertFalse(runtime_detection.ctranslate2_cuda_is_available())
            self.assertTrue(runtime_detection.whisper_cuda_is_available())

    def test_ctranslate2_probe_fails_closed(self):
        fake_ctranslate2 = SimpleNamespace(get_cuda_device_count=lambda: (_ for _ in ()).throw(RuntimeError("boom")))

        with patch.dict(sys.modules, {"ctranslate2": fake_ctranslate2, "torch": None}):
            self.assertFalse(runtime_detection.ctranslate2_cuda_is_available())
            self.assertFalse(runtime_detection.whisper_cuda_is_available())


if __name__ == "__main__":
    unittest.main(verbosity=2)
