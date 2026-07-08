from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_updates import (
    APP_VERSION,
    is_newer_version,
    parse_version,
    should_auto_check_updates,
    update_info_from_release,
)


class AppUpdatesTest(unittest.TestCase):
    def test_parse_version_accepts_plain_and_v_prefixed_tags(self):
        self.assertEqual(parse_version("v3.0.3")[:3], (3, 0, 3))
        self.assertEqual(parse_version("3.1")[:3], (3, 1, 0))

    def test_is_newer_version_uses_semver_numbers(self):
        self.assertTrue(is_newer_version("v3.0.3", "3.0.2"))
        self.assertFalse(is_newer_version("v2.0.2", "3.0.0"))
        self.assertFalse(is_newer_version("v3.0.0", "3.0.0"))

    def test_update_info_uses_github_release_url(self):
        info = update_info_from_release(
            {
                "tag_name": "v3.0.3",
                "html_url": "https://github.com/gurjar1/OmniDictate/releases/tag/v3.0.3",
            },
            current_version="3.0.1",
        )

        self.assertTrue(info.update_available)
        self.assertEqual(info.latest_version, "v3.0.3")
        self.assertIn("/releases/tag/v3.0.3", info.release_url)

    def test_current_patch_release_does_not_update_to_itself(self):
        self.assertEqual(APP_VERSION, "3.0.3")
        info = update_info_from_release(
            {
                "tag_name": "v3.0.3",
                "html_url": "https://github.com/gurjar1/OmniDictate/releases/tag/v3.0.3",
            },
        )

        self.assertFalse(info.update_available)

    def test_auto_update_check_runs_once_per_day(self):
        today = date(2026, 7, 8)

        self.assertTrue(should_auto_check_updates(True, "", today=today))
        self.assertFalse(should_auto_check_updates(True, "2026-07-08", today=today))
        self.assertTrue(should_auto_check_updates(True, "2026-07-07", today=today))
        self.assertFalse(should_auto_check_updates(False, "2026-07-07", today=today))

    def test_auto_update_check_recovers_from_bad_saved_date(self):
        self.assertTrue(
            should_auto_check_updates(True, "not-a-date", today=date(2026, 7, 8))
        )
        self.assertTrue(
            should_auto_check_updates(True, "2026-07-09", today=date(2026, 7, 8))
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
