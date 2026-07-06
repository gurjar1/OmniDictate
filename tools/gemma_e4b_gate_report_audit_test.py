from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.gemma_e4b_gate_report_audit import E4B_MODEL, audit_reports
from tools.whisper_fixture_test import DEFAULT_PHRASE


def _preflight_report() -> dict:
    return {
        "model": E4B_MODEL,
        "model_storage": "smoke_test_assets/models",
        "local_dir": "smoke_test_assets/models/gemma-4-E4B-it",
        "resolved_reference": "smoke_test_assets/models/gemma-4-E4B-it",
        "local_summary": {"exists": True, "files": 3, "bytes": 123456, "has_safetensors": True},
        "transformers": {
            "available": True,
            "version": "test-transformers",
            "processor_class": "AutoProcessor",
            "model_class": "AutoModelForMultimodalLM",
        },
        "torch": {"available": True, "version": "test-torch", "cuda_available": True, "cuda_devices": []},
        "model_kwargs_keys": ["device_map", "local_files_only", "quantization_config"],
        "warnings": [],
    }


def _smoke_report() -> dict:
    return {
        "runtime": "transformers",
        "model": E4B_MODEL,
        "quantization": "4-bit",
        "audio_mode": "hybrid-whisper",
        "whisper_model": "tiny",
        "gguf_url": "http://127.0.0.1:8080/v1",
        "gguf_model": "",
        "audio": "smoke_test_assets/gemma_live_smoke.wav",
        "image": "smoke_test_assets/gemma_live_smoke.png",
        "expected": DEFAULT_PHRASE,
        "min_word_ratio": 0.75,
        "backend_load_success": True,
        "backend_status": "Gemma model loaded",
        "backend_warnings": [],
        "status": "passed",
        "text": DEFAULT_PHRASE,
        "execution_label": "Whisper -> Gemma",
        "used_visual_context": True,
        "latency_seconds": 4.2,
        "result_warnings": [],
        "error": "",
    }


class GemmaE4BGateReportAuditTest(unittest.TestCase):
    def test_valid_e4b_reports_close_gate(self):
        self.assertEqual(audit_reports(_preflight_report(), _smoke_report()), [])

    def test_missing_weights_do_not_close_gate(self):
        preflight = _preflight_report()
        preflight["local_summary"] = {"exists": False, "files": 0, "bytes": 0, "has_safetensors": False}

        failures = audit_reports(preflight, _smoke_report())

        self.assertIn("preflight report does not prove local E4B directory exists", failures)
        self.assertIn("preflight report does not prove local E4B safetensors exist", failures)
        self.assertIn("preflight report local E4B weights have zero bytes", failures)

    def test_non_hybrid_or_mismatched_smoke_does_not_close_gate(self):
        smoke = _smoke_report()
        smoke["audio_mode"] = "native-audio"
        smoke["execution_label"] = "Native Gemma audio"
        smoke["used_visual_context"] = False
        smoke["text"] = "unrelated"

        failures = audit_reports(_preflight_report(), smoke)

        self.assertIn("E4B release gate requires the hybrid-whisper path", failures)
        self.assertIn("E4B live smoke did not use the Whisper -> Gemma route", failures)
        self.assertIn("E4B live smoke did not use visual context", failures)
        self.assertIn("E4B live smoke text does not meet the word-match threshold", failures)

    def test_cli_reports_failed_smoke(self):
        smoke = _smoke_report()
        smoke["status"] = "failed"
        smoke["error"] = "RuntimeError: out of memory"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            preflight_path = temp_path / "preflight.json"
            smoke_path = temp_path / "smoke.json"
            preflight_path.write_text(json.dumps(_preflight_report()), encoding="utf-8")
            smoke_path.write_text(json.dumps(smoke), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "gemma_e4b_gate_report_audit.py"),
                    "--preflight-report",
                    str(preflight_path),
                    "--smoke-report",
                    str(smoke_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("E4B live smoke report did not pass", result.stdout)
        self.assertIn("E4B live smoke report contains an error", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
