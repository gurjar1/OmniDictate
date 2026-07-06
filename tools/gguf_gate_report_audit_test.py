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

from tools.gguf_gate_report_audit import audit_reports
from tools.whisper_fixture_test import DEFAULT_PHRASE


def _probe_report() -> dict:
    return {
        "url": "http://127.0.0.1:8080/v1",
        "base_url": "http://127.0.0.1:8080/v1",
        "requested_model": "",
        "selected_model": "local-mm-gguf",
        "no_image": False,
        "models": ["local-mm-gguf"],
        "status": "passed",
        "response_text": "text and image input received",
        "error": "",
    }


def _smoke_report() -> dict:
    return {
        "runtime": "gguf-server",
        "model": "google/gemma-4-E2B-it",
        "quantization": "4-bit",
        "audio_mode": "hybrid-whisper",
        "whisper_model": "tiny",
        "gguf_url": "http://127.0.0.1:8080/v1",
        "gguf_model": "",
        "audio": "smoke_test_assets/gemma_live_smoke.wav",
        "image": "smoke_test_assets/gemma_live_smoke.png",
        "expected": DEFAULT_PHRASE,
        "min_word_ratio": 0.6,
        "backend_load_success": True,
        "backend_status": "Connected to GGUF server",
        "backend_warnings": [],
        "status": "passed",
        "text": DEFAULT_PHRASE,
        "execution_label": "Whisper -> GGUF server",
        "used_visual_context": True,
        "latency_seconds": 1.2,
        "result_warnings": [],
        "error": "",
    }


class GGUFRealServerGateReportAuditTest(unittest.TestCase):
    def test_valid_real_server_reports_close_gate(self):
        self.assertEqual(audit_reports(_probe_report(), _smoke_report(), "LM Studio"), [])

    def test_mock_label_does_not_close_gate(self):
        failures = audit_reports(_probe_report(), _smoke_report(), "mock server")

        self.assertIn("server implementation must be a named real server, not a mock", failures)

    def test_probe_only_or_mismatched_backend_report_does_not_close_gate(self):
        smoke = _smoke_report()
        smoke["gguf_url"] = "http://127.0.0.1:9999/v1"
        smoke["execution_label"] = "Whisper only"
        smoke["used_visual_context"] = False
        smoke["text"] = "unrelated"

        failures = audit_reports(_probe_report(), smoke, "llama.cpp")

        self.assertIn("GGUF backend smoke URL does not match the direct probe base_url", failures)
        self.assertIn("GGUF backend smoke did not use the GGUF server refinement route", failures)
        self.assertIn("GGUF backend smoke did not use visual context", failures)
        self.assertIn("GGUF backend smoke text does not meet the word-match threshold", failures)

    def test_cli_reports_failure_for_failed_probe(self):
        probe = _probe_report()
        probe["status"] = "failed"
        probe["error"] = "connection refused"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            probe_path = temp_path / "probe.json"
            smoke_path = temp_path / "smoke.json"
            probe_path.write_text(json.dumps(probe), encoding="utf-8")
            smoke_path.write_text(json.dumps(_smoke_report()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "gguf_gate_report_audit.py"),
                    "--probe-report",
                    str(probe_path),
                    "--smoke-report",
                    str(smoke_path),
                    "--server-implementation",
                    "LM Studio",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("direct probe report did not pass", result.stdout)
        self.assertIn("direct probe report contains an error", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
