from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from types import SimpleNamespace
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import live_microphone_smoke, microphone_capture_diagnostic, open_gate_summary


class _FakeSink:
    statuses = ["Listening...", "Recording (VAD)...", "Transcribing..."]
    errors: list[str] = []
    transcripts = ["hello world this is a simple speech test"]


class _FakeApp:
    def __init__(self):
        self.processed_events = 0

    def processEvents(self):
        self.processed_events += 1
        return None


class _FakePttWorker:
    def __init__(self, sink: _FakeSink | None = None):
        self.sink = sink
        self.vad_enabled: list[bool] = []
        self.ptt_states: list[bool] = []

    def set_vad_enabled(self, enabled: bool):
        self.vad_enabled.append(enabled)

    def set_ptt_state(self, is_pressed: bool):
        self.ptt_states.append(is_pressed)
        if not is_pressed and self.sink is not None:
            self.sink.transcripts.append("hello world this is a simple speech test")


class MicrophoneEvidenceToolingTest(unittest.TestCase):
    def test_live_microphone_report_contains_per_mode_evidence(self):
        args = argparse.Namespace(
            model="large-v3-turbo",
            mode="both",
            manual=True,
            countdown=3.0,
            device="Microphone (Realtek(R) Audio)",
            capture_only=False,
            expected="hello world this is a simple speech test",
            min_word_ratio=0.6,
            max_transcripts=1,
        )
        results = [
            {"mode": "vad", "transcript": "hello world this is a simple speech test"},
            {"mode": "ptt", "transcript": "hello world this is a simple speech test"},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "live-loop-report.json"

            live_microphone_smoke._write_report(report_path, args, results, _FakeSink())

            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["model"], "large-v3-turbo")
        self.assertEqual(payload["mode"], "both")
        self.assertTrue(payload["manual"])
        self.assertEqual(payload["countdown"], 3.0)
        self.assertEqual(payload["device"], "Microphone (Realtek(R) Audio)")
        self.assertEqual(payload["expected"], args.expected)
        self.assertEqual(payload["max_transcripts"], 1)
        self.assertEqual(payload["outcome"], "passed")
        self.assertEqual(payload["failure"], "")
        self.assertEqual(payload["failed_mode"], "")
        self.assertEqual(payload["results"], results)
        self.assertEqual(payload["transcripts"], _FakeSink.transcripts)
        self.assertIn("Listening...", payload["statuses"])
        self.assertEqual(payload["errors"], [])

    def test_live_microphone_failed_report_records_mode_and_transcripts(self):
        args = argparse.Namespace(
            model="tiny",
            mode="both",
            manual=False,
            countdown=3.0,
            device="",
            capture_only=False,
            expected="hello world this is a simple speech test",
            min_word_ratio=0.6,
            max_transcripts=1,
        )
        sink = _FakeSink()
        sink.transcripts = ["We're open to the world."]

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "live-loop-failed-report.json"

            live_microphone_smoke._write_report(
                report_path,
                args,
                [],
                sink,
                outcome="failed",
                failure="AssertionError: Transcript did not match",
                failed_mode="vad",
            )

            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["outcome"], "failed")
        self.assertEqual(payload["failed_mode"], "vad")
        self.assertIn("Transcript did not match", payload["failure"])
        self.assertEqual(payload["transcripts"], ["We're open to the world."])
        self.assertEqual(payload["results"], [])

    def test_mismatched_transcript_fails_after_configured_attempts(self):
        sink = _FakeSink()
        sink.transcripts = ["We're open to the world."]

        with self.assertRaisesRegex(AssertionError, "after 1 attempt"):
            live_microphone_smoke._wait_for_transcript(
                sink,
                "hello world this is a simple speech test",
                0.6,
                10,
                _FakeApp(),
                0,
                max_transcripts=1,
            )

    def test_apply_input_device_preserves_default_output_device(self):
        class _Default:
            device = [1, 3]

        fake_sounddevice = SimpleNamespace(default=_Default())
        original = sys.modules.get("sounddevice")
        sys.modules["sounddevice"] = fake_sounddevice
        try:
            live_microphone_smoke._apply_input_device("Microphone (Realtek(R) Audio)")
        finally:
            if original is None:
                del sys.modules["sounddevice"]
            else:
                sys.modules["sounddevice"] = original

        self.assertEqual(fake_sounddevice.default.device, ("Microphone (Realtek(R) Audio)", 3))

    def test_apply_input_device_converts_numeric_string_to_index(self):
        class _Default:
            device = [1, 3]

        fake_sounddevice = SimpleNamespace(default=_Default())
        original = sys.modules.get("sounddevice")
        sys.modules["sounddevice"] = fake_sounddevice
        try:
            live_microphone_smoke._apply_input_device("8")
        finally:
            if original is None:
                del sys.modules["sounddevice"]
            else:
                sys.modules["sounddevice"] = original

        self.assertEqual(fake_sounddevice.default.device, (8, 3))

    def test_capture_device_arg_converts_numeric_string_to_index(self):
        self.assertEqual(microphone_capture_diagnostic._sounddevice_device_arg("1"), 1)
        self.assertEqual(
            microphone_capture_diagnostic._sounddevice_device_arg("Microphone (Realtek(R) Audio)"),
            "Microphone (Realtek(R) Audio)",
        )
        self.assertIsNone(microphone_capture_diagnostic._sounddevice_device_arg(""))

    def test_microphone_device_inventory_lists_input_capable_devices(self):
        class _DevicePair:
            def __iter__(self):
                return iter([1, 3])

        class _Default:
            device = _DevicePair()

        devices = [
            {"name": "Speaker", "hostapi": 0, "max_input_channels": 0, "default_samplerate": 48000.0},
            {"name": "Microphone (Realtek(R) Audio)", "hostapi": 0, "max_input_channels": 2, "default_samplerate": 44100.0},
            {"name": "USB Microphone", "hostapi": 1, "max_input_channels": 1, "default_samplerate": 16000.0},
        ]

        def query_devices(kind=None):
            if kind == "input":
                return devices[1]
            return devices

        fake_sounddevice = SimpleNamespace(default=_Default(), query_devices=query_devices)

        payload = microphone_capture_diagnostic._device_inventory(fake_sounddevice)

        self.assertEqual(payload["kind"], "audio-device-inventory")
        self.assertEqual(payload["default_devices"], [1, 3])
        self.assertEqual(payload["default_input_name"], "Microphone (Realtek(R) Audio)")
        self.assertEqual(payload["recommended_device_argument"], "1")
        self.assertEqual(payload["recommended_device"]["name"], "Microphone (Realtek(R) Audio)")
        self.assertEqual(payload["duplicate_input_names"], [])
        self.assertEqual([device["name"] for device in payload["input_devices"]], [
            "Microphone (Realtek(R) Audio)",
            "USB Microphone",
        ])
        self.assertEqual(payload["input_devices"][0]["index"], 1)

    def test_microphone_device_inventory_flags_duplicate_input_names(self):
        class _Default:
            device = [1, 3]

        devices = [
            {"name": "Microphone", "hostapi": 0, "max_input_channels": 2, "default_samplerate": 44100.0},
            {"name": "Microphone", "hostapi": 1, "max_input_channels": 2, "default_samplerate": 48000.0},
        ]

        def query_devices(kind=None):
            if kind == "input":
                return devices[1]
            return devices

        fake_sounddevice = SimpleNamespace(default=_Default(), query_devices=query_devices)

        payload = microphone_capture_diagnostic._device_inventory(fake_sounddevice)

        self.assertEqual(payload["recommended_device_argument"], "1")
        self.assertEqual(payload["duplicate_input_names"], ["Microphone"])

    def test_manual_prompt_prints_expected_phrase_and_countdown(self):
        output = io.StringIO()

        with redirect_stdout(output):
            live_microphone_smoke._manual_prompt("hello world", "VAD", 0)

        text = output.getvalue()
        self.assertIn("VAD: speak this phrase when prompted:", text)
        self.assertIn("hello world", text)
        self.assertIn("VAD: speak now.", text)

    def test_ptt_manual_window_pumps_events_while_pressed(self):
        args = argparse.Namespace(
            expected="hello world this is a simple speech test",
            manual=True,
            countdown=0,
            timeout=0.1,
            capture_only=True,
            min_word_ratio=0.6,
            max_transcripts=1,
        )
        sink = _FakeSink()
        sink.transcripts = []
        app = _FakeApp()
        worker = _FakePttWorker(sink)

        transcript = live_microphone_smoke._run_ptt(worker, sink, args, app)

        self.assertEqual(transcript, "hello world this is a simple speech test")
        self.assertEqual(worker.vad_enabled, [False])
        self.assertEqual(worker.ptt_states, [True, False])
        self.assertGreater(app.processed_events, 0)

    def test_open_gate_summary_keeps_full_physical_microphone_sequence(self):
        physical_gate = next(gate for gate in open_gate_summary.OPEN_GATES if gate.key == "physical-microphone")

        self.assertEqual(len(physical_gate.next_command), 1)
        self.assertIn("physical_microphone_gate.py", physical_gate.next_command[0])
        self.assertIn("--model large-v3-turbo", physical_gate.next_command[0])
        self.assertIn("--report-json smoke_test_assets\\microphone\\physical-gate-report.json", physical_gate.next_command[0])

    def test_open_gate_summary_prints_then_steps(self):
        output = io.StringIO()
        original_argv = sys.argv
        sys.argv = ["open_gate_summary.py", "--strict"]
        try:
            with redirect_stdout(output):
                rc = open_gate_summary.main()
        finally:
            sys.argv = original_argv

        text = output.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("Next: .\\venv\\Scripts\\python.exe tools\\physical_microphone_gate.py", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
