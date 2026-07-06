from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import open_gate_summary, publication_blocker_audit


DEFAULT_REPORT = ROOT / "smoke_test_assets" / "packaging" / "release-status-report.json"
SCHEMA_VERSION = 1
EXTERNAL_GATE_DRY_RUN_COMMAND = (
    r".\venv\Scripts\python.exe tools\external_gate_orchestrator.py "
    r"--report-json smoke_test_assets\external-gates-dry-run.json"
)
MIC_DEVICE_INVENTORY_REPORT = ROOT / "smoke_test_assets" / "microphone" / "audio-device-inventory.json"
PHYSICAL_MIC_RUN_CARD_COMMAND = (
    r".\venv\Scripts\python.exe tools\physical_microphone_run_card.py "
    r"--report-json smoke_test_assets\microphone\physical-gate-dry-run.json"
)
E4B_PREFLIGHT_COMMAND = (
    r".\venv\Scripts\python.exe tools\gemma_model_preflight.py "
    r"--model google/gemma-4-E4B-it --require-local "
    r"--report-json smoke_test_assets\gemma-e4b-preflight.json"
)
GGUF_SERVER_PROBE_COMMAND = (
    r".\venv\Scripts\python.exe tools\gguf_server_probe.py "
    r"--url http://127.0.0.1:8080/v1 --timeout 60 "
    r"--report-json smoke_test_assets\gguf\real-server-probe.json"
)


def _generated_at_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json_if_present(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _recommended_microphone_device() -> str:
    inventory = _read_json_if_present(MIC_DEVICE_INVENTORY_REPORT)
    return str(inventory.get("recommended_device_argument") or "").strip()


def _external_gate_selected_mic_command() -> str:
    device = _recommended_microphone_device() or "1"
    return (
        r".\venv\Scripts\python.exe tools\external_gate_orchestrator.py "
        f"--microphone-device {device} "
        r"--report-json smoke_test_assets\external-gates-dry-run.json"
    )


def build_release_status() -> tuple[str, list[str], dict]:
    blocker_status, blocker_failures, blocker_payload = publication_blocker_audit.audit_publication_blockers()
    validation_failures = open_gate_summary._validate_current_docs()
    failures = [*blocker_failures, *validation_failures]
    status = "invalid" if failures else blocker_status
    open_gate_payloads = open_gate_summary._gate_payloads()
    next_commands = [
        str(gate["next_command"][0])
        for gate in open_gate_payloads
        if gate.get("next_command")
    ]
    next_preparation_commands = [
        PHYSICAL_MIC_RUN_CARD_COMMAND,
        E4B_PREFLIGHT_COMMAND,
        GGUF_SERVER_PROBE_COMMAND,
    ] if next_commands else []
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _generated_at_utc(),
        "status": status,
        "publication": blocker_payload,
        "open_gate_count": len(open_gate_summary.OPEN_GATES),
        "open_gates": open_gate_payloads,
        "external_gate_dry_run_command": EXTERNAL_GATE_DRY_RUN_COMMAND,
        "external_gate_selected_microphone_command": _external_gate_selected_mic_command(),
        "next_commands": next_commands,
        "next_preparation_command": next_preparation_commands[0] if next_preparation_commands else "",
        "next_preparation_commands": next_preparation_commands,
        "next_recommended_command": next_commands[0] if next_commands else "",
        "next_recommended_commands": next_commands,
        "microphone_device_inventory_report": str(MIC_DEVICE_INVENTORY_REPORT.relative_to(ROOT)),
        "phase4_checklist": "docs/implementation-plans-and-checklists/phase-4-release-execution.md",
        "release_checklist": "docs/release/RELEASE_CHECKLIST_3.0.0-whisper.md",
        "publishing_runbook": "docs/release/PUBLISHING_RUNBOOK_3.0.0.md",
        "failures": failures,
    }
    return status, failures, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print one release status report for OmniDictate's current publish/no-publish state."
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--report-json",
        default="",
        help=f"Optional JSON output path. Defaults to no file; suggested path is {DEFAULT_REPORT.relative_to(ROOT)}.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status, failures, payload = build_release_status()
    if args.report_json:
        report_path = Path(args.report_json)
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    elif failures:
        print("Release status report is invalid:")
        for failure in failures:
            print(f"- {failure}")
    else:
        print(f"Release status: {status}")
        print(f"Final artifact status: {payload['publication'].get('final_artifact_status', '')}")
        print(f"Installer SHA256: {payload['publication'].get('installer_sha256', '')}")
        print(f"Open gates: {payload['open_gate_count']}")
        if payload["next_preparation_command"]:
            print(f"Next preparation command: {payload['next_preparation_command']}")
        print(f"Next recommended command: {payload['next_recommended_command']}")
        print(f"Dry-run all gates: {payload['external_gate_dry_run_command']}")
        print(f"Dry-run with selected microphone: {payload['external_gate_selected_microphone_command']}")
        for gate in payload["open_gates"]:
            print(f"- {gate['key']}: {gate['external_dependency']}")
            for index, command in enumerate(gate.get("next_command") or []):
                label = "Next" if index == 0 else "Then"
                print(f"  {label}: {command}")
        print(f"Checklist: {payload['phase4_checklist']}")
    return 0 if status in {"blocked", "ready"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
