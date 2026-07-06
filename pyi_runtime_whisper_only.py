"""PyInstaller runtime hook for the public Whisper-only package."""

from __future__ import annotations

import os

os.environ.setdefault("OMNIDICTATE_PACKAGE_PROFILE", "whisper-only")
