from __future__ import annotations

import argparse
import json
import os
import queue
import statistics
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import librosa

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.base import PromptMode, TargetAppContext, TranscriptionRequest, TranscriptionResult, VisualContextSnapshot
from engines.transformers_asr_backend import TransformersASRBackend
from engines.whisper_backend import WhisperBackend
from whisper_fixture_test import DEFAULT_PHRASE, normalize_words, synthesize_wav


@dataclass
class RunResult:
    text: str
    latency_seconds: float
    word_match_ratio: float


@dataclass
class BackendSummary:
    backend: str
    model: str
    runs: list[RunResult]
    median_latency_seconds: float
    best_word_match_ratio: float
    cache_path: str | None = None
    cache_file_count: int | None = None
    cache_size_bytes: int | None = None


@dataclass
class PackageBoundarySummary:
    checked: bool
    bundle_path: str
    exists: bool
    total_size_bytes: int | None
    forbidden_present: list[str]
    passed: bool


@dataclass
class ImportBoundarySummary:
    checked: bool
    returncode: int | None
    passed: bool


@dataclass
class CommandRoutingResult:
    spoken_command: str
    transcript: str
    expected_output: str
    routed_output: str | None
    passed: bool


FORBIDDEN_BASELINE_PACKAGES = [
    "accelerate",
    "av",
    "bitsandbytes",
    "cv2",
    "huggingface_hub",
    "model_downloader",
    "sentencepiece",
    "torch",
    "transformers",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark Whisper against an optional alternative STT adapter on the same fixture."
    )
    parser.add_argument("--audio", default="", help="Optional WAV/audio file. If omitted, Windows SAPI generates one.")
    parser.add_argument(
        "--audio-source",
        choices=["generated-sapi", "physical-microphone", "other-file"],
        default="",
        help="Evidence label for the audio fixture. Defaults to generated-sapi when --audio is omitted, otherwise other-file.",
    )
    parser.add_argument("--expected", default=DEFAULT_PHRASE)
    parser.add_argument("--language", default="en")
    parser.add_argument("--whisper-model", default="large-v3-turbo")
    parser.add_argument("--candidate-model", default="", help="Optional Transformers ASR model id to compare.")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--min-word-ratio", type=float, default=0.75)
    parser.add_argument("--promotion-speedup", type=float, default=0.20)
    parser.add_argument("--report-json", default="")
    parser.add_argument(
        "--whisper-package-dir",
        default="",
        help="Optional Whisper-only PyInstaller bundle to inspect for forbidden candidate runtimes.",
    )
    parser.add_argument(
        "--check-import-boundary",
        action="store_true",
        help="Run tools/import_boundary_test.py in a subprocess and record the result.",
    )
    parser.add_argument(
        "--check-command-routing",
        action="store_true",
        help="Transcribe spoken punctuation commands with the candidate and route them through the worker.",
    )
    parser.add_argument(
        "--command-check",
        action="append",
        default=[],
        metavar="COMMAND=OUTPUT",
        help='Command routing case such as "comma=,". Can be passed more than once.',
    )
    parser.add_argument("--keep-audio", action="store_true")
    return parser.parse_args()


def _word_match_ratio(actual: str, expected: str) -> float:
    expected_words = normalize_words(expected)
    actual_words = set(normalize_words(actual))
    if not expected_words:
        raise AssertionError("Expected text produced no comparable words.")
    matched = [word for word in expected_words if word in actual_words]
    return len(matched) / len(expected_words)


def _request(audio, sample_rate: int, language: str) -> TranscriptionRequest:
    return TranscriptionRequest(
        audio=audio,
        sample_rate=sample_rate,
        language=language,
        prompt_mode=PromptMode.PURE,
        visual_context=VisualContextSnapshot(),
        target_app=TargetAppContext(title="STT adapter benchmark", process_name="stt_adapter_benchmark"),
        max_new_tokens=48,
    )


def _summarize(backend_name: str, model: str, runs: list[RunResult]) -> BackendSummary:
    cache = _model_cache_summary(model) if backend_name == "transformers-asr" else None
    return BackendSummary(
        backend=backend_name,
        model=model,
        runs=runs,
        median_latency_seconds=statistics.median(run.latency_seconds for run in runs),
        best_word_match_ratio=max(run.word_match_ratio for run in runs),
        cache_path=str(cache[0]) if cache else None,
        cache_file_count=cache[1] if cache else None,
        cache_size_bytes=cache[2] if cache else None,
    )


def _model_cache_summary(model_id: str) -> tuple[Path, int, int] | None:
    cache_root = os.environ.get("HF_HUB_CACHE")
    if cache_root:
        hub_root = Path(cache_root)
    else:
        hub_root = Path.home() / ".cache" / "huggingface" / "hub"

    cache_name = "models--" + model_id.replace("/", "--")
    model_cache = hub_root / cache_name
    if not model_cache.exists():
        return None

    files = [path for path in model_cache.rglob("*") if path.is_file()]
    size = sum(path.stat().st_size for path in files)
    return model_cache, len(files), size


def _directory_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def _package_boundary_summary(bundle_arg: str) -> PackageBoundarySummary | None:
    if not bundle_arg:
        return None

    bundle = Path(bundle_arg)
    exists = bundle.exists()
    total_size = _directory_size(bundle) if exists else None
    forbidden_present: list[str] = []
    if exists:
        internal = bundle / "_internal"
        if internal.exists():
            names = {child.name.lower() for child in internal.iterdir()}
            forbidden_present = [
                package_name
                for package_name in FORBIDDEN_BASELINE_PACKAGES
                if package_name.lower() in names
            ]
        else:
            forbidden_present = ["missing _internal directory"]
    return PackageBoundarySummary(
        checked=True,
        bundle_path=str(bundle),
        exists=exists,
        total_size_bytes=total_size,
        forbidden_present=forbidden_present,
        passed=exists and not forbidden_present,
    )


def _import_boundary_summary(check_import_boundary: bool) -> ImportBoundarySummary:
    if not check_import_boundary:
        return ImportBoundarySummary(checked=False, returncode=None, passed=False)
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "import_boundary_test.py")],
        cwd=ROOT,
        check=False,
    )
    return ImportBoundarySummary(
        checked=True,
        returncode=completed.returncode,
        passed=completed.returncode == 0,
    )


def _parse_command_checks(values: list[str]) -> list[tuple[str, str]]:
    if not values:
        return [("comma", ","), ("period", ".")]
    checks: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise ValueError(f"Command check must use COMMAND=OUTPUT format: {value}")
        command, expected = value.split("=", 1)
        command = command.strip()
        if not command:
            raise ValueError(f"Command check has an empty command: {value}")
        checks.append((command, expected))
    return checks


def _run_command_routing_checks(args: argparse.Namespace) -> list[CommandRoutingResult]:
    if not args.check_command_routing or not args.candidate_model:
        return []

    from PySide6.QtCore import QCoreApplication

    from core_logic import DictationWorker
    from engines.context_capture import VisualContextManager

    app = QCoreApplication.instance() or QCoreApplication([])
    settings = AppSettings(backend="transformers-asr", alternative_stt_model=args.candidate_model, language=args.language)
    backend = TransformersASRBackend(settings)
    load_result = backend.load()
    print(f"Command-check status: {load_result.status_message}")
    if not load_result.success:
        raise RuntimeError(load_result.status_message)

    worker = DictationWorker(
        gui_wid=0,
        app_settings=settings,
        visual_context_manager=VisualContextManager(settings),
    )
    results: list[CommandRoutingResult] = []
    try:
        for command, expected_output in _parse_command_checks(args.command_check):
            audio_path = synthesize_wav(command)
            try:
                audio, sample_rate = librosa.load(audio_path, sr=16000, mono=True)
                transcription = backend.transcribe(_request(audio, sample_rate, args.language))
                worker._handle_transcription_result(
                    TranscriptionResult(
                        text=transcription.text,
                        raw_text=transcription.raw_text,
                        prompt_mode=PromptMode.PURE,
                        used_visual_context=False,
                        latency_seconds=transcription.latency_seconds,
                        execution_route=transcription.execution_route,
                    )
                )
                try:
                    routed_output = worker.text_queue.get_nowait()
                except queue.Empty:
                    routed_output = None
                passed = routed_output == expected_output
                results.append(
                    CommandRoutingResult(
                        spoken_command=command,
                        transcript=transcription.text,
                        expected_output=expected_output,
                        routed_output=routed_output,
                        passed=passed,
                    )
                )
                print(
                    "Command check "
                    f"{command!r}: transcript={transcription.text!r} "
                    f"routed={routed_output!r} expected={expected_output!r}"
                )
            finally:
                if not args.keep_audio:
                    try:
                        audio_path.unlink()
                    except OSError:
                        pass
                app.processEvents()
    finally:
        backend.unload()
    return results


def _run_whisper(audio, sample_rate: int, args: argparse.Namespace) -> BackendSummary:
    settings = AppSettings(backend="faster-whisper", whisper_model=args.whisper_model, language=args.language)
    backend = WhisperBackend(settings)
    load_result = backend.load()
    print(f"Whisper status: {load_result.status_message}")
    if not load_result.success:
        raise RuntimeError(load_result.status_message)
    runs: list[RunResult] = []
    try:
        for index in range(args.runs):
            result = backend.transcribe(_request(audio, sample_rate, args.language))
            ratio = _word_match_ratio(result.text, args.expected)
            runs.append(RunResult(result.text, result.latency_seconds, ratio))
            print(f"Whisper run {index + 1}: latency={result.latency_seconds:.2f}s match={ratio:.0%}")
    finally:
        backend.unload()
    return _summarize("faster-whisper", args.whisper_model, runs)


def _run_candidate(audio, sample_rate: int, args: argparse.Namespace) -> BackendSummary:
    settings = AppSettings(backend="transformers-asr", alternative_stt_model=args.candidate_model, language=args.language)
    backend = TransformersASRBackend(settings)
    load_result = backend.load()
    print(f"Candidate status: {load_result.status_message}")
    if not load_result.success:
        raise RuntimeError(load_result.status_message)
    runs: list[RunResult] = []
    try:
        for index in range(args.runs):
            result = backend.transcribe(_request(audio, sample_rate, args.language))
            ratio = _word_match_ratio(result.text, args.expected)
            runs.append(RunResult(result.text, result.latency_seconds, ratio))
            print(f"Candidate run {index + 1}: latency={result.latency_seconds:.2f}s match={ratio:.0%}")
    finally:
        backend.unload()
    return _summarize("transformers-asr", args.candidate_model, runs)


def _decision(
    baseline: BackendSummary,
    candidate: BackendSummary | None,
    min_word_ratio: float,
    promotion_speedup: float,
) -> str:
    if baseline.best_word_match_ratio < min_word_ratio:
        return "invalid-baseline"
    if candidate is None:
        return "baseline-only"
    if candidate.best_word_match_ratio < baseline.best_word_match_ratio:
        return "defer-candidate-accuracy"
    required_latency = baseline.median_latency_seconds * (1.0 - promotion_speedup)
    if candidate.median_latency_seconds <= required_latency:
        return "candidate-meets-latency-promotion-bar"
    return "defer-candidate-no-measured-win"


def _promotion_blockers(
    candidate: BackendSummary | None,
    decision: str,
    package_boundary: PackageBoundarySummary | None,
    import_boundary: ImportBoundarySummary,
    command_routing: list[CommandRoutingResult],
    audio_source: str,
) -> list[str]:
    if candidate is None:
        return []
    blockers = ["release UI promotion not approved"]
    if audio_source != "physical-microphone":
        blockers.append("physical microphone snippets not benchmarked")
    if not command_routing:
        blockers.append("command/punctuation behavior not benchmarked")
    elif not all(result.passed for result in command_routing):
        blockers.append("command/punctuation behavior failed")
    if package_boundary is None or not package_boundary.passed:
        blockers.append("Whisper-only package boundary not proven in this benchmark")
    if not import_boundary.passed:
        blockers.append("baseline import boundary not proven in this benchmark")
    if candidate.cache_size_bytes is None:
        blockers.append("candidate cache footprint not found in local Hugging Face cache")
    if decision != "candidate-meets-latency-promotion-bar":
        blockers.append("candidate did not meet latency promotion bar")
    return blockers


def main() -> int:
    args = parse_args()
    if args.runs < 1:
        raise ValueError("--runs must be at least 1.")

    audio_source = args.audio_source or ("other-file" if args.audio else "generated-sapi")
    audio_path = Path(args.audio) if args.audio else synthesize_wav(args.expected)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    print(f"Audio fixture: {audio_path}")
    audio, sample_rate = librosa.load(audio_path, sr=16000, mono=True)
    if audio.size == 0:
        raise AssertionError("Audio fixture loaded as empty.")

    candidate_summary: BackendSummary | None = None
    try:
        baseline_summary = _run_whisper(audio, sample_rate, args)
        if args.candidate_model:
            candidate_summary = _run_candidate(audio, sample_rate, args)
    finally:
        if not args.audio and not args.keep_audio:
            try:
                audio_path.unlink()
            except OSError:
                pass

    package_boundary = _package_boundary_summary(args.whisper_package_dir)
    import_boundary = _import_boundary_summary(args.check_import_boundary)
    command_routing = _run_command_routing_checks(args)
    decision = _decision(baseline_summary, candidate_summary, args.min_word_ratio, args.promotion_speedup)
    promotion_blockers = _promotion_blockers(
        candidate_summary,
        decision,
        package_boundary,
        import_boundary,
        command_routing,
        audio_source,
    )
    payload = {
        "audio": str(audio_path),
        "audio_source": audio_source,
        "expected": args.expected,
        "runs": args.runs,
        "min_word_ratio": args.min_word_ratio,
        "promotion_speedup": args.promotion_speedup,
        "baseline": asdict(baseline_summary),
        "candidate": asdict(candidate_summary) if candidate_summary else None,
        "package_boundary": asdict(package_boundary) if package_boundary else None,
        "import_boundary": asdict(import_boundary),
        "command_routing": [asdict(result) for result in command_routing],
        "decision": decision,
        "promotion_ready": bool(candidate_summary is not None and not promotion_blockers),
        "promotion_blockers": promotion_blockers,
    }
    print(f"Decision: {decision}")
    if promotion_blockers:
        print("Promotion blockers:")
        for blocker in promotion_blockers:
            print(f"- {blocker}")
    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote report: {report_path.resolve()}")
    return 0 if decision != "invalid-baseline" else 1


if __name__ == "__main__":
    raise SystemExit(main())
