from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import external_gate_closure_audit
from tools.gemma_e4b_gate_report_audit import E4B_MODEL
from tools.whisper_fixture_test import DEFAULT_PHRASE


def _capture_report() -> dict:
    return {
        "peak": 0.08,
        "clipping_ratio": 0.0,
        "transcript": DEFAULT_PHRASE,
        "prompted": True,
        "expected": DEFAULT_PHRASE,
        "device": "Microphone (Realtek(R) Audio)",
    }


def _loop_report() -> dict:
    return {
        "device": "Microphone (Realtek(R) Audio)",
        "outcome": "passed",
        "expected": DEFAULT_PHRASE,
        "results": [
            {"mode": "vad", "transcript": DEFAULT_PHRASE},
            {"mode": "ptt", "transcript": DEFAULT_PHRASE},
        ],
        "errors": [],
    }


def _e4b_preflight() -> dict:
    return {
        "model": E4B_MODEL,
        "local_summary": {"exists": True, "files": 2, "bytes": 123, "has_safetensors": True},
        "transformers": {"available": True, "model_class": "AutoModelForMultimodalLM"},
        "torch": {"available": True},
    }


def _e4b_smoke() -> dict:
    return {
        "status": "passed",
        "runtime": "transformers",
        "model": E4B_MODEL,
        "audio_mode": "hybrid-whisper",
        "backend_load_success": True,
        "execution_label": "Whisper -> Gemma",
        "used_visual_context": True,
        "text": DEFAULT_PHRASE,
        "error": "",
    }


def _gguf_probe() -> dict:
    return {
        "status": "passed",
        "base_url": "http://127.0.0.1:8080/v1",
        "selected_model": "local-mm-gguf",
        "response_text": "ok",
        "error": "",
    }


def _gguf_smoke() -> dict:
    return {
        "status": "passed",
        "runtime": "gguf-server",
        "gguf_url": "http://127.0.0.1:8080/v1",
        "backend_load_success": True,
        "execution_label": "Whisper -> GGUF server",
        "used_visual_context": True,
        "text": DEFAULT_PHRASE,
        "error": "",
    }


class ExternalGateClosureAuditTest(unittest.TestCase):
    def test_current_audit_reports_physical_proven_and_experimental_missing_evidence(self):
        status, failures, payload = external_gate_closure_audit.build_closure_audit()

        self.assertEqual(status, "passed")
        self.assertEqual(failures, [])
        self.assertEqual(payload["eligible_for_proven"], ["physical-microphone"])
        self.assertEqual(
            [row["closure_state"] for row in payload["gate_rows"]],
            ["eligible-for-proven", "missing-evidence", "missing-evidence"],
        )

    def test_all_valid_reports_are_eligible_for_proven(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            microphone = root / "smoke_test_assets" / "microphone"
            gguf = root / "smoke_test_assets" / "gguf"
            microphone.mkdir(parents=True)
            gguf.mkdir(parents=True)
            (microphone / "spoken-phrase-large-v3-turbo-report.json").write_text(json.dumps(_capture_report()), encoding="utf-8")
            (microphone / "live-loop-large-v3-turbo-report.json").write_text(json.dumps(_loop_report()), encoding="utf-8")
            (root / "smoke_test_assets" / "gemma-e4b-preflight.json").write_text(json.dumps(_e4b_preflight()), encoding="utf-8")
            (root / "smoke_test_assets" / "gemma-e4b-live-smoke.json").write_text(json.dumps(_e4b_smoke()), encoding="utf-8")
            (gguf / "real-server-probe.json").write_text(json.dumps(_gguf_probe()), encoding="utf-8")
            (gguf / "real-server-smoke.json").write_text(json.dumps(_gguf_smoke()), encoding="utf-8")

            with mock.patch.object(external_gate_closure_audit, "ROOT", root):
                status, failures, payload = external_gate_closure_audit.build_closure_audit()

        self.assertEqual(status, "passed")
        self.assertEqual(failures, [])
        self.assertEqual(
            payload["eligible_for_proven"],
            ["physical-microphone", "gemma-e4b-live", "gguf-real-server"],
        )
        self.assertTrue(all(row["scope_decision_target"] == "proven" for row in payload["gate_rows"]))

    def test_cli_writes_report_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "external-gate-closure-audit.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "external_gate_closure_audit.py"),
                    "--json",
                    "--report-json",
                    str(report),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertIn("missing-evidence", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
