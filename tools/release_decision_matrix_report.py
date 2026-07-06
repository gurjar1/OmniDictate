from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import release_status_report


DEFAULT_REPORT = ROOT / "smoke_test_assets" / "packaging" / "release-decision-matrix.json"
DEFAULT_EXTERNAL_GATES_REPORT = ROOT / "smoke_test_assets" / "external-gates-dry-run.json"
DEFAULT_PREREQUISITES_REPORT = ROOT / "smoke_test_assets" / "external-gate-prerequisites.json"
DEFAULT_CLOSURE_AUDIT_REPORT = ROOT / "smoke_test_assets" / "external-gate-closure-audit.json"
DEFAULT_GITHUB_PREFLIGHT_REPORT = ROOT / "smoke_test_assets" / "packaging" / "github-release-preflight.json"
DEFAULT_PUBLICATION_BLOCKERS_REPORT = ROOT / "smoke_test_assets" / "packaging" / "publication-blockers.json"
SCHEMA_VERSION = 1


def _generated_at_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def _read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _external_gate_commands(external_payload: dict[str, Any]) -> dict[str, str]:
    commands: dict[str, str] = {}
    for gate in external_payload.get("gates", []):
        key = gate.get("key")
        command = gate.get("command")
        if isinstance(key, str) and isinstance(command, str):
            commands[key] = command
    return commands


def _preparation_commands_by_gate(commands: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for command in commands:
        if "physical_microphone_run_card.py" in command:
            mapping["physical-microphone"] = command
        elif "gemma_model_preflight.py" in command:
            mapping["gemma-e4b-live"] = command
        elif "gguf_server_probe.py" in command:
            mapping["gguf-real-server"] = command
    return mapping


def build_release_decision_matrix(
    external_gates_report: Path = DEFAULT_EXTERNAL_GATES_REPORT,
    prerequisites_report: Path = DEFAULT_PREREQUISITES_REPORT,
    closure_audit_report: Path = DEFAULT_CLOSURE_AUDIT_REPORT,
    github_preflight_report: Path = DEFAULT_GITHUB_PREFLIGHT_REPORT,
) -> tuple[str, list[str], dict[str, Any]]:
    status, status_failures, release_payload = release_status_report.build_release_status()
    failures = list(status_failures)
    external_payload = _read_json_if_present(external_gates_report)
    prerequisites_payload = _read_json_if_present(prerequisites_report)
    closure_payload = _read_json_if_present(closure_audit_report)
    github_payload = _read_json_if_present(github_preflight_report)

    if not external_payload:
        failures.append(f"missing external gate dry-run report: {_display_path(external_gates_report)}")
    if not prerequisites_payload:
        failures.append(f"missing external gate prerequisites report: {_display_path(prerequisites_report)}")
    if not closure_payload:
        failures.append(f"missing external gate closure audit report: {_display_path(closure_audit_report)}")
    if not github_payload:
        failures.append(f"missing GitHub release preflight report: {_display_path(github_preflight_report)}")

    dry_run_commands = _external_gate_commands(external_payload)
    prerequisite_rows = {
        row.get("key", ""): row for row in prerequisites_payload.get("gate_rows", [])
    }
    closure_rows = {
        row.get("key", ""): row for row in closure_payload.get("gate_rows", [])
    }
    publication = release_payload.get("publication", {})
    gate_rows: list[dict[str, Any]] = []
    preparation_commands = release_payload.get("next_preparation_commands", [])
    preparation_by_gate = _preparation_commands_by_gate([str(command) for command in preparation_commands])
    for gate in release_payload.get("open_gates", []):
        key = gate.get("key", "")
        next_commands = gate.get("next_command", [])
        gate_rows.append(
            {
                "key": key,
                "title": gate.get("title", ""),
                "release_scope_status": gate.get("release_scope_status", ""),
                "gate_status": gate.get("status", ""),
                "human_or_external_dependency": gate.get("external_dependency", ""),
                "evidence": gate.get("evidence", ""),
                "next_command": next_commands[0] if next_commands else "",
                "preparation_command": preparation_by_gate.get(str(key), ""),
                "dry_run_command": dry_run_commands.get(key, ""),
                "ready_for_live_attempt": prerequisite_rows.get(key, {}).get("ready_for_live_attempt", False),
                "missing_files": prerequisite_rows.get(key, {}).get("missing_files", []),
                "missing_reports": prerequisite_rows.get(key, {}).get("missing_reports", []),
                "closure_report": prerequisite_rows.get(key, {}).get("closure_report", ""),
                "closure_audit_command": prerequisite_rows.get(key, {}).get("closure_audit_command", ""),
                "closure_state": closure_rows.get(key, {}).get("closure_state", ""),
                "scope_decision_target": closure_rows.get(key, {}).get("scope_decision_target", ""),
                "proves": "release gate can be removed only when this command writes a passing report",
            }
        )

    if external_payload and set(dry_run_commands) != {row["key"] for row in gate_rows}:
        failures.append("external gate dry-run report does not match current open gate set")
    if prerequisites_payload and set(prerequisite_rows) != {row["key"] for row in gate_rows}:
        failures.append("external gate prerequisites report does not match current open gate set")
    if closure_payload and set(closure_rows) != {row["key"] for row in gate_rows}:
        failures.append("external gate closure audit report does not match current open gate set")

    publication_status = "invalid" if failures else status
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _generated_at_utc(),
        "status": publication_status,
        "publish_ready": publication_status == "ready",
        "summary": {
            "publication_status": publication.get("status", ""),
            "final_public_status": publication.get("final_public_status", ""),
            "final_artifact_status": publication.get("final_artifact_status", ""),
            "installer_sha256": publication.get("installer_sha256", ""),
            "open_gate_count": release_payload.get("open_gate_count", 0),
            "github_preflight_status": github_payload.get("status", ""),
            "github_publish_ready": github_payload.get("publish_ready", False),
        },
        "reports": {
            "release_status": _display_path(release_status_report.DEFAULT_REPORT),
            "publication_blockers": _display_path(DEFAULT_PUBLICATION_BLOCKERS_REPORT),
            "external_gates_dry_run": _display_path(external_gates_report),
            "external_gate_prerequisites": _display_path(prerequisites_report),
            "external_gate_closure_audit": _display_path(closure_audit_report),
            "github_preflight": _display_path(github_preflight_report),
            "scope_decisions": publication.get("scope_decisions_doc", ""),
            "phase4_checklist": release_payload.get("phase4_checklist", ""),
            "publishing_runbook": release_payload.get("publishing_runbook", ""),
        },
        "gate_rows": gate_rows,
        "next_preparation_commands": release_payload.get("next_preparation_commands", []),
        "next_commands": release_payload.get("next_commands", []),
        "failures": failures,
    }
    return publication_status, failures, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit a compact release decision matrix for current publish readiness and remaining gates."
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--report-json", default="", help=f"Optional JSON output path; suggested {DEFAULT_REPORT.relative_to(ROOT)}.")
    parser.add_argument(
        "--external-gates-report",
        default=str(DEFAULT_EXTERNAL_GATES_REPORT.relative_to(ROOT)),
        help="Saved aggregate external-gate dry-run report.",
    )
    parser.add_argument(
        "--prerequisites-report",
        default=str(DEFAULT_PREREQUISITES_REPORT.relative_to(ROOT)),
        help="Saved non-interactive external-gate prerequisite report.",
    )
    parser.add_argument(
        "--closure-audit-report",
        default=str(DEFAULT_CLOSURE_AUDIT_REPORT.relative_to(ROOT)),
        help="Saved external-gate closure audit report.",
    )
    parser.add_argument(
        "--github-preflight-report",
        default=str(DEFAULT_GITHUB_PREFLIGHT_REPORT.relative_to(ROOT)),
        help="Saved GitHub release preflight report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status, failures, payload = build_release_decision_matrix(
        _resolve_path(args.external_gates_report),
        _resolve_path(args.prerequisites_report),
        _resolve_path(args.closure_audit_report),
        _resolve_path(args.github_preflight_report),
    )
    if args.report_json:
        report_path = _resolve_path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    elif failures:
        print("Release decision matrix is invalid:")
        for failure in failures:
            print(f"- {failure}")
    else:
        print(f"Release decision: {status}")
        print(f"Final artifact: {payload['summary']['final_artifact_status']}")
        print(f"GitHub preflight: {payload['summary']['github_preflight_status']}")
        print(f"Open gates: {payload['summary']['open_gate_count']}")
        for row in payload["gate_rows"]:
            print(f"- {row['key']} [{row['release_scope_status']}]: {row['human_or_external_dependency']}")
            if row["preparation_command"]:
                print(f"  Prep: {row['preparation_command']}")
            print(f"  Next: {row['next_command']}")
    return 0 if status in {"blocked", "ready"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
