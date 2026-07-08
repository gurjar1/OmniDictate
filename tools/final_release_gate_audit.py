from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_updates import APP_VERSION

EXPECTED_INSTALLER_NAME = f"OmniDictate_Setup_v{APP_VERSION}.exe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"Validate whether final v{APP_VERSION} artifacts are ready for publication."
    )
    parser.add_argument("--preflight-report", required=True, help="JSON from final_release_preflight.py --report-json.")
    parser.add_argument(
        "--bundle",
        default=r"smoke_test_assets\packaging\dist-whisper-final\OmniDictate",
        help="Final PyInstaller bundle directory.",
    )
    parser.add_argument(
        "--installer",
        default=rf"smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v{APP_VERSION}.exe",
        help="Final public installer executable.",
    )
    parser.add_argument("--max-bundle-mb", type=float, default=330.0)
    parser.add_argument("--max-installer-mb", type=float, default=330.0)
    parser.add_argument("--report-json", default="", help="Optional path for final artifact audit JSON.")
    return parser.parse_args()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _directory_size(path: Path) -> int:
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def audit_final_release(
    preflight_report: dict,
    bundle: Path,
    installer: Path,
    max_bundle_mb: float = 330.0,
    max_installer_mb: float = 330.0,
) -> tuple[list[str], dict]:
    failures: list[str] = []
    payload = {
        "status": "not-ready",
        "bundle": str(bundle),
        "installer": str(installer),
        "bundle_bytes": 0,
        "installer_bytes": 0,
        "installer_sha256": "",
    }

    if preflight_report.get("status") != "ready-to-run":
        failures.append("final release preflight report is not ready-to-run")
    if preflight_report.get("failures"):
        failures.append("final release preflight report contains failures")
    if str(preflight_report.get("final_installer") or "") != str(installer):
        failures.append("final installer path does not match the preflight report")
    if str(preflight_report.get("final_bundle") or "") != str(bundle):
        failures.append("final bundle path does not match the preflight report")

    if installer.name != EXPECTED_INSTALLER_NAME:
        failures.append(f"final installer must be named {EXPECTED_INSTALLER_NAME}")
    if "smoke" in installer.name.lower() or "whisper-release-smoke" in str(installer).lower():
        failures.append("final installer path must not use smoke artifact naming")
    if not bundle.exists() or not bundle.is_dir():
        failures.append(f"final bundle directory is missing: {bundle}")
    else:
        bundle_bytes = _directory_size(bundle)
        payload["bundle_bytes"] = bundle_bytes
        if bundle_bytes <= 0:
            failures.append("final bundle directory has no files")
        if bundle_bytes > max_bundle_mb * 1024 * 1024:
            failures.append(f"final bundle exceeds {max_bundle_mb:.0f} MB")
        internal_dir = bundle / "_internal"
        if not (bundle / "OmniDictate.exe").is_file():
            failures.append("final bundle is missing OmniDictate.exe")
        if not (internal_dir / "python311.dll").is_file():
            failures.append("final bundle is missing _internal\\python311.dll")
        av_candidates = list(internal_dir.glob("av*")) if internal_dir.exists() else []
        if not av_candidates:
            failures.append("final bundle is missing PyAV files required by Faster-Whisper")
    if not installer.exists() or not installer.is_file():
        failures.append(f"final installer is missing: {installer}")
    else:
        installer_bytes = installer.stat().st_size
        payload["installer_bytes"] = installer_bytes
        payload["installer_sha256"] = _sha256(installer)
        if installer_bytes <= 0:
            failures.append("final installer has zero bytes")
        if installer_bytes > max_installer_mb * 1024 * 1024:
            failures.append(f"final installer exceeds {max_installer_mb:.0f} MB")

    if not failures:
        payload["status"] = "ready"
    return failures, payload


def main() -> int:
    args = parse_args()
    failures, payload = audit_final_release(
        _read_json(Path(args.preflight_report)),
        Path(args.bundle),
        Path(args.installer),
        max_bundle_mb=args.max_bundle_mb,
        max_installer_mb=args.max_installer_mb,
    )
    payload["failures"] = failures
    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if failures:
        print("Final release gate audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Final release gate audit passed.")
    print(f"Installer SHA256: {payload['installer_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
