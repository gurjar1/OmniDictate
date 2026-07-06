from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.whisper_fixture_test import DEFAULT_PHRASE, normalize_words


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate whether saved GGUF probe and backend reports close the real-server gate."
    )
    parser.add_argument("--probe-report", required=True, help="JSON from gguf_server_probe.py.")
    parser.add_argument("--smoke-report", required=True, help="JSON from gemma_smoke_test.py --runtime gguf-server.")
    parser.add_argument(
        "--server-implementation",
        required=True,
        help="Named real local server implementation, for example LM Studio or llama.cpp.",
    )
    parser.add_argument("--expected", default=DEFAULT_PHRASE)
    parser.add_argument("--min-word-ratio", type=float, default=0.6)
    return parser.parse_args()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _word_ratio(actual: str, expected: str) -> float:
    expected_words = normalize_words(expected)
    if not expected_words:
        return 0.0
    actual_words = set(normalize_words(actual))
    matched = [word for word in expected_words if word in actual_words]
    return len(matched) / len(expected_words)


def audit_reports(
    probe_report: dict,
    smoke_report: dict,
    server_implementation: str,
    expected: str = DEFAULT_PHRASE,
    min_word_ratio: float = 0.6,
) -> list[str]:
    failures: list[str] = []
    server_label = server_implementation.strip()
    if not server_label:
        failures.append("server implementation label is required")
    if "mock" in server_label.lower():
        failures.append("server implementation must be a named real server, not a mock")

    if probe_report.get("status") != "passed":
        failures.append("GGUF direct probe report did not pass")
    if not probe_report.get("base_url"):
        failures.append("GGUF direct probe report is missing base_url")
    if not probe_report.get("selected_model"):
        failures.append("GGUF direct probe report is missing selected_model")
    if not probe_report.get("response_text"):
        failures.append("GGUF direct probe report is missing response text")
    if probe_report.get("error"):
        failures.append("GGUF direct probe report contains an error")

    if smoke_report.get("status") != "passed":
        failures.append("GGUF backend smoke report did not pass")
    if smoke_report.get("runtime") != "gguf-server":
        failures.append("GGUF backend smoke report runtime is not gguf-server")
    if smoke_report.get("gguf_url") != probe_report.get("base_url"):
        failures.append("GGUF backend smoke URL does not match the direct probe base_url")
    if smoke_report.get("backend_load_success") is not True:
        failures.append("GGUF backend smoke did not load successfully")
    if smoke_report.get("execution_label") != "Whisper -> GGUF server":
        failures.append("GGUF backend smoke did not use the GGUF server refinement route")
    if smoke_report.get("used_visual_context") is not True:
        failures.append("GGUF backend smoke did not use visual context")
    if _word_ratio(str(smoke_report.get("text") or ""), expected) < min_word_ratio:
        failures.append("GGUF backend smoke text does not meet the word-match threshold")
    if smoke_report.get("error"):
        failures.append("GGUF backend smoke report contains an error")

    return failures


def main() -> int:
    args = parse_args()
    failures = audit_reports(
        _read_json(Path(args.probe_report)),
        _read_json(Path(args.smoke_report)),
        server_implementation=args.server_implementation,
        expected=args.expected,
        min_word_ratio=args.min_word_ratio,
    )
    if failures:
        print("GGUF real-server gate report audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("GGUF real-server gate report audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
