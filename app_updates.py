from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass


APP_VERSION = "3.0.2"
GITHUB_RELEASES_URL = "https://github.com/gurjar1/OmniDictate/releases"
GITHUB_LATEST_RELEASE_API = "https://api.github.com/repos/gurjar1/OmniDictate/releases/latest"


@dataclass(slots=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_url: str
    update_available: bool


def parse_version(value: str) -> tuple[int, int, int, str]:
    cleaned = (value or "").strip()
    if cleaned.lower().startswith("v"):
        cleaned = cleaned[1:]
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?([.-].*)?$", cleaned)
    if not match:
        return (0, 0, 0, cleaned)
    major = int(match.group(1) or 0)
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    suffix = match.group(4) or ""
    return (major, minor, patch, suffix)


def is_newer_version(latest: str, current: str) -> bool:
    latest_parts = parse_version(latest)
    current_parts = parse_version(current)
    return latest_parts[:3] > current_parts[:3]


def update_info_from_release(payload: dict, current_version: str = APP_VERSION) -> UpdateInfo:
    latest_version = str(payload.get("tag_name") or payload.get("name") or "").strip()
    release_url = str(payload.get("html_url") or GITHUB_RELEASES_URL).strip() or GITHUB_RELEASES_URL
    return UpdateInfo(
        current_version=current_version,
        latest_version=latest_version,
        release_url=release_url,
        update_available=is_newer_version(latest_version, current_version),
    )


def check_latest_release(current_version: str = APP_VERSION, timeout: float = 5.0) -> UpdateInfo:
    request = urllib.request.Request(
        GITHUB_LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"OmniDictate/{current_version}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return update_info_from_release(payload, current_version=current_version)
