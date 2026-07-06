from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_updates import is_newer_version, parse_version, update_info_from_release


class AppUpdatesTest(unittest.TestCase):
    def test_parse_version_accepts_plain_and_v_prefixed_tags(self):
        self.assertEqual(parse_version("v3.0.1")[:3], (3, 0, 1))
        self.assertEqual(parse_version("3.1")[:3], (3, 1, 0))

    def test_is_newer_version_uses_semver_numbers(self):
        self.assertTrue(is_newer_version("v3.0.1", "3.0.0"))
        self.assertFalse(is_newer_version("v2.0.2", "3.0.0"))
        self.assertFalse(is_newer_version("v3.0.0", "3.0.0"))

    def test_update_info_uses_github_release_url(self):
        info = update_info_from_release(
            {
                "tag_name": "v3.0.1",
                "html_url": "https://github.com/gurjar1/OmniDictate/releases/tag/v3.0.1",
            },
            current_version="3.0.0",
        )

        self.assertTrue(info.update_available)
        self.assertEqual(info.latest_version, "v3.0.1")
        self.assertIn("/releases/tag/v3.0.1", info.release_url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
