from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "venv" / "Scripts" / "python.exe"
PYINSTALLER = ROOT / "venv" / "Scripts" / "pyinstaller.exe"
ISCC = Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")
FINAL_DIST = Path(r"smoke_test_assets\packaging\dist-whisper-final")
FINAL_BUNDLE = FINAL_DIST / "OmniDictate"
FINAL_BUILD = Path(r"smoke_test_assets\packaging\build-whisper-final")
FINAL_INSTALLER_DIR = Path(r"smoke_test_assets\packaging\installer-whisper-final")
FINAL_INSTALLER = FINAL_INSTALLER_DIR / "OmniDictate_Setup_v3.0.0.exe"
FINAL_INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "OmniDictate"
FINAL_SMOKE_INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "OmniDictateFinalSmoke"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the final public v3.0.0 release artifact gate.")
    parser.add_argument(
        "--preflight-report",
        default=r"smoke_test_assets\packaging\final-release-preflight.json",
    )
    parser.add_argument(
        "--gate-report",
        default=r"smoke_test_assets\packaging\final-release-gate-report.json",
    )
    parser.add_argument("--max-bundle-mb", type=float, default=330.0)
    parser.add_argument("--max-installer-mb", type=float, default=330.0)
    parser.add_argument("--report-json", default="", help="Optional wrapper summary JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Print/write commands without building artifacts.")
    return parser.parse_args(argv)


def _fmt_float(value: float) -> str:
    return f"{value:g}"


def _repo_rel(path: Path) -> str:
    return str(path).replace("/", "\\")


def build_commands(args: argparse.Namespace) -> tuple[list[dict[str, object]], dict[str, str]]:
    preflight_report = Path(args.preflight_report)
    gate_report = Path(args.gate_report)
    commands: list[dict[str, object]] = [
        {
            "name": "final release preflight",
            "command": [
                str(PYTHON),
                str(ROOT / "tools" / "final_release_preflight.py"),
                "--report-json",
                str(preflight_report),
            ],
        },
        {
            "name": "PyInstaller final whisper-only bundle",
            "command": [
                str(PYINSTALLER),
                "--clean",
                "--noconfirm",
                "--distpath",
                _repo_rel(FINAL_DIST),
                "--workpath",
                _repo_rel(FINAL_BUILD),
                "OmniDictate.spec",
            ],
            "env": {"OMNIDICTATE_PACKAGE_PROFILE": "whisper-only"},
        },
        {
            "name": "Inno Setup final installer",
            "command": [
                str(ISCC),
                "/DAppVersion=3.0.0",
                f"/DSourceDir={_repo_rel(FINAL_BUNDLE)}",
                f"/DInstallerOutputDir={_repo_rel(FINAL_INSTALLER_DIR)}",
                "/DCompressionMode=none",
                "/DSolidCompressionMode=no",
                "OmniDictate_Setup.iss",
            ],
        },
        {
            "name": "final packaged Whisper runtime smoke",
            "command": [
                str(PYTHON),
                str(ROOT / "tools" / "packaged_app_smoke.py"),
                "--installer",
                _repo_rel(FINAL_INSTALLER),
                "--install-dir",
                str(FINAL_SMOKE_INSTALL_DIR),
                "--screenshot",
                r"smoke_test_assets\ui\packaged-whisper-final.png",
                "--launch-timeout",
                "180",
                "--package-smoke-model",
                "large-v3-turbo",
                "--package-smoke-load-whisper",
            ],
        },
        {
            "name": "final installer smoke",
            "command": [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "tools" / "installer_smoke.ps1"),
                "-InstallerPath",
                _repo_rel(FINAL_INSTALLER),
                "-InstallDir",
                str(FINAL_INSTALL_DIR),
                "-UseInstallerDefaults",
                "-AllowRemoveExisting",
            ],
        },
        {
            "name": "final bundle size audit",
            "command": [
                str(PYTHON),
                str(ROOT / "tools" / "package_size_audit.py"),
                _repo_rel(FINAL_BUNDLE),
                "--top",
                "8",
                "--fail-over-mb",
                _fmt_float(args.max_bundle_mb),
            ],
        },
        {
            "name": "final installer hash",
            "command": [
                str(PYTHON),
                str(ROOT / "tools" / "file_sha256.py"),
                _repo_rel(FINAL_INSTALLER),
            ],
        },
        {
            "name": "final artifact gate audit",
            "command": [
                str(PYTHON),
                str(ROOT / "tools" / "final_release_gate_audit.py"),
                "--preflight-report",
                str(preflight_report),
                "--bundle",
                _repo_rel(FINAL_BUNDLE),
                "--installer",
                _repo_rel(FINAL_INSTALLER),
                "--max-bundle-mb",
                _fmt_float(args.max_bundle_mb),
                "--max-installer-mb",
                _fmt_float(args.max_installer_mb),
                "--report-json",
                str(gate_report),
            ],
        },
    ]
    paths = {
        "preflight_report": str(preflight_report),
        "gate_report": str(gate_report),
        "bundle": _repo_rel(FINAL_BUNDLE),
        "installer": _repo_rel(FINAL_INSTALLER),
    }
    return commands, paths


def _display_command(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    commands, paths = build_commands(args)
    results: list[dict[str, object]] = []
    payload = {
        "status": "dry-run" if args.dry_run else "running",
        "paths": paths,
        "commands": [
            {
                "name": str(item["name"]),
                "command": _display_command(item["command"]),  # type: ignore[arg-type]
                "env": item.get("env", {}),
            }
            for item in commands
        ],
        "results": results,
    }

    print("Final public release gate sequence:")
    for item in commands:
        env = item.get("env") or {}
        env_text = f" env={env}" if env else ""
        print(f"- {item['name']}: {_display_command(item['command'])}{env_text}")  # type: ignore[arg-type]

    if args.dry_run:
        if args.report_json:
            _write_report(Path(args.report_json), payload)
            print(f"Wrote report: {Path(args.report_json).resolve()}")
        return 0

    for index, item in enumerate(commands, start=1):
        command = item["command"]  # type: ignore[assignment]
        env = os.environ.copy()
        env.update(item.get("env") or {})  # type: ignore[arg-type]
        print("")
        print(f"==> Step {index}/{len(commands)}: {item['name']}")
        print(_display_command(command))  # type: ignore[arg-type]
        result = subprocess.run(command, cwd=ROOT, env=env, check=False)  # type: ignore[arg-type]
        results.append(
            {
                "name": str(item["name"]),
                "command": _display_command(command),  # type: ignore[arg-type]
                "returncode": result.returncode,
            }
        )
        if result.returncode != 0:
            payload["status"] = "failed"
            if args.report_json:
                _write_report(Path(args.report_json), payload)
                print(f"Wrote report: {Path(args.report_json).resolve()}")
            return result.returncode

    payload["status"] = "passed"
    if args.report_json:
        _write_report(Path(args.report_json), payload)
        print(f"Wrote report: {Path(args.report_json).resolve()}")
    print("Final public release gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
