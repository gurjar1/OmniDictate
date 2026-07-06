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

from tools import (
    gemma_e4b_gate_report_audit,
    gguf_gate_report_audit,
    microphone_gate_report_audit,
    open_gate_summary,
)
from tools.whisper_fixture_test import DEFAULT_PHRASE


SCHEMA_VERSION = 1
DEFAULT_REPORT = ROOT / "smoke_test_assets" / "external-gate-closure-audit.json"


def _generated_at_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _path_status(path: Path) -> dict[str, Any]:
    return {
        "path": _display_path(path),
        "exists": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else 0,
    }


def _audit_physical_microphone(expected: str, min_word_ratio: float) -> tuple[list[Path], list[str]]:
    capture_report = ROOT / "smoke_test_assets" / "microphone" / "spoken-phrase-large-v3-turbo-report.json"
    loop_report = ROOT / "smoke_test_assets" / "microphone" / "live-loop-large-v3-turbo-report.json"
    required = [capture_report, loop_report]
    if not all(path.is_file() for path in required):
        return required, []
    return required, microphone_gate_report_audit.audit_reports(
        _read_json(capture_report),
        _read_json(loop_report),
        expected=expected,
        min_word_ratio=min_word_ratio,
    )


def _audit_gemma_e4b(expected: str) -> tuple[list[Path], list[str]]:
    preflight_report = ROOT / "smoke_test_assets" / "gemma-e4b-preflight.json"
    smoke_report = ROOT / "smoke_test_assets" / "gemma-e4b-live-smoke.json"
    required = [preflight_report, smoke_report]
    if not all(path.is_file() for path in required):
        return required, []
    return required, gemma_e4b_gate_report_audit.audit_reports(
        _read_json(preflight_report),
        _read_json(smoke_report),
        expected=expected,
    )


def _audit_gguf(expected: str, min_word_ratio: float, server_implementation: str) -> tuple[list[Path], list[str]]:
    probe_report = ROOT / "smoke_test_assets" / "gguf" / "real-server-probe.json"
    smoke_report = ROOT / "smoke_test_assets" / "gguf" / "real-server-smoke.json"
    required = [probe_report, smoke_report]
    if not all(path.is_file() for path in required):
        return required, []
    return required, gguf_gate_report_audit.audit_reports(
        _read_json(probe_report),
        _read_json(smoke_report),
        server_implementation=server_implementation,
        expected=expected,
        min_word_ratio=min_word_ratio,
    )


def _gate_audit(gate_key: str, expected: str, gguf_server_implementation: str) -> tuple[list[Path], list[str]]:
    if gate_key == "physical-microphone":
        return _audit_physical_microphone(expected, 0.6)
    if gate_key == "gemma-e4b-live":
        return _audit_gemma_e4b(expected)
    if gate_key == "gguf-real-server":
        return _audit_gguf(expected, 0.6, gguf_server_implementation)
    raise KeyError(f"unknown gate key: {gate_key}")


def build_closure_audit(
    expected: str = DEFAULT_PHRASE,
    gguf_server_implementation: str = "LM Studio",
) -> tuple[str, list[str], dict[str, Any]]:
    failures: list[str] = []
    scope_statuses = open_gate_summary._release_scope_statuses()
    rows: list[dict[str, Any]] = []
    for gate in open_gate_summary.OPEN_GATES:
        required_reports, audit_failures = _gate_audit(gate.key, expected, gguf_server_implementation)
        report_statuses = [_path_status(path) for path in required_reports]
        missing_reports = [item["path"] for item in report_statuses if not item["exists"]]
        if missing_reports:
            closure_state = "missing-evidence"
        elif audit_failures:
            closure_state = "evidence-failed"
        else:
            closure_state = "eligible-for-proven"

        rows.append(
            {
                "key": gate.key,
                "title": gate.title,
                "release_scope_status": scope_statuses.get(gate.key, ""),
                "closure_state": closure_state,
                "required_reports": report_statuses,
                "missing_reports": missing_reports,
                "audit_failures": audit_failures,
                "scope_decision_target": "proven" if closure_state == "eligible-for-proven" else "pending",
                "next_command": gate.next_command[0] if gate.next_command else "",
            }
        )

    if {row["key"] for row in rows} != {gate.key for gate in open_gate_summary.OPEN_GATES}:
        failures.append("closure audit gate rows are out of sync with open gates")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _generated_at_utc(),
        "status": "passed" if not failures else "invalid",
        "open_gate_count": len(rows),
        "eligible_for_proven": [row["key"] for row in rows if row["closure_state"] == "eligible-for-proven"],
        "gate_rows": rows,
        "failures": failures,
    }
    return payload["status"], failures, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read saved external-gate evidence and report which gates are eligible for a proven scope decision."
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--report-json", default="", help=f"Optional JSON output path; suggested {DEFAULT_REPORT.relative_to(ROOT)}.")
    parser.add_argument("--expected", default=DEFAULT_PHRASE)
    parser.add_argument("--gguf-server-implementation", default="LM Studio")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status, failures, payload = build_closure_audit(args.expected, args.gguf_server_implementation)
    if args.report_json:
        report_path = Path(args.report_json)
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    elif failures:
        print("External gate closure audit is invalid:")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("External gate closure audit passed.")
        for row in payload["gate_rows"]:
            print(f"- {row['key']} [{row['release_scope_status']}]: {row['closure_state']}")
            if row["missing_reports"]:
                print(f"  Missing reports: {', '.join(row['missing_reports'])}")
            if row["audit_failures"]:
                print(f"  Audit failures: {'; '.join(row['audit_failures'])}")
            print(f"  Scope decision target: {row['scope_decision_target']}")
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
