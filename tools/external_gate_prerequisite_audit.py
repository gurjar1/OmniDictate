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

from tools import open_gate_summary


SCHEMA_VERSION = 1
DEFAULT_REPORT = ROOT / "smoke_test_assets" / "external-gate-prerequisites.json"
DEFAULT_MODEL_STORAGE = ROOT / "smoke_test_assets" / "models"
E4B_MODEL_DIR = DEFAULT_MODEL_STORAGE / "gemma-4-E4B-it"


GATE_EVIDENCE = {
    "physical-microphone": {
        "required_reports": [
            ROOT / "smoke_test_assets" / "microphone" / "spoken-phrase-large-v3-turbo-report.json",
            ROOT / "smoke_test_assets" / "microphone" / "live-loop-large-v3-turbo-report.json",
            ROOT / "smoke_test_assets" / "microphone" / "physical-gate-report.json",
        ],
        "required_files": [
            ROOT / "smoke_test_assets" / "microphone" / "spoken-phrase-large-v3-turbo.wav",
        ],
        "closure_report": ROOT / "smoke_test_assets" / "microphone" / "physical-gate-report.json",
        "closure_audit_command": (
            r".\venv\Scripts\python.exe tools\microphone_gate_report_audit.py "
            r"--capture-report smoke_test_assets\microphone\spoken-phrase-large-v3-turbo-report.json "
            r"--loop-report smoke_test_assets\microphone\live-loop-large-v3-turbo-report.json"
        ),
        "device_inventory_report": ROOT / "smoke_test_assets" / "microphone" / "audio-device-inventory.json",
        "prerequisite": "Human must speak the gate phrase into the selected microphone.",
    },
    "gemma-e4b-live": {
        "required_reports": [
            ROOT / "smoke_test_assets" / "gemma-e4b-preflight.json",
            ROOT / "smoke_test_assets" / "gemma-e4b-live-smoke.json",
            ROOT / "smoke_test_assets" / "gemma-e4b-gate-report.json",
        ],
        "required_files": [
            ROOT / "smoke_test_assets" / "gemma_live_smoke.wav",
            ROOT / "smoke_test_assets" / "gemma_live_smoke.png",
        ],
        "closure_report": ROOT / "smoke_test_assets" / "gemma-e4b-gate-report.json",
        "closure_audit_command": (
            r".\venv\Scripts\python.exe tools\gemma_e4b_gate_report_audit.py "
            r"--preflight-report smoke_test_assets\gemma-e4b-preflight.json "
            r"--smoke-report smoke_test_assets\gemma-e4b-live-smoke.json"
        ),
        "prerequisite": "Local Gemma E4B safetensors must exist before live generation.",
    },
    "gguf-real-server": {
        "required_reports": [
            ROOT / "smoke_test_assets" / "gguf" / "real-server-probe.json",
            ROOT / "smoke_test_assets" / "gguf" / "real-server-smoke.json",
            ROOT / "smoke_test_assets" / "gguf" / "real-server-gate-report.json",
        ],
        "required_files": [
            ROOT / "smoke_test_assets" / "gemma_live_smoke.wav",
            ROOT / "smoke_test_assets" / "gemma_live_smoke.png",
        ],
        "closure_report": ROOT / "smoke_test_assets" / "gguf" / "real-server-gate-report.json",
        "closure_audit_command": (
            r'.\venv\Scripts\python.exe tools\gguf_gate_report_audit.py '
            r"--probe-report smoke_test_assets\gguf\real-server-probe.json "
            r"--smoke-report smoke_test_assets\gguf\real-server-smoke.json "
            r'--server-implementation "LM Studio"'
        ),
        "prerequisite": "A named real OpenAI-compatible local server must be running.",
    },
}


def _generated_at_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _path_status(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": _display_path(path),
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else 0,
        }
        for path in paths
    ]


def _model_dir_summary(path: Path) -> dict[str, Any]:
    files = [child for child in path.rglob("*") if child.is_file()] if path.exists() else []
    safetensors = [child for child in files if child.suffix == ".safetensors"]
    return {
        "path": _display_path(path),
        "exists": path.exists(),
        "files": len(files),
        "bytes": sum(child.stat().st_size for child in files),
        "safetensors": len(safetensors),
        "has_safetensors": bool(safetensors),
    }


def _all_present(items: list[dict[str, Any]]) -> bool:
    return all(bool(item.get("exists")) for item in items)


def build_prerequisite_audit(model_storage: Path = DEFAULT_MODEL_STORAGE) -> tuple[str, list[str], dict[str, Any]]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    scope_statuses = open_gate_summary._release_scope_statuses()
    gate_payloads = {str(gate["key"]): gate for gate in open_gate_summary._gate_payloads()}
    model_dir = model_storage / "gemma-4-E4B-it"
    model_summary = _model_dir_summary(model_dir)

    for gate in open_gate_summary.OPEN_GATES:
        spec = GATE_EVIDENCE[gate.key]
        required_files = _path_status(spec["required_files"])
        required_reports = _path_status(spec["required_reports"])
        missing_files = [item["path"] for item in required_files if not item["exists"]]
        missing_reports = [item["path"] for item in required_reports if not item["exists"]]
        prerequisites: list[str] = [spec["prerequisite"]]
        ready_for_live_attempt = _all_present(required_files)

        if gate.key == "gemma-e4b-live":
            ready_for_live_attempt = ready_for_live_attempt and model_summary["has_safetensors"]
            if not model_summary["has_safetensors"]:
                prerequisites.append(f"Missing local safetensors under {_display_path(model_dir)}.")
        elif gate.key == "gguf-real-server":
            ready_for_live_attempt = False
            prerequisites.append("Server readiness cannot be proven without executing the real gate.")
        elif gate.key == "physical-microphone":
            ready_for_live_attempt = False
            prerequisites.append("Microphone readiness cannot be proven without a prompted physical run.")

        row = {
            "key": gate.key,
            "title": gate.title,
            "release_scope_status": scope_statuses.get(gate.key, ""),
            "evidence": gate.evidence,
            "ready_for_live_attempt": ready_for_live_attempt,
            "required_files": required_files,
            "required_reports": required_reports,
            "missing_files": missing_files,
            "missing_reports": missing_reports,
            "prerequisites": prerequisites,
            "closure_report": _display_path(spec["closure_report"]),
            "closure_audit_command": spec["closure_audit_command"],
            "next_command": (
                str(gate_payloads.get(gate.key, {}).get("next_command", [""])[0])
                if gate_payloads.get(gate.key, {}).get("next_command")
                else ""
            ),
        }
        if "device_inventory_report" in spec:
            row["device_inventory_report"] = _path_status([spec["device_inventory_report"]])[0]
        rows.append(row)

    if {row["key"] for row in rows} != set(GATE_EVIDENCE):
        failures.append("external gate prerequisite audit is out of sync with open gate set")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _generated_at_utc(),
        "status": "passed" if not failures else "invalid",
        "open_gate_count": len(rows),
        "model_storage": _display_path(model_storage),
        "gemma_e4b_model_dir": model_summary,
        "gate_rows": rows,
        "failures": failures,
    }
    return payload["status"], failures, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit remaining external-gate prerequisites without opening devices, loading models, or contacting servers."
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--report-json", default="", help=f"Optional JSON output path; suggested {DEFAULT_REPORT.relative_to(ROOT)}.")
    parser.add_argument("--model-storage", default=str(DEFAULT_MODEL_STORAGE), help="Local model storage directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status, failures, payload = build_prerequisite_audit(Path(args.model_storage))
    if args.report_json:
        report_path = Path(args.report_json)
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    elif failures:
        print("External gate prerequisite audit is invalid:")
        for failure in failures:
            print(f"- {failure}")
    else:
        print("External gate prerequisite audit passed.")
        for row in payload["gate_rows"]:
            print(f"- {row['key']} [{row['release_scope_status']}]")
            print(f"  Ready for live attempt: {row['ready_for_live_attempt']}")
            if row["missing_files"]:
                print(f"  Missing files: {', '.join(row['missing_files'])}")
            if row["missing_reports"]:
                print(f"  Missing reports: {', '.join(row['missing_reports'])}")
            print(f"  Closure report: {row['closure_report']}")
            if row.get("device_inventory_report"):
                inventory = row["device_inventory_report"]
                print(f"  Device inventory: {inventory['path']}")
            print(f"  Audit: {row['closure_audit_command']}")
            print(f"  Next: {row['next_command']}")
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
