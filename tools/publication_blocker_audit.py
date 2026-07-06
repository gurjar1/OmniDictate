from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import open_gate_summary, release_scope_decision_audit


FINAL_PUBLIC_REPORT = ROOT / "smoke_test_assets" / "packaging" / "final-public-release-gate-report.json"
FINAL_AUDIT_REPORT = ROOT / "smoke_test_assets" / "packaging" / "final-release-gate-report.json"
SCHEMA_VERSION = 1


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _resolve_arg_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def _generated_at_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def audit_publication_blockers(
    final_public_report: Path = FINAL_PUBLIC_REPORT,
    final_audit_report: Path = FINAL_AUDIT_REPORT,
    scope_decisions_doc: Path = release_scope_decision_audit.DECISIONS_DOC,
) -> tuple[str, list[str], dict]:
    failures: list[str] = []
    scope_status, scope_failures, _scope_payload = release_scope_decision_audit.audit_scope_decisions(scope_decisions_doc)
    scope_decisions = (
        release_scope_decision_audit.read_scope_decisions(scope_decisions_doc)
        if scope_status == "passed"
        else {}
    )
    pending_gate_keys = {
        gate_key
        for gate_key, decision in scope_decisions.items()
        if decision.status == "pending"
    }
    blockers = [gate.key for gate in open_gate_summary.OPEN_GATES if gate.key in pending_gate_keys]
    gate_payloads = {str(gate["key"]): gate for gate in open_gate_summary._gate_payloads()}
    gate_details = [
        {
            "key": gate.key,
            "title": gate.title,
            "release_scope_status": scope_decisions.get(gate.key).status if gate.key in scope_decisions else "",
            "external_dependency": gate.external_dependency,
            "evidence": gate.evidence,
            "next_commands": gate_payloads.get(gate.key, {}).get("next_command", gate.next_command),
        }
        for gate in open_gate_summary.OPEN_GATES
        if gate.key in pending_gate_keys
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _generated_at_utc(),
        "status": "blocked",
        "scope_decisions_doc": _display_path(scope_decisions_doc),
        "scope_decision_status": scope_status,
        "scope_gate_statuses": {
            gate_key: decision.status for gate_key, decision in sorted(scope_decisions.items())
        },
        "open_gate_count": len(blockers),
        "open_gates": blockers,
        "open_gate_details": gate_details,
        "final_public_report": _display_path(final_public_report),
        "final_audit_report": _display_path(final_audit_report),
        "final_public_status": "",
        "final_artifact_status": "",
        "installer_sha256": "",
        "failures": failures,
    }

    if scope_failures:
        failures.extend(f"release scope decision audit failed: {failure}" for failure in scope_failures)

    expected_gate_universe = {"physical-microphone", "gemma-e4b-live", "gguf-real-server"}
    current_open_gate_universe = {gate.key for gate in open_gate_summary.OPEN_GATES}
    if current_open_gate_universe != expected_gate_universe:
        failures.append(f"unexpected open gate universe: {sorted(current_open_gate_universe)}")
    if set(scope_decisions) != expected_gate_universe and scope_status == "passed":
        failures.append(f"unexpected release scope decision set: {sorted(scope_decisions)}")

    if not final_public_report.is_file():
        failures.append(f"missing final public release gate report: {final_public_report}")
    else:
        report = _read_json(final_public_report)
        payload["final_public_status"] = report.get("status", "")
        if report.get("status") != "passed":
            failures.append("final public release gate report is not passed")

    if not final_audit_report.is_file():
        failures.append(f"missing final release gate audit report: {final_audit_report}")
    else:
        audit_report = _read_json(final_audit_report)
        payload["final_artifact_status"] = audit_report.get("status", "")
        payload["installer_sha256"] = audit_report.get("installer_sha256", "")
        if audit_report.get("status") != "ready":
            failures.append("final release gate audit report is not ready")
        if not audit_report.get("installer_sha256"):
            failures.append("final release gate audit report is missing installer SHA256")

    if failures:
        payload["status"] = "invalid"
        return "invalid", failures, payload
    if not blockers:
        payload["status"] = "ready"
        return "ready", failures, payload
    return "blocked", failures, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report whether OmniDictate can be published, and list remaining blockers."
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--report-json", default="", help="Optional path for a JSON audit report.")
    parser.add_argument("--final-public-report", default=str(FINAL_PUBLIC_REPORT.relative_to(ROOT)))
    parser.add_argument("--final-audit-report", default=str(FINAL_AUDIT_REPORT.relative_to(ROOT)))
    parser.add_argument(
        "--scope-decisions-doc",
        default=str(release_scope_decision_audit.DECISIONS_DOC.relative_to(ROOT)),
        help="Release scope decision document.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status, failures, payload = audit_publication_blockers(
        _resolve_arg_path(args.final_public_report),
        _resolve_arg_path(args.final_audit_report),
        _resolve_arg_path(args.scope_decisions_doc),
    )
    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    elif failures:
        print("Publication blocker audit failed:")
        for failure in failures:
            print(f"- {failure}")
    else:
        if status == "ready":
            print("Publication blocker audit passed: no pending release-scope gates.")
        else:
            print("Publication is blocked by remaining external gates:")
            for gate in open_gate_summary.OPEN_GATES:
                if gate.key in payload["open_gates"]:
                    print(f"- {gate.key}: {gate.external_dependency}")
        print(f"Final artifact: {payload['final_artifact_status']}")
        print(f"Installer SHA256: {payload['installer_sha256']}")
    return 0 if status in {"blocked", "ready"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
