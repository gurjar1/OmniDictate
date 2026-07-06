from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.whisper_fixture_test import DEFAULT_PHRASE, normalize_words

E4B_MODEL = "google/gemma-4-E4B-it"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate whether saved Gemma E4B preflight and live-smoke reports close the E4B gate."
    )
    parser.add_argument("--preflight-report", required=True, help="JSON from gemma_model_preflight.py.")
    parser.add_argument("--smoke-report", required=True, help="JSON from gemma_smoke_test.py for E4B.")
    parser.add_argument("--expected", default=DEFAULT_PHRASE)
    parser.add_argument("--min-word-ratio", type=float, default=0.75)
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
    preflight_report: dict,
    smoke_report: dict,
    expected: str = DEFAULT_PHRASE,
    min_word_ratio: float = 0.75,
) -> list[str]:
    failures: list[str] = []

    if preflight_report.get("model") != E4B_MODEL:
        failures.append("preflight report is not for Gemma E4B")
    local_summary = preflight_report.get("local_summary") or {}
    if local_summary.get("exists") is not True:
        failures.append("preflight report does not prove local E4B directory exists")
    if local_summary.get("has_safetensors") is not True:
        failures.append("preflight report does not prove local E4B safetensors exist")
    if int(local_summary.get("bytes") or 0) <= 0:
        failures.append("preflight report local E4B weights have zero bytes")
    transformers = preflight_report.get("transformers") or {}
    if transformers.get("available") is not True:
        failures.append("preflight report does not prove Transformers is available")
    if transformers.get("model_class") not in {"AutoModelForMultimodalLM", "AutoModelForImageTextToText"}:
        failures.append("preflight report does not expose a Gemma multimodal model class")
    torch = preflight_report.get("torch") or {}
    if torch.get("available") is not True:
        failures.append("preflight report does not prove Torch is available")

    if smoke_report.get("status") != "passed":
        failures.append("E4B live smoke report did not pass")
    if smoke_report.get("runtime") != "transformers":
        failures.append("E4B live smoke runtime is not transformers")
    if smoke_report.get("model") != E4B_MODEL:
        failures.append("E4B live smoke report is not for Gemma E4B")
    if smoke_report.get("audio_mode") != "hybrid-whisper":
        failures.append("E4B release gate requires the hybrid-whisper path")
    if smoke_report.get("backend_load_success") is not True:
        failures.append("E4B live smoke did not load successfully")
    if smoke_report.get("execution_label") != "Whisper -> Gemma":
        failures.append("E4B live smoke did not use the Whisper -> Gemma route")
    if smoke_report.get("used_visual_context") is not True:
        failures.append("E4B live smoke did not use visual context")
    if _word_ratio(str(smoke_report.get("text") or ""), expected) < min_word_ratio:
        failures.append("E4B live smoke text does not meet the word-match threshold")
    if smoke_report.get("error"):
        failures.append("E4B live smoke report contains an error")

    return failures


def main() -> int:
    args = parse_args()
    failures = audit_reports(
        _read_json(Path(args.preflight_report)),
        _read_json(Path(args.smoke_report)),
        expected=args.expected,
        min_word_ratio=args.min_word_ratio,
    )
    if failures:
        print("Gemma E4B gate report audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Gemma E4B gate report audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
