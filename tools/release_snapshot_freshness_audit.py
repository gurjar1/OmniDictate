from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import (
    external_gate_orchestrator,
    external_gate_closure_audit,
    external_gate_prerequisite_audit,
    github_release_preflight,
    publication_blocker_audit,
    release_decision_matrix_report,
    release_status_report,
)


DEFAULT_PUBLICATION_REPORT = ROOT / "smoke_test_assets" / "packaging" / "publication-blockers.json"
DEFAULT_RELEASE_STATUS_REPORT = ROOT / "smoke_test_assets" / "packaging" / "release-status-report.json"
DEFAULT_GITHUB_PREFLIGHT_REPORT = ROOT / "smoke_test_assets" / "packaging" / "github-release-preflight.json"
DEFAULT_EXTERNAL_GATES_REPORT = ROOT / "smoke_test_assets" / "external-gates-dry-run.json"
DEFAULT_PREREQUISITES_REPORT = ROOT / "smoke_test_assets" / "external-gate-prerequisites.json"
DEFAULT_CLOSURE_AUDIT_REPORT = ROOT / "smoke_test_assets" / "external-gate-closure-audit.json"
DEFAULT_DECISION_MATRIX_REPORT = ROOT / "smoke_test_assets" / "packaging" / "release-decision-matrix.json"
VOLATILE_KEYS = {"generated_at_utc"}


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize(child)
            for key, child in value.items()
            if key not in VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_normalize(child) for child in value]
    return value


def _diff_report(name: str, expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    normalized_expected = _normalize(expected)
    normalized_actual = _normalize(actual)
    if normalized_expected == normalized_actual:
        return []

    failures = [f"{name} is stale or does not match current tool output"]
    for key in sorted(set(normalized_expected) | set(normalized_actual)):
        if normalized_expected.get(key) != normalized_actual.get(key):
            failures.append(f"{name}.{key} differs")
    return failures


def _expected_external_gate_dry_run() -> dict[str, Any]:
    microphone_device = external_gate_orchestrator.recommended_microphone_device()
    gates = external_gate_orchestrator.selected_gates("all", microphone_device)
    return {
        "status": "dry-run-passed",
        "mode": "dry-run",
        "gate_count": len(gates),
        "microphone_device": microphone_device,
        "microphone_device_source": "inventory" if microphone_device else "",
        "microphone_device_inventory_report": str(
            external_gate_orchestrator.MIC_DEVICE_INVENTORY_REPORT.relative_to(ROOT)
        ),
        "gates": [
            {
                "key": gate.key,
                "title": gate.title,
                "release_scope_status": external_gate_orchestrator._release_scope_status(gate.key),
                "dependency": gate.dependency,
                "command": external_gate_orchestrator._display_command(gate.dry_run_command),
            }
            for gate in gates
        ],
        "results": [
            {
                "key": gate.key,
                "command": external_gate_orchestrator._display_command(gate.dry_run_command),
                "returncode": 0,
            }
            for gate in gates
        ],
    }


def audit_release_snapshots(
    publication_report: Path = DEFAULT_PUBLICATION_REPORT,
    release_status_path: Path = DEFAULT_RELEASE_STATUS_REPORT,
    github_preflight_path: Path = DEFAULT_GITHUB_PREFLIGHT_REPORT,
    external_gates_path: Path = DEFAULT_EXTERNAL_GATES_REPORT,
    prerequisites_path: Path = DEFAULT_PREREQUISITES_REPORT,
    closure_audit_path: Path = DEFAULT_CLOSURE_AUDIT_REPORT,
    decision_matrix_path: Path = DEFAULT_DECISION_MATRIX_REPORT,
) -> tuple[str, list[str], dict[str, Any]]:
    failures: list[str] = []
    payload: dict[str, Any] = {
        "status": "passed",
        "publication_report": str(publication_report.relative_to(ROOT))
        if publication_report.is_relative_to(ROOT)
        else str(publication_report),
        "release_status_report": str(release_status_path.relative_to(ROOT))
        if release_status_path.is_relative_to(ROOT)
        else str(release_status_path),
        "github_preflight_report": str(github_preflight_path.relative_to(ROOT))
        if github_preflight_path.is_relative_to(ROOT)
        else str(github_preflight_path),
        "external_gates_report": str(external_gates_path.relative_to(ROOT))
        if external_gates_path.is_relative_to(ROOT)
        else str(external_gates_path),
        "prerequisites_report": str(prerequisites_path.relative_to(ROOT))
        if prerequisites_path.is_relative_to(ROOT)
        else str(prerequisites_path),
        "closure_audit_report": str(closure_audit_path.relative_to(ROOT))
        if closure_audit_path.is_relative_to(ROOT)
        else str(closure_audit_path),
        "decision_matrix_report": str(decision_matrix_path.relative_to(ROOT))
        if decision_matrix_path.is_relative_to(ROOT)
        else str(decision_matrix_path),
        "ignored_keys": sorted(VOLATILE_KEYS),
        "failures": failures,
    }

    if not publication_report.is_file():
        failures.append(f"missing publication report: {publication_report}")
    else:
        _status, _blocker_failures, expected_publication = publication_blocker_audit.audit_publication_blockers()
        actual_publication = _read_json(publication_report)
        failures.extend(_diff_report("publication_report", expected_publication, actual_publication))

    if not release_status_path.is_file():
        failures.append(f"missing release status report: {release_status_path}")
    else:
        _status, _status_failures, expected_release = release_status_report.build_release_status()
        actual_release = _read_json(release_status_path)
        failures.extend(_diff_report("release_status_report", expected_release, actual_release))

    if not github_preflight_path.is_file():
        failures.append(f"missing GitHub release preflight report: {github_preflight_path}")
    else:
        _status, _preflight_failures, expected_preflight = github_release_preflight.build_github_release_preflight()
        actual_preflight = _read_json(github_preflight_path)
        failures.extend(_diff_report("github_preflight_report", expected_preflight, actual_preflight))

    if not external_gates_path.is_file():
        failures.append(f"missing external gate dry-run report: {external_gates_path}")
    else:
        actual_external = _read_json(external_gates_path)
        failures.extend(_diff_report("external_gates_report", _expected_external_gate_dry_run(), actual_external))

    if not prerequisites_path.is_file():
        failures.append(f"missing external gate prerequisites report: {prerequisites_path}")
    else:
        _status, _prereq_failures, expected_prerequisites = external_gate_prerequisite_audit.build_prerequisite_audit()
        actual_prerequisites = _read_json(prerequisites_path)
        failures.extend(_diff_report("prerequisites_report", expected_prerequisites, actual_prerequisites))

    if not closure_audit_path.is_file():
        failures.append(f"missing external gate closure audit report: {closure_audit_path}")
    else:
        _status, _closure_failures, expected_closure = external_gate_closure_audit.build_closure_audit()
        actual_closure = _read_json(closure_audit_path)
        failures.extend(_diff_report("closure_audit_report", expected_closure, actual_closure))

    if not decision_matrix_path.is_file():
        failures.append(f"missing release decision matrix report: {decision_matrix_path}")
    else:
        _status, _matrix_failures, expected_matrix = release_decision_matrix_report.build_release_decision_matrix()
        actual_matrix = _read_json(decision_matrix_path)
        failures.extend(_diff_report("decision_matrix_report", expected_matrix, actual_matrix))

    if failures:
        payload["status"] = "failed"
    return payload["status"], failures, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify saved release status snapshots still match current non-interactive tool output."
    )
    parser.add_argument(
        "--publication-report",
        default=str(DEFAULT_PUBLICATION_REPORT.relative_to(ROOT)),
        help="Saved publication blocker JSON report.",
    )
    parser.add_argument(
        "--release-status-report",
        default=str(DEFAULT_RELEASE_STATUS_REPORT.relative_to(ROOT)),
        help="Saved release status JSON report.",
    )
    parser.add_argument(
        "--github-preflight-report",
        default=str(DEFAULT_GITHUB_PREFLIGHT_REPORT.relative_to(ROOT)),
        help="Saved GitHub release preflight JSON report.",
    )
    parser.add_argument(
        "--external-gates-report",
        default=str(DEFAULT_EXTERNAL_GATES_REPORT.relative_to(ROOT)),
        help="Saved external gate dry-run JSON report.",
    )
    parser.add_argument(
        "--prerequisites-report",
        default=str(DEFAULT_PREREQUISITES_REPORT.relative_to(ROOT)),
        help="Saved external gate prerequisite JSON report.",
    )
    parser.add_argument(
        "--closure-audit-report",
        default=str(DEFAULT_CLOSURE_AUDIT_REPORT.relative_to(ROOT)),
        help="Saved external gate closure audit JSON report.",
    )
    parser.add_argument(
        "--decision-matrix-report",
        default=str(DEFAULT_DECISION_MATRIX_REPORT.relative_to(ROOT)),
        help="Saved release decision matrix JSON report.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status, failures, payload = audit_release_snapshots(
        _resolve_path(args.publication_report),
        _resolve_path(args.release_status_report),
        _resolve_path(args.github_preflight_report),
        _resolve_path(args.external_gates_report),
        _resolve_path(args.prerequisites_report),
        _resolve_path(args.closure_audit_report),
        _resolve_path(args.decision_matrix_report),
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    elif failures:
        print("Release snapshot freshness audit failed:")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("Release snapshot freshness audit passed.")
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
