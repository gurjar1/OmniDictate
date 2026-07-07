from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines import runtime_detection
from engines.whisper_backend import _build_runtime_diagnostics, _runtime_requirement_hint


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

    def test_ctranslate2_runtime_probe_records_cuda_errors(self):
        fake_ctranslate2 = SimpleNamespace(
            __version__="4.5.0",
            get_cuda_device_count=lambda: (_ for _ in ()).throw(RuntimeError("missing cudnn")),
        )

        with patch.dict(sys.modules, {"ctranslate2": fake_ctranslate2}):
            payload = runtime_detection.ctranslate2_runtime_probe()

        self.assertTrue(payload["available"])
        self.assertEqual(payload["version"], "4.5.0")
        self.assertIn("missing cudnn", payload["error"])

    def test_runtime_requirement_hint_is_version_aware(self):
        self.assertIn("cuDNN 9", _runtime_requirement_hint("4.5.0"))
        self.assertIn("cuDNN 8", _runtime_requirement_hint("4.4.0"))

    def test_cpu_diagnostics_are_plain_language_and_actionable(self):
        fake_ctranslate2 = SimpleNamespace(
            __version__="4.5.0",
            get_cuda_device_count=lambda: 0,
        )

        with patch.dict(sys.modules, {"ctranslate2": fake_ctranslate2}):
            diagnostics = _build_runtime_diagnostics(
                model_name="large-v3-turbo",
                loaded_device="cpu",
                loaded_compute_type="int8",
                warnings=[],
            )

        self.assertEqual(diagnostics.status, "cpu-mode")
        self.assertIn("CPU mode", diagnostics.headline)
        self.assertTrue(any("NVIDIA GPU" in step for step in diagnostics.next_steps))
        self.assertTrue(any("CUDA" in step for step in diagnostics.next_steps))
        self.assertGreaterEqual(len(diagnostics.actions), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
