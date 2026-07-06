from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import open_gate_summary


MIC_DEVICE_INVENTORY_REPORT = ROOT / "smoke_test_assets" / "microphone" / "audio-device-inventory.json"


@dataclass(frozen=True)
class GateCommand:
    key: str
    title: str
    dependency: str
    command: list[str]
    dry_run_command: list[str]


def _python() -> str:
    return sys.executable


def _read_json_if_present(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def recommended_microphone_device() -> str:
    inventory = _read_json_if_present(MIC_DEVICE_INVENTORY_REPORT)
    return str(inventory.get("recommended_device_argument", "")).strip()


def _gate_commands(microphone_device: str = "") -> dict[str, GateCommand]:
    python = _python()
    physical_command = [
        python,
        str(ROOT / "tools" / "physical_microphone_gate.py"),
        "--model",
        "large-v3-turbo",
        "--duration",
        "7",
        "--countdown",
        "3",
        "--timeout",
        "40",
        "--report-json",
        str(ROOT / "smoke_test_assets" / "microphone" / "physical-gate-report.json"),
    ]
    physical_dry_run_command = [
        python,
        str(ROOT / "tools" / "physical_microphone_gate.py"),
        "--model",
        "large-v3-turbo",
        "--duration",
        "7",
        "--countdown",
        "3",
        "--timeout",
        "40",
        "--report-json",
        str(ROOT / "smoke_test_assets" / "microphone" / "physical-gate-dry-run.json"),
        "--dry-run",
    ]
    if microphone_device:
        physical_command.extend(["--device", microphone_device])
        physical_dry_run_command.extend(["--device", microphone_device])

    return {
        "physical-microphone": GateCommand(
            key="physical-microphone",
            title="Physical microphone phrase-match VAD/PTT",
            dependency="A human must speak the expected phrase into the selected microphone.",
            command=physical_command,
            dry_run_command=physical_dry_run_command,
        ),
        "gemma-e4b-live": GateCommand(
            key="gemma-e4b-live",
            title="Gemma E4B local weights and live generation",
            dependency="Local Gemma E4B weights must be available before live generation can be tested.",
            command=[
                python,
                str(ROOT / "tools" / "gemma_e4b_gate.py"),
                "--model",
                "google/gemma-4-E4B-it",
                "--audio",
                str(ROOT / "smoke_test_assets" / "gemma_live_smoke.wav"),
                "--image",
                str(ROOT / "smoke_test_assets" / "gemma_live_smoke.png"),
                "--report-json",
                str(ROOT / "smoke_test_assets" / "gemma-e4b-gate-report.json"),
            ],
            dry_run_command=[
                python,
                str(ROOT / "tools" / "gemma_e4b_gate.py"),
                "--model",
                "google/gemma-4-E4B-it",
                "--audio",
                str(ROOT / "smoke_test_assets" / "gemma_live_smoke.wav"),
                "--image",
                str(ROOT / "smoke_test_assets" / "gemma_live_smoke.png"),
                "--report-json",
                str(ROOT / "smoke_test_assets" / "gemma-e4b-gate-dry-run.json"),
                "--dry-run",
            ],
        ),
        "gguf-real-server": GateCommand(
            key="gguf-real-server",
            title="Real GGUF/OpenAI-compatible local server",
            dependency="A llama.cpp, LM Studio, or equivalent server must be running with a multimodal model.",
            command=[
                python,
                str(ROOT / "tools" / "gguf_real_server_gate.py"),
                "--url",
                "http://127.0.0.1:8080/v1",
                "--server-implementation",
                "LM Studio",
                "--audio",
                str(ROOT / "smoke_test_assets" / "gemma_live_smoke.wav"),
                "--image",
                str(ROOT / "smoke_test_assets" / "gemma_live_smoke.png"),
                "--report-json",
                str(ROOT / "smoke_test_assets" / "gguf" / "real-server-gate-report.json"),
            ],
            dry_run_command=[
                python,
                str(ROOT / "tools" / "gguf_real_server_gate.py"),
                "--url",
                "http://127.0.0.1:8080/v1",
                "--server-implementation",
                "LM Studio",
                "--audio",
                str(ROOT / "smoke_test_assets" / "gemma_live_smoke.wav"),
                "--image",
                str(ROOT / "smoke_test_assets" / "gemma_live_smoke.png"),
                "--report-json",
                str(ROOT / "smoke_test_assets" / "gguf" / "real-server-gate-dry-run.json"),
                "--dry-run",
            ],
        ),
        "final-public-release": GateCommand(
            key="final-public-release",
            title="Final public v3.0.0 release artifact",
            dependency="Run only after remaining release-scope gates pass or are explicitly scoped out.",
            command=[
                python,
                str(ROOT / "tools" / "final_public_release_gate.py"),
                "--report-json",
                str(ROOT / "smoke_test_assets" / "packaging" / "final-public-release-gate-report.json"),
            ],
            dry_run_command=[
                python,
                str(ROOT / "tools" / "final_public_release_gate.py"),
                "--report-json",
                str(ROOT / "smoke_test_assets" / "packaging" / "final-public-release-gate-dry-run.json"),
                "--dry-run",
            ],
        ),
    }


def _display_command(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    gate_keys = ["all", *[gate.key for gate in open_gate_summary.OPEN_GATES]]
    parser = argparse.ArgumentParser(description="Dry-run or execute OmniDictate's remaining external gates.")
    parser.add_argument("--gate", choices=gate_keys, default="all")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run real gate commands. Default is dry-run only.",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="When executing, continue after a gate returns non-zero.",
    )
    parser.add_argument(
        "--microphone-device",
        default="",
        help=(
            "Optional sounddevice input device index for the physical microphone gate. "
            "Use a device name only when the inventory shows it is unique."
        ),
    )
    parser.add_argument("--report-json", default="", help="Optional aggregate JSON report.")
    return parser.parse_args(argv)


def selected_gates(key: str, microphone_device: str = "") -> list[GateCommand]:
    commands = _gate_commands(microphone_device or recommended_microphone_device())
    if key == "all":
        return [commands[gate.key] for gate in open_gate_summary.OPEN_GATES]
    return [commands[key]]


def _release_scope_status(key: str) -> str:
    return open_gate_summary._release_scope_statuses().get(key, "")


def _gate_payload(gate: GateCommand, command: list[str]) -> dict[str, str]:
    return {
        "key": gate.key,
        "title": gate.title,
        "release_scope_status": _release_scope_status(gate.key),
        "dependency": gate.dependency,
        "command": _display_command(command),
    }


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    microphone_device = args.microphone_device or recommended_microphone_device()
    gates = selected_gates(args.gate, microphone_device)
    mode = "execute" if args.execute else "dry-run"
    results: list[dict[str, object]] = []
    payload = {
        "status": "running" if args.execute else "dry-run",
        "mode": mode,
        "gate_count": len(gates),
        "microphone_device": microphone_device,
        "microphone_device_source": "argument" if args.microphone_device else ("inventory" if microphone_device else ""),
        "microphone_device_inventory_report": str(MIC_DEVICE_INVENTORY_REPORT.relative_to(ROOT)),
        "gates": [],
        "results": results,
    }

    print(f"External gate orchestrator mode: {mode}")
    for gate in gates:
        command = gate.command if args.execute else gate.dry_run_command
        payload["gates"].append(_gate_payload(gate, command))
        print(f"- {gate.title} [{gate.key}]")
        print(f"  Scope: {_release_scope_status(gate.key)}")
        print(f"  Dependency: {gate.dependency}")
        print(f"  Command: {_display_command(command)}")

    if not args.execute:
        for gate in gates:
            command = gate.dry_run_command
            print("")
            print(f"==> Dry-run {gate.key}")
            result = subprocess.run(command, cwd=ROOT, check=False)
            results.append(
                {
                    "key": gate.key,
                    "command": _display_command(command),
                    "returncode": result.returncode,
                }
            )
            if result.returncode != 0 and not args.continue_on_failure:
                payload["status"] = "failed"
                if args.report_json:
                    _write_report(Path(args.report_json), payload)
                return result.returncode
        payload["status"] = "dry-run-passed"
        if args.report_json:
            _write_report(Path(args.report_json), payload)
            print(f"Wrote report: {Path(args.report_json).resolve()}")
        return 0

    for gate in gates:
        command = gate.command
        print("")
        print(f"==> Execute {gate.key}")
        result = subprocess.run(command, cwd=ROOT, check=False)
        results.append(
            {
                "key": gate.key,
                "command": _display_command(command),
                "returncode": result.returncode,
            }
        )
        if result.returncode != 0 and not args.continue_on_failure:
            payload["status"] = "failed"
            if args.report_json:
                _write_report(Path(args.report_json), payload)
            return result.returncode

    payload["status"] = "passed" if all(item["returncode"] == 0 for item in results) else "failed"
    if args.report_json:
        _write_report(Path(args.report_json), payload)
        print(f"Wrote report: {Path(args.report_json).resolve()}")
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
