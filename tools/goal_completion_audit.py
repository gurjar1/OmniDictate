from __future__ import annotations

import sys
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import open_gate_summary


COMPLETION_AUDIT = ROOT / "docs" / "ai" / "COMPLETION_AUDIT.md"
HANDOFF = ROOT / "docs" / "ai" / "HANDOFF.md"
STATE = ROOT / "docs" / "ai" / "STATE.md"
VERIFY = ROOT / "docs" / "ai" / "VERIFY.md"
DECISION_MATRIX = ROOT / "smoke_test_assets" / "packaging" / "release-decision-matrix.json"

REQUIRED_OBJECTIVE_MARKERS = [
    "Status: release objective locally ready",
    "Understand the successful `v2.0.2` baseline",
    "Compare local Gemma-era work to the known-good baseline",
    "Decide whether the Gemma direction is salvageable",
    "Preserve Whisper as the stable product path",
    "Review current STT model landscape",
    "Include better STT models if justified",
    "Understand features and UI/UX",
    "Create agent/AI/spec/test/acceptance docs",
    "Implement loop principle",
    "Complete testing with minimum human intervention",
    "Verify physical microphone behavior",
    "Verify live Gemma E4B",
    "Verify real GGUF server route",
    "Final release readiness",
    "Objective Evidence Matrix",
    "Proof standard",
    "Authoritative evidence",
    "Closure condition",
    "adjacent tests or plausible implementation intent are not enough",
    "Verify the known-good `v2.0.2` baseline",
    "Analyze whether local Gemma-era direction was right",
    "Preserve and test Whisper features",
    "Close physical microphone behavior",
    "Close live Gemma E4B",
    "Close real GGUF route",
    "Publish or prepare final release",
    "locally ready for publication",
]

REQUIRED_INCOMPLETE_ROWS = [
    "| Verify live Gemma E4B |",
    "| Verify real GGUF server route |",
]

REQUIRED_OPEN_GATE_KEYS = {
    "physical-microphone",
    "gemma-e4b-live",
    "gguf-real-server",
}
REQUIRED_RELEASE_SCOPE_STATUSES = {
    "physical-microphone": "proven",
    "gemma-e4b-live": "scoped-out",
    "gguf-real-server": "scoped-out",
}

REQUIRED_PHYSICAL_MIC_MARKERS = [
    "tools\\physical_microphone_run_card.py --report-json smoke_test_assets\\microphone\\physical-gate-dry-run.json",
    "tools\\physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --report-json smoke_test_assets\\microphone\\physical-gate-report.json",
    "saved audio-device inventory recommendation",
]

REQUIRED_SHARED_DOC_MARKERS = [
    "physical microphone",
    "Gemma E4B",
    "GGUF",
    "v3.0.0",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _row_is_incomplete(text: str, row_marker: str) -> bool:
    return any(line.startswith(row_marker) and line.rstrip().endswith("| Incomplete |") for line in text.splitlines())


def main() -> int:
    failures: list[str] = []
    completion = _read(COMPLETION_AUDIT)

    for marker in REQUIRED_OBJECTIVE_MARKERS:
        if marker not in completion:
            failures.append(f"completion audit missing objective marker: {marker}")

    for row_marker in REQUIRED_INCOMPLETE_ROWS:
        if not _row_is_incomplete(completion, row_marker):
            failures.append(f"completion audit row is not explicitly incomplete: {row_marker}")

    for marker in REQUIRED_PHYSICAL_MIC_MARKERS:
        if marker not in completion:
            failures.append(f"completion audit missing physical microphone run marker: {marker}")

    gate_failures = open_gate_summary._validate_current_docs()
    failures.extend(f"open gate summary mismatch: {failure}" for failure in gate_failures)

    gates = {gate.key for gate in open_gate_summary.OPEN_GATES}
    if gates != REQUIRED_OPEN_GATE_KEYS:
        failures.append(f"open gate key set changed: {sorted(gates)}")
    if len(open_gate_summary.OPEN_GATES) != 3:
        failures.append(f"expected 3 open gates, found {len(open_gate_summary.OPEN_GATES)}")

    if not DECISION_MATRIX.is_file():
        failures.append(f"missing release decision matrix: {DECISION_MATRIX}")
    else:
        matrix = _read_json(DECISION_MATRIX)
        if matrix.get("status") != "ready":
            failures.append("release decision matrix does not report ready status")
        if matrix.get("publish_ready") is not True:
            failures.append("release decision matrix does not report publish_ready true")
        summary = matrix.get("summary", {})
        if summary.get("final_artifact_status") != "ready":
            failures.append("release decision matrix does not report final artifact ready")
        if summary.get("open_gate_count") != 3:
            failures.append("release decision matrix does not report three open gates")
        matrix_rows = matrix.get("gate_rows", [])
        matrix_gate_keys = {row.get("key", "") for row in matrix_rows}
        if matrix_gate_keys != REQUIRED_OPEN_GATE_KEYS:
            failures.append(f"release decision matrix open gate set changed: {sorted(matrix_gate_keys)}")
        for row in matrix_rows:
            key = row.get("key", "")
            if row.get("release_scope_status") != REQUIRED_RELEASE_SCOPE_STATUSES.get(key):
                failures.append(
                    f"release decision matrix gate has unexpected release scope status: {key}"
                )
            if not row.get("next_command"):
                failures.append(f"release decision matrix gate is missing next command: {key}")

    shared_docs = {
        "HANDOFF.md": _read(HANDOFF),
        "STATE.md": _read(STATE),
        "VERIFY.md": _read(VERIFY),
    }
    for doc_name, text in shared_docs.items():
        for marker in REQUIRED_SHARED_DOC_MARKERS:
            if marker not in text:
                failures.append(f"{doc_name} missing open gate marker: {marker}")

    if failures:
        print("Goal completion audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Goal completion audit passed: local release preparation is ready; GitHub publication remains a separate action.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
