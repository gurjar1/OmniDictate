from __future__ import annotations

import argparse
from pathlib import Path


def _directory_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def _format_mb(size: int) -> str:
    return f"{size / (1024 * 1024):.1f} MB"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize the largest top-level files/directories in a PyInstaller bundle.")
    parser.add_argument(
        "bundle",
        nargs="?",
        default="smoke_test_assets/packaging/dist/OmniDictate",
        help="Path to the PyInstaller output directory.",
    )
    parser.add_argument("--top", type=int, default=30, help="Number of largest entries to print.")
    parser.add_argument(
        "--fail-over-mb",
        type=float,
        default=0.0,
        help="Exit non-zero if the bundle is larger than this many MB.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle = Path(args.bundle)
    if not bundle.exists():
        raise SystemExit(f"Bundle path not found: {bundle}")

    entries: list[tuple[str, int]] = []
    total = 0
    for child in bundle.iterdir():
        size = _directory_size(child) if child.is_dir() else child.stat().st_size
        entries.append((child.name, size))
        total += size

    entries.sort(key=lambda item: item[1], reverse=True)
    print(f"Bundle: {bundle}")
    print(f"Total: {_format_mb(total)} ({total} bytes)")
    print(f"Top {min(args.top, len(entries))} entries:")
    for name, size in entries[: args.top]:
        print(f"{_format_mb(size):>10}  {name}")

    if args.fail_over_mb and total > args.fail_over_mb * 1024 * 1024:
        print(f"FAIL: bundle exceeds {args.fail_over_mb:.1f} MB")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
