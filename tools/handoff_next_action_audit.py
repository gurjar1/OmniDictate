from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import release_status_report

HANDOFF = ROOT / "docs" / "ai" / "HANDOFF.md"


REQUIRED_EXACT_NEXT_ACTION_MARKERS = [
    "## Exact Next Action",
    "tools\\open_gate_summary.py --strict",
    "tools\\publication_blocker_audit.py --report-json smoke_test_assets\\packaging\\publication-blockers.json",
    "tools\\release_status_report.py --report-json smoke_test_assets\\packaging\\release-status-report.json",
    "tools\\external_gate_prerequisite_audit.py --report-json smoke_test_assets\\external-gate-prerequisites.json",
    "tools\\external_gate_closure_audit.py --report-json smoke_test_assets\\external-gate-closure-audit.json",
    "tools\\release_decision_matrix_report.py --report-json smoke_test_assets\\packaging\\release-decision-matrix.json",
    "tools\\github_release_preflight.py --report-json smoke_test_assets\\packaging\\github-release-preflight.json",
    "docs\\implementation-plans-and-checklists\\phase-4-release-execution.md",
    "tools\\external_gate_orchestrator.py --report-json smoke_test_assets\\external-gates-dry-run.json",
    "tools\\gemma_e4b_gate.py --model google/gemma-4-E4B-it",
    "tools\\gguf_real_server_gate.py --url http://127.0.0.1:8080/v1 --server-implementation",
    "powershell -ExecutionPolicy Bypass -File tools\\verify_local.ps1",
]


def audit_handoff_next_action() -> list[str]:
    text = HANDOFF.read_text(encoding="utf-8")
    if "## Exact Next Action" not in text:
        return ["HANDOFF.md is missing the Exact Next Action section."]
    exact_next_action = text.split("## Exact Next Action", 1)[1]
    failures = [
        f"Exact Next Action missing marker: {marker}"
        for marker in REQUIRED_EXACT_NEXT_ACTION_MARKERS
        if marker not in exact_next_action and marker != "## Exact Next Action"
    ]
    _status, release_failures, payload = release_status_report.build_release_status()
    failures.extend(f"release status report invalid: {failure}" for failure in release_failures)
    recommended_command = payload.get("next_recommended_command", "")
    if recommended_command and recommended_command not in exact_next_action:
        failures.append(f"Exact Next Action missing recommended command: {recommended_command}")
    return failures


def main() -> int:
    failures = audit_handoff_next_action()
    if failures:
        print("Handoff next-action audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Handoff next-action audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
