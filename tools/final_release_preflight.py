from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYINSTALLER = ROOT / "venv" / "Scripts" / "pyinstaller.exe"
PYTHON = ROOT / "venv" / "Scripts" / "python.exe"
ISCC = Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")
FINAL_DIST = Path(r"smoke_test_assets\packaging\dist-whisper-final")
FINAL_BUNDLE = FINAL_DIST / "OmniDictate"
FINAL_BUILD = Path(r"smoke_test_assets\packaging\build-whisper-final")
FINAL_INSTALLER_DIR = Path(r"smoke_test_assets\packaging\installer-whisper-final")
FINAL_INSTALLER = FINAL_INSTALLER_DIR / "OmniDictate_Setup_v3.0.0.exe"


def _repo_rel(path: Path) -> str:
    return str(path).replace("/", "\\")


def _final_commands() -> list[str]:
    return [
        r"$env:OMNIDICTATE_PACKAGE_PROFILE='whisper-only'",
        rf".\venv\Scripts\pyinstaller.exe --clean --noconfirm --distpath {_repo_rel(FINAL_DIST)} --workpath {_repo_rel(FINAL_BUILD)} OmniDictate.spec",
        rf"& '{ISCC}' /DAppVersion='3.0.0' /DSourceDir='{_repo_rel(FINAL_BUNDLE)}' /DInstallerOutputDir='{_repo_rel(FINAL_INSTALLER_DIR)}' /DCompressionMode=none /DSolidCompressionMode=no OmniDictate_Setup.iss",
        rf".\venv\Scripts\python.exe tools\packaged_app_smoke.py --installer {_repo_rel(FINAL_INSTALLER)} --install-dir ""$env:LOCALAPPDATA\OmniDictateFinalSmoke"" --screenshot smoke_test_assets\\ui\\packaged-whisper-final.png --launch-timeout 180 --package-smoke-model large-v3-turbo --package-smoke-load-whisper",
        rf"powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1 -InstallerPath {_repo_rel(FINAL_INSTALLER)} -InstallDir ""$env:LOCALAPPDATA\OmniDictate"" -UseInstallerDefaults",
        rf".\venv\Scripts\python.exe tools\package_size_audit.py {_repo_rel(FINAL_BUNDLE)} --top 8 --fail-over-mb 330",
        rf"Get-FileHash {_repo_rel(FINAL_INSTALLER)} -Algorithm SHA256",
    ]


def _validate_static_inputs() -> list[str]:
    failures: list[str] = []
    required_paths = [
        ROOT / "OmniDictate.spec",
        ROOT / "OmniDictate_Setup.iss",
        ROOT / "tools" / "installer_smoke.ps1",
        ROOT / "tools" / "package_size_audit.py",
        ROOT / "tools" / "verify_local.ps1",
        ROOT / "tools" / "verify_whisper.ps1",
    ]
    for path in required_paths:
        if not path.exists():
            failures.append(f"Missing required release input: {path}")
    if not PYINSTALLER.exists():
        failures.append(f"Missing PyInstaller executable: {PYINSTALLER}")
    if not PYTHON.exists():
        failures.append(f"Missing venv Python executable: {PYTHON}")
    if not ISCC.exists():
        failures.append(f"Missing Inno Setup compiler: {ISCC}")

    spec_text = (ROOT / "OmniDictate.spec").read_text(encoding="utf-8")
    if 'OMNIDICTATE_PACKAGE_PROFILE' not in spec_text or '"whisper-only"' not in spec_text:
        failures.append("OmniDictate.spec does not expose the whisper-only package profile.")

    iss_text = (ROOT / "OmniDictate_Setup.iss").read_text(encoding="utf-8")
    for snippet in [
        '#define AppVersion "3.0.0"',
        '#define DefaultDir "{localappdata}\\OmniDictate"',
        '#define PrivilegesRequiredMode "lowest"',
        "OutputBaseFilename=OmniDictate_Setup_v{#AppVersion}",
    ]:
        if snippet not in iss_text:
            failures.append(f"OmniDictate_Setup.iss missing release marker: {snippet}")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and print the final v3.0.0 release build sequence without building.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--report-json", default="", help="Optional path for a JSON preflight report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failures = _validate_static_inputs()
    payload = {
        "status": "ready-to-run" if not failures else "preflight-failed",
        "final_installer": _repo_rel(FINAL_INSTALLER),
        "final_bundle": _repo_rel(FINAL_BUNDLE),
        "final_dist": _repo_rel(FINAL_DIST),
        "final_installer_dir": _repo_rel(FINAL_INSTALLER_DIR),
        "commands": _final_commands(),
        "warnings": [
            "Do not run the final build until open release-scope gates pass or are explicitly scoped out.",
            "After final build, update docs/release/ARTIFACT_MANIFEST_3.0.0-whisper.md with final artifact hashes.",
        ],
        "failures": failures,
    }
    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("OmniDictate final v3.0.0 release preflight")
        print(f"Status: {payload['status']}")
        print(f"Final installer: {payload['final_installer']}")
        print("")
        print("Commands:")
        for command in payload["commands"]:
            print(f"- {command}")
        if payload["warnings"]:
            print("")
            print("Warnings:")
            for warning in payload["warnings"]:
                print(f"- {warning}")
        if failures:
            print("")
            print("Failures:")
            for failure in failures:
                print(f"- {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
