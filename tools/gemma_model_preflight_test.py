from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import gemma_model_preflight


class GemmaModelPreflightTest(unittest.TestCase):
    def test_directory_summary_detects_missing_and_safetensors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_dir = Path(temp_dir) / "gemma-4-E4B-it"

            missing = gemma_model_preflight._directory_summary(model_dir)
            self.assertFalse(missing["exists"])
            self.assertEqual(missing["files"], 0)
            self.assertFalse(missing["has_safetensors"])

            model_dir.mkdir()
            (model_dir / "model.safetensors").write_bytes(b"fake")
            present = gemma_model_preflight._directory_summary(model_dir)

        self.assertTrue(present["exists"])
        self.assertEqual(present["files"], 1)
        self.assertEqual(present["bytes"], 4)
        self.assertTrue(present["has_safetensors"])

    def test_require_local_fails_and_writes_boundary_report_when_weights_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "e4b-preflight.json"
            original_argv = sys.argv
            sys.argv = [
                "gemma_model_preflight.py",
                "--model",
                "google/gemma-4-E4B-it",
                "--model-storage",
                temp_dir,
                "--require-local",
                "--report-json",
                str(report_path),
            ]
            try:
                with patch.object(
                    gemma_model_preflight,
                    "_transformers_summary",
                    return_value={
                        "available": True,
                        "version": "test-transformers",
                        "processor_class": "AutoProcessor",
                        "model_class": "AutoModelForMultimodalLM",
                    },
                ), patch.object(
                    gemma_model_preflight,
                    "_torch_summary",
                    return_value={
                        "available": True,
                        "version": "test-torch",
                        "cuda_available": True,
                        "cuda_devices": [{"index": 0, "name": "test-gpu", "total_memory_bytes": 123}],
                    },
                ):
                    rc = gemma_model_preflight.main()
            finally:
                sys.argv = original_argv

            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 1)
        self.assertEqual(payload["model"], "google/gemma-4-E4B-it")
        self.assertFalse(payload["local_summary"]["exists"])
        self.assertFalse(payload["local_summary"]["has_safetensors"])
        self.assertEqual(payload["transformers"]["model_class"], "AutoModelForMultimodalLM")
        self.assertTrue(payload["torch"]["cuda_available"])
        self.assertIn("gemma_smoke_test.py", payload["recommended_hybrid_command"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
