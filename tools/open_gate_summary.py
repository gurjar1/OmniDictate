from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCOPE_DECISIONS_DOC = "docs/release/RELEASE_SCOPE_DECISIONS_3.0.0.md"
MIC_DEVICE_INVENTORY_REPORT = ROOT / "smoke_test_assets" / "microphone" / "audio-device-inventory.json"


@dataclass(frozen=True)
class Gate:
    key: str
    title: str
    status: str
    evidence: str
    next_command: list[str]
    external_dependency: str


OPEN_GATES = [
    Gate(
        key="physical-microphone",
        title="Physical microphone phrase-match VAD/PTT",
        status="open",
        evidence="docs/evidence/live-microphone-audio-device-2026-07-04.md",
        next_command=[
            r".\venv\Scripts\python.exe tools\physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --report-json smoke_test_assets\microphone\physical-gate-report.json",
        ],
        external_dependency="A human must speak the expected phrase into the selected microphone.",
    ),
    Gate(
        key="gemma-e4b-live",
        title="Gemma E4B local weights and live generation",
        status="open",
        evidence="docs/evidence/gemma-e4b-preflight-2026-07-05.md",
        next_command=[
            r".\venv\Scripts\python.exe tools\gemma_e4b_gate.py --model google/gemma-4-E4B-it --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gemma-e4b-gate-report.json",
        ],
        external_dependency="Local Gemma E4B weights must be available before live generation can be tested.",
    ),
    Gate(
        key="gguf-real-server",
        title="Real GGUF/OpenAI-compatible local server",
        status="open",
        evidence="docs/evidence/gguf-real-server-runbook-2026-07-05.md",
        next_command=[
            r'.\venv\Scripts\python.exe tools\gguf_real_server_gate.py --url http://127.0.0.1:8080/v1 --server-implementation "LM Studio" --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gguf\real-server-gate-report.json',
        ],
        external_dependency="A llama.cpp, LM Studio, or equivalent server must be running with a multimodal model.",
    ),
]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _gate_has_evidence(gate: Gate) -> bool:
    return (ROOT / gate.evidence).is_file()


def _release_scope_statuses() -> dict[str, str]:
    path = ROOT / SCOPE_DECISIONS_DOC
    if not path.is_file():
        return {}

    statuses: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `"):
            continue
        cells = [cell.strip().strip("`") for cell in stripped.strip("|").split("|")]
        if len(cells) >= 2:
            statuses[cells[0]] = cells[1]
    return statuses


def _read_json_if_present(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _command_with_recommended_microphone(command: str) -> str:
    inventory = _read_json_if_present(MIC_DEVICE_INVENTORY_REPORT)
    device_arg = str(inventory.get("recommended_device_argument", "")).strip()
    if not device_arg or " --device " in command:
        return command
    marker = " --report-json "
    if marker not in command:
        return f"{command} --device {device_arg}"
    return command.replace(marker, f" --device {device_arg}{marker}", 1)


def _effective_next_commands(gate: Gate) -> list[str]:
    if gate.key != "physical-microphone":
        return gate.next_command
    return [_command_with_recommended_microphone(command) for command in gate.next_command]


def _gate_payloads() -> list[dict[str, object]]:
    scope_statuses = _release_scope_statuses()
    payloads: list[dict[str, object]] = []
    for gate in OPEN_GATES:
        gate_payload = asdict(gate)
        gate_payload["next_command"] = _effective_next_commands(gate)
        gate_payload["release_scope_status"] = scope_statuses.get(gate.key, "")
        payloads.append(gate_payload)
    return payloads


def _validate_current_docs() -> list[str]:
    failures: list[str] = []
    completion = _read("docs/ai/COMPLETION_AUDIT.md")
    checklist = _read("docs/release/RELEASE_CHECKLIST_3.0.0-whisper.md")
    scope_statuses = _release_scope_statuses()
    expected_scope_statuses = {
        "physical-microphone": "proven",
        "gemma-e4b-live": "scoped-out",
        "gguf-real-server": "scoped-out",
    }
    for gate in OPEN_GATES:
        if not _gate_has_evidence(gate):
            failures.append(f"{gate.key}: missing evidence path {gate.evidence}")
        if scope_statuses.get(gate.key) != expected_scope_statuses[gate.key]:
            failures.append(
                f"{gate.key}: release scope status is not {expected_scope_statuses[gate.key]}"
            )

    required_completion_markers = [
        "Status: release objective locally ready",
        "Physical microphone phrase-match VAD/PTT",
        "Gemma E4B live weights",
        "Real GGUF server",
    ]
    for marker in required_completion_markers:
        if marker not in completion:
            failures.append(f"completion audit missing marker: {marker}")

    required_checklist_markers = [
        "Physical microphone phrase-match VAD and PTT both pass on real speech.",
        "physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --report-json",
        "Gemma 4 E4B is scoped out of the public Whisper-only `v3.0.0` release",
        "gemma_e4b_gate.py --model google/gemma-4-E4B-it --audio smoke_test_assets\\gemma_live_smoke.wav",
        "Real GGUF server support is scoped out of the public Whisper-only",
        "gguf_real_server_gate.py --url http://127.0.0.1:8080/v1 --server-implementation",
        "Final public `OmniDictate_Setup_v3.0.0.exe` artifact gate passed",
    ]
    for marker in required_checklist_markers:
        if marker not in checklist:
            failures.append(f"release checklist missing open-gate marker: {marker}")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print the current external gates that keep OmniDictate unreleased.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero if the open-gate docs/evidence markers are inconsistent.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failures = _validate_current_docs()
    payload = {
        "status": "goal-not-complete",
        "open_gate_count": len(OPEN_GATES),
        "scope_decisions_doc": SCOPE_DECISIONS_DOC,
        "open_gates": _gate_payloads(),
        "validation_failures": failures,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"OmniDictate open gates: {len(OPEN_GATES)}")
        for gate in OPEN_GATES:
            scope_status = _release_scope_statuses().get(gate.key, "")
            print(f"- {gate.title} [{gate.key}]")
            print(f"  Scope: {scope_status}")
            print(f"  Evidence: {gate.evidence}")
            print(f"  Dependency: {gate.external_dependency}")
            for index, command in enumerate(_effective_next_commands(gate)):
                label = "Next" if index == 0 else "Then"
                print(f"  {label}: {command}")
        if failures:
            print("")
            print("Open-gate summary validation failures:")
            for failure in failures:
                print(f"- {failure}")
    return 1 if args.strict and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
