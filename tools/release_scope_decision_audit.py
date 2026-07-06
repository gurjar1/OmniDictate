from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import open_gate_summary


DECISIONS_DOC = ROOT / "docs" / "release" / "RELEASE_SCOPE_DECISIONS_3.0.0.md"
ALLOWED_STATUSES = {"pending", "proven", "scoped-out"}
REQUIRED_GATES = {
    "physical-microphone": ROOT / "smoke_test_assets" / "microphone" / "physical-gate-report.json",
    "gemma-e4b-live": ROOT / "smoke_test_assets" / "gemma-e4b-gate-report.json",
    "gguf-real-server": ROOT / "smoke_test_assets" / "gguf" / "real-server-gate-report.json",
}


@dataclass(frozen=True)
class ScopeDecision:
    gate_key: str
    status: str
    required_evidence: str
    current_evidence: str
    user_authorization: str
    release_update: str


def _strip_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def _parse_table(text: str) -> dict[str, ScopeDecision]:
    decisions: dict[str, ScopeDecision] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `"):
            continue
        cells = [_strip_cell(cell) for cell in stripped.strip("|").split("|")]
        if len(cells) != 6:
            continue
        decision = ScopeDecision(
            gate_key=cells[0],
            status=cells[1],
            required_evidence=cells[2],
            current_evidence=cells[3],
            user_authorization=cells[4],
            release_update=cells[5],
        )
        decisions[decision.gate_key] = decision
    return decisions


def read_scope_decisions(doc_path: Path = DECISIONS_DOC) -> dict[str, ScopeDecision]:
    return _parse_table(doc_path.read_text(encoding="utf-8"))


def _report_status(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(payload.get("status", ""))


def _has_real_authorization(value: str) -> bool:
    lowered = value.lower()
    if lowered in {"", "n/a", "not applicable", "not applicable while pending"}:
        return False
    if re.search(r"\b(todo|tbd|pending|not applicable)\b", lowered):
        return False
    return bool(re.search(r"\buser authorized\b.*\b\d{4}-\d{2}-\d{2}\b", lowered))


def _has_release_update_marker(value: str) -> bool:
    lowered = value.lower()
    if re.search(r"\b(todo|tbd|pending|not applicable)\b", lowered):
        return False
    return bool(re.search(r"\bupdated\b.*\b\d{4}-\d{2}-\d{2}\b", lowered))


def audit_scope_decisions(doc_path: Path = DECISIONS_DOC) -> tuple[str, list[str], dict]:
    failures: list[str] = []
    payload = {
        "status": "passed",
        "decisions_doc": str(doc_path.relative_to(ROOT)) if doc_path.is_relative_to(ROOT) else str(doc_path),
        "gate_statuses": {},
        "open_gate_count": len(open_gate_summary.OPEN_GATES),
        "failures": failures,
    }

    if not doc_path.is_file():
        failures.append(f"missing release scope decisions doc: {doc_path}")
        payload["status"] = "failed"
        return "failed", failures, payload

    text = doc_path.read_text(encoding="utf-8")
    for marker in [
        "Allowed statuses:",
        "`pending`: the gate remains a publication blocker.",
        "`proven`: the gate has a passing report",
        "`scoped-out`: the user explicitly moved the gate",
        "User authorized ... on YYYY-MM-DD",
        "Updated ... on YYYY-MM-DD",
    ]:
        if marker not in text:
            failures.append(f"release scope decisions doc missing marker: {marker}")
    if (
        "Current decision: publication remains blocked" not in text
        and "Current decision: publication is ready" not in text
    ):
        failures.append(
            "release scope decisions doc missing marker: Current decision: publication remains blocked/ready"
        )

    decisions = _parse_table(text)
    open_gates = {gate.key for gate in open_gate_summary.OPEN_GATES}

    for gate_key, report_path in REQUIRED_GATES.items():
        decision = decisions.get(gate_key)
        if decision is None:
            failures.append(f"missing release scope decision row: {gate_key}")
            continue

        payload["gate_statuses"][gate_key] = decision.status
        if decision.status not in ALLOWED_STATUSES:
            failures.append(f"{gate_key} has invalid release scope status: {decision.status}")

        if decision.status == "pending" and gate_key not in open_gates:
            failures.append(f"{gate_key} is pending but not present in open gate summary")

        if decision.status == "proven" and _report_status(report_path) != "passed":
            failures.append(f"{gate_key} is proven but its gate report is not passed: {report_path}")

        if decision.status == "scoped-out":
            if not _has_real_authorization(decision.user_authorization):
                failures.append(
                    f"{gate_key} is scoped-out without explicit dated user authorization"
                )
            if not _has_release_update_marker(decision.release_update):
                failures.append(
                    f"{gate_key} is scoped-out without a dated release note/checklist update marker"
                )

    unknown = sorted(set(decisions) - set(REQUIRED_GATES))
    for gate_key in unknown:
        failures.append(f"unknown release scope decision row: {gate_key}")

    if failures:
        payload["status"] = "failed"
    return payload["status"], failures, payload


def main() -> int:
    status, failures, _payload = audit_scope_decisions()
    if failures:
        print("Release scope decision audit failed:")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("Release scope decision audit passed.")
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
