from __future__ import annotations

import argparse
import hashlib
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "release" / "ARTIFACT_MANIFEST_3.0.0-whisper.md"


@dataclass(frozen=True)
class ManifestArtifact:
    name: str
    path: Path
    size: int
    sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _parse_size(text: str) -> int:
    normalized = text.replace(",", "").strip().lower()
    match = re.match(r"^(\d+)\s+bytes$", normalized)
    if not match:
        raise ValueError(f"Unsupported manifest size cell: {text!r}")
    return int(match.group(1))


def _parse_artifacts(text: str) -> list[ManifestArtifact]:
    artifacts: list[ManifestArtifact] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Artifact | Path | Size | SHA256 |"):
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("| ---"):
            continue
        if not line.startswith("|"):
            if artifacts:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            continue
        name, raw_path, raw_size, raw_hash = cells
        path_text = raw_path.strip("`")
        hash_text = raw_hash.strip("`").upper()
        artifacts.append(
            ManifestArtifact(
                name=name,
                path=ROOT / path_text,
                size=_parse_size(raw_size),
                sha256=hash_text,
            )
        )
    return artifacts


def _read_png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        header = file.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"Not a valid PNG file: {path}")
    return struct.unpack(">II", header[16:24])


def _expected_screenshot_dimensions(text: str) -> tuple[int, int] | None:
    match = re.search(r"(\d+)x(\d+)\s+RGB", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def audit_manifest(manifest_path: Path) -> list[str]:
    failures: list[str] = []
    text = manifest_path.read_text(encoding="utf-8")
    artifacts = _parse_artifacts(text)
    if not artifacts:
        failures.append("No artifact table rows found in manifest.")
        return failures

    for artifact in artifacts:
        if not artifact.path.exists():
            failures.append(f"{artifact.name}: missing file {artifact.path}")
            continue
        actual_size = artifact.path.stat().st_size
        if actual_size != artifact.size:
            failures.append(f"{artifact.name}: size mismatch manifest={artifact.size} actual={actual_size}")
        actual_hash = _sha256(artifact.path)
        if actual_hash != artifact.sha256:
            failures.append(f"{artifact.name}: sha256 mismatch manifest={artifact.sha256} actual={actual_hash}")

    expected_dimensions = _expected_screenshot_dimensions(text)
    screenshot = ROOT / "smoke_test_assets" / "ui" / "packaged-whisper-first-run.png"
    if expected_dimensions is not None:
        if not screenshot.exists():
            failures.append(f"Packaged first-run screenshot missing: {screenshot}")
        else:
            actual_dimensions = _read_png_dimensions(screenshot)
            if actual_dimensions != expected_dimensions:
                failures.append(
                    "Packaged first-run screenshot dimensions mismatch "
                    f"manifest={expected_dimensions[0]}x{expected_dimensions[1]} "
                    f"actual={actual_dimensions[0]}x{actual_dimensions[1]}"
                )
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify release artifact manifest hashes, sizes, and screenshot dimensions.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Manifest markdown file to verify.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failures = audit_manifest(Path(args.manifest))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("Artifact manifest audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
