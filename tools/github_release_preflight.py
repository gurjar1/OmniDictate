from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import release_status_report
from app_updates import APP_VERSION


DEFAULT_REPORT = ROOT / "smoke_test_assets" / "packaging" / "github-release-preflight.json"
DEFAULT_TAG = f"v{APP_VERSION}"
LAST_PUBLIC_TAG = "v3.0.1"
INSTALLER = ROOT / "smoke_test_assets" / "packaging" / "installer-whisper-final" / f"OmniDictate_Setup_v{APP_VERSION}.exe"
SCHEMA_VERSION = 1


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _tag_exists(remote: str, tag: str) -> tuple[bool, str, str]:
    result = _git(["ls-remote", "--tags", remote, f"refs/tags/{tag}"])
    output = result.stdout.strip()
    if result.returncode != 0:
        return False, output, result.stderr.strip()
    return bool(output), output, ""


def _generated_at_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def build_github_release_preflight(remote: str = "origin", tag: str = DEFAULT_TAG) -> tuple[str, list[str], dict]:
    failures: list[str] = []
    warnings: list[str] = []
    release_status, release_failures, release_payload = release_status_report.build_release_status()
    failures.extend(release_failures)
    publication_payload = release_payload.get("publication", {})
    scope_gate_statuses = publication_payload.get("scope_gate_statuses", {})
    pending_scope_gates = sorted(
        gate_key for gate_key, gate_status in scope_gate_statuses.items() if gate_status == "pending"
    )

    remote_result = _git(["remote", "get-url", remote])
    remote_url = remote_result.stdout.strip()
    if remote_result.returncode != 0 or not remote_url:
        failures.append(f"git remote is not configured: {remote}")

    tag_exists, tag_output, tag_error = _tag_exists(remote, tag)
    if tag_error:
        failures.append(f"could not query remote tag {tag}: {tag_error}")

    last_tag_exists, last_tag_output, last_tag_error = _tag_exists(remote, LAST_PUBLIC_TAG)
    if last_tag_error:
        warnings.append(f"could not query last public tag {LAST_PUBLIC_TAG}: {last_tag_error}")
    elif not last_tag_exists:
        warnings.append(f"last public tag was not found on remote: {LAST_PUBLIC_TAG}")

    if tag_exists:
        failures.append(f"release tag already exists on remote: {tag}")
    if not INSTALLER.is_file():
        failures.append(f"final installer is missing: {INSTALLER}")

    publish_ready = release_status == "ready" and not failures and not tag_exists
    if release_status == "blocked":
        warnings.append("publication is blocked by remaining release-scope gates")
    elif release_status != "ready":
        failures.append(f"release status is not publishable: {release_status}")

    status = "ready" if publish_ready else "blocked"
    if failures:
        status = "invalid"

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _generated_at_utc(),
        "status": status,
        "publish_ready": publish_ready,
        "remote": remote,
        "remote_url": remote_url,
        "tag": tag,
        "tag_exists": tag_exists,
        "tag_query": tag_output,
        "last_public_tag": LAST_PUBLIC_TAG,
        "last_public_tag_exists": last_tag_exists,
        "last_public_tag_query": last_tag_output,
        "release_status": release_status,
        "publication_status": publication_payload.get("status", ""),
        "scope_decisions_doc": publication_payload.get("scope_decisions_doc", ""),
        "scope_gate_statuses": scope_gate_statuses,
        "pending_release_scope_gates": pending_scope_gates,
        "release_status_report": release_payload,
        "installer": _display_path(INSTALLER),
        "installer_exists": INSTALLER.is_file(),
        "suggested_release_title": f"OmniDictate v{APP_VERSION}",
        "release_notes": f"docs/release/RELEASE_NOTES_{APP_VERSION}.md",
        "publishing_runbook": "docs/release/PUBLISHING_RUNBOOK_3.0.0.md",
        "warnings": warnings,
        "failures": failures,
    }
    return status, failures, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight the GitHub release state without publishing.")
    parser.add_argument("--remote", default="origin", help="Git remote to inspect.")
    parser.add_argument("--tag", default=DEFAULT_TAG, help="Release tag to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--report-json",
        default="",
        help=f"Optional JSON output path. Suggested path: {DEFAULT_REPORT.relative_to(ROOT)}.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status, failures, payload = build_github_release_preflight(args.remote, args.tag)
    if args.report_json:
        report_path = Path(args.report_json)
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    elif failures:
        print("GitHub release preflight is invalid:")
        for failure in failures:
            print(f"- {failure}")
    else:
        print(f"GitHub release preflight: {status}")
        print(f"Remote: {payload['remote_url']}")
        print(f"Tag {payload['tag']} exists: {payload['tag_exists']}")
        print(f"Last public tag {payload['last_public_tag']} exists: {payload['last_public_tag_exists']}")
        print(f"Release status: {payload['release_status']}")
        for warning in payload["warnings"]:
            print(f"Warning: {warning}")
    return 0 if status in {"blocked", "ready"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
