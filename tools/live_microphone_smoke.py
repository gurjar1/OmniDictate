from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, Slot

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from app_settings import AppSettings
from core_logic import DictationWorker
from engines.context_capture import VisualContextManager
from whisper_fixture_test import DEFAULT_PHRASE, assert_transcript_matches, normalize_words


class _WorkerSink(QObject):
    def __init__(self):
        super().__init__()
        self.transcripts: list[str] = []
        self.statuses: list[str] = []
        self.errors: list[str] = []

    @Slot(str)
    def on_transcription(self, text: str) -> None:
        print(f"Transcript: {text}")
        self.transcripts.append(text)

    @Slot(str)
    def on_status(self, text: str) -> None:
        print(f"Status: {text}")
        self.statuses.append(text)

    @Slot(str)
    def on_error(self, text: str) -> None:
        print(f"Error: {text}")
        self.errors.append(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify OmniDictate can capture physical microphone audio in VAD and/or PTT mode."
    )
    parser.add_argument("--model", default="tiny", help="Whisper model to load for the live mic smoke.")
    parser.add_argument("--mode", choices=["vad", "ptt", "both"], default="both")
    parser.add_argument("--expected", default=DEFAULT_PHRASE, help="Phrase to speak or play.")
    parser.add_argument("--timeout", type=float, default=24.0, help="Seconds to wait for each transcript.")
    parser.add_argument("--min-word-ratio", type=float, default=0.6, help="Minimum expected-word match ratio.")
    parser.add_argument(
        "--max-transcripts",
        type=int,
        default=1,
        help="Maximum non-empty transcripts to compare per mode before failing. Use 0 to wait until timeout.",
    )
    parser.add_argument(
        "--capture-only",
        action="store_true",
        help="Pass when any non-empty transcript is captured. Use only for hardware capture diagnosis.",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Do not play SAPI audio. Print a prompt and wait for a human to speak the phrase.",
    )
    parser.add_argument(
        "--countdown",
        type=float,
        default=3.0,
        help="Seconds to wait after each manual prompt before asking the user to speak.",
    )
    parser.add_argument("--device", default="", help="Optional sounddevice input device index or name.")
    parser.add_argument("--report-json", default="", help="Optional path for a JSON report after pass, failure, or interruption.")
    return parser.parse_args()


def _manual_prompt(text: str, label: str, countdown: float) -> None:
    print(f"{label}: speak this phrase when prompted:")
    print(f"  {text}")
    if countdown <= 0:
        print(f"{label}: speak now.")
        return
    remaining = int(round(countdown))
    while remaining > 0:
        print(f"{label}: speak in {remaining}...")
        time.sleep(1.0)
        remaining -= 1
    print(f"{label}: speak now.")


def _play_or_prompt(text: str, manual: bool, label: str, countdown: float) -> threading.Thread | None:
    if manual:
        _manual_prompt(text, label, countdown)
        return None

    def _speak() -> None:
        import win32com.client

        voice = win32com.client.Dispatch("SAPI.SpVoice")
        voice.Speak(text)

    thread = threading.Thread(target=_speak, daemon=True)
    thread.start()
    return thread


def _sleep_with_events(app: QCoreApplication, seconds: float, sink: _WorkerSink | None = None) -> None:
    deadline = time.time() + max(0.0, seconds)
    while time.time() < deadline:
        app.processEvents()
        if sink is not None and sink.errors:
            raise RuntimeError(sink.errors[-1])
        time.sleep(0.05)


def _wait_for_transcript(
    sink: _WorkerSink,
    expected: str,
    min_word_ratio: float,
    timeout: float,
    app: QCoreApplication,
    start_index: int,
    max_transcripts: int = 1,
) -> str:
    deadline = time.time() + timeout
    last_error: AssertionError | None = None
    checked_until = start_index
    best_transcript = ""
    best_ratio = 0.0
    compared = 0
    expected_words = normalize_words(expected)
    while time.time() < deadline:
        app.processEvents()
        if sink.errors:
            raise RuntimeError(sink.errors[-1])
        for transcript in sink.transcripts[checked_until:]:
            checked_until += 1
            if not transcript.strip():
                continue
            compared += 1
            if best_transcript == "":
                best_transcript = transcript
            if expected_words:
                actual_words = set(normalize_words(transcript))
                matched = [word for word in expected_words if word in actual_words]
                ratio = len(matched) / len(expected_words)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_transcript = transcript
            try:
                assert_transcript_matches(transcript, expected, min_word_ratio)
                return transcript
            except AssertionError as exc:
                last_error = exc
                if max_transcripts > 0 and compared >= max_transcripts:
                    raise AssertionError(
                        f"Transcript did not match after {compared} attempt(s). "
                        f"Best match: {best_ratio:.0%} from {best_transcript!r}. Last error: {last_error}"
                    ) from last_error
        time.sleep(0.1)
    if last_error is not None:
        raise AssertionError(
            f"Timed out waiting for a matching transcript. "
            f"Best match: {best_ratio:.0%} from {best_transcript!r}. Last error: {last_error}"
        ) from last_error
    raise AssertionError("Timed out waiting for any transcript from physical microphone audio.")


def _run_vad(
    worker: DictationWorker,
    sink: _WorkerSink,
    args: argparse.Namespace,
    app: QCoreApplication,
) -> str:
    print("Starting VAD microphone smoke.")
    worker.set_vad_enabled(True)
    start_index = len(sink.transcripts)
    speaker = _play_or_prompt(args.expected, args.manual, "VAD", args.countdown)
    if args.capture_only:
        transcript = _wait_for_any_transcript(sink, args.timeout, app, start_index)
    else:
        transcript = _wait_for_transcript(
            sink,
            args.expected,
            args.min_word_ratio,
            args.timeout,
            app,
            start_index,
            args.max_transcripts,
        )
    if speaker is not None:
        speaker.join(timeout=2.0)
    print(f"VAD microphone smoke passed: {transcript}")
    return transcript


def _run_ptt(
    worker: DictationWorker,
    sink: _WorkerSink,
    args: argparse.Namespace,
    app: QCoreApplication,
) -> str:
    print("Starting PTT microphone smoke.")
    worker.set_vad_enabled(False)
    start_index = len(sink.transcripts)
    if args.manual:
        _manual_prompt(args.expected, "PTT", args.countdown)
        worker.set_ptt_state(True)
        print("PTT: recording now; speak clearly until recording stops.")
        _sleep_with_events(app, min(5.0, args.timeout / 2), sink)
    else:
        worker.set_ptt_state(True)
        speaker = _play_or_prompt(args.expected, False, "PTT", args.countdown)
        while speaker is not None and speaker.is_alive():
            _sleep_with_events(app, 0.1, sink)
    worker.set_ptt_state(False)
    _sleep_with_events(app, 0.2, sink)
    if args.capture_only:
        transcript = _wait_for_any_transcript(sink, args.timeout, app, start_index)
    else:
        transcript = _wait_for_transcript(
            sink,
            args.expected,
            args.min_word_ratio,
            args.timeout,
            app,
            start_index,
            args.max_transcripts,
        )
    print(f"PTT microphone smoke passed: {transcript}")
    return transcript


def _wait_for_any_transcript(
    sink: _WorkerSink,
    timeout: float,
    app: QCoreApplication,
    start_index: int,
) -> str:
    deadline = time.time() + timeout
    checked_until = start_index
    while time.time() < deadline:
        app.processEvents()
        if sink.errors:
            raise RuntimeError(sink.errors[-1])
        for transcript in sink.transcripts[checked_until:]:
            checked_until += 1
            if transcript.strip():
                return transcript
        time.sleep(0.1)
    raise AssertionError("Timed out waiting for any transcript from physical microphone audio.")


def _write_report(
    path: Path,
    args: argparse.Namespace,
    results: list[dict[str, str]],
    sink: _WorkerSink,
    outcome: str = "passed",
    failure: str = "",
    failed_mode: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": args.model,
        "mode": args.mode,
        "manual": bool(args.manual),
        "countdown": args.countdown,
        "device": args.device,
        "capture_only": bool(args.capture_only),
        "expected": args.expected,
        "min_word_ratio": args.min_word_ratio,
        "max_transcripts": args.max_transcripts,
        "outcome": outcome,
        "failure": failure,
        "failed_mode": failed_mode,
        "results": results,
        "transcripts": sink.transcripts,
        "statuses": sink.statuses,
        "errors": sink.errors,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _apply_input_device(device: str) -> None:
    if not device:
        return
    import sounddevice as sd

    selected_device: int | str
    try:
        selected_device = int(str(device).strip())
    except ValueError:
        selected_device = device

    current_default = sd.default.device
    try:
        output_device = current_default[1]
    except (TypeError, IndexError):
        output_device = None
    sd.default.device = (selected_device, output_device)


def main() -> int:
    args = parse_args()
    app = QCoreApplication.instance() or QCoreApplication([])

    try:
        import sounddevice as sd

        _apply_input_device(args.device)
        print(f"Default audio devices: {sd.default.device}")
        print(f"Default input: {sd.query_devices(kind='input')['name']}")
    except Exception as exc:
        print(f"Could not inspect default audio input: {exc}")

    settings = AppSettings(
        backend="faster-whisper",
        whisper_model=args.model,
        language="en",
        vad_enabled=True,
        silence_threshold=500,
        char_delay=0.02,
        screen_context_enabled=False,
        webcam_enabled=False,
    )
    worker = DictationWorker(
        gui_wid=0,
        app_settings=settings,
        visual_context_manager=VisualContextManager(settings),
    )
    sink = _WorkerSink()
    worker.transcription_ready.connect(sink.on_transcription)
    worker.status_updated.connect(sink.on_status)
    worker.error_occurred.connect(sink.on_error)

    try:
        worker.start_processing()
        if sink.errors:
            raise RuntimeError(sink.errors[-1])
        deadline = time.time() + args.timeout
        while "Listening..." not in sink.statuses and time.time() < deadline:
            app.processEvents()
            if sink.errors:
                raise RuntimeError(sink.errors[-1])
            time.sleep(0.1)

        modes = ["vad", "ptt"] if args.mode == "both" else [args.mode]
        results: list[dict[str, str]] = []
        failure = ""
        current_mode = ""
        try:
            for mode in modes:
                current_mode = mode
                if mode == "vad":
                    transcript = _run_vad(worker, sink, args, app)
                else:
                    transcript = _run_ptt(worker, sink, args, app)
                results.append({"mode": mode, "transcript": transcript})
                current_mode = ""
        except KeyboardInterrupt:
            print("Live microphone smoke interrupted by user.")
            if args.report_json:
                report_path = Path(args.report_json)
                _write_report(
                    report_path,
                    args,
                    results,
                    sink,
                    outcome="interrupted",
                    failure="KeyboardInterrupt",
                    failed_mode=current_mode,
                )
                print(f"Wrote report: {report_path.resolve()}")
            return 130
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
            if args.report_json:
                report_path = Path(args.report_json)
                _write_report(
                    report_path,
                    args,
                    results,
                    sink,
                    outcome="failed",
                    failure=failure,
                    failed_mode=current_mode,
                )
                print(f"Wrote report: {report_path.resolve()}")
            raise

        if args.report_json:
            report_path = Path(args.report_json)
            _write_report(report_path, args, results, sink, outcome="passed", failure=failure)
            print(f"Wrote report: {report_path.resolve()}")

        print("Live microphone smoke passed.")
        return 0
    finally:
        worker.stop_processing()
        for _ in range(20):
            app.processEvents()
            time.sleep(0.05)


if __name__ == "__main__":
    raise SystemExit(main())
