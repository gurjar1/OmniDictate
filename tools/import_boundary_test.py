from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ImportBoundaryTest(unittest.TestCase):
    def test_baseline_ui_import_does_not_eager_load_experimental_stacks(self):
        import main_gui  # noqa: F401
        import core_logic  # noqa: F401

        unexpected = {
            name: name in sys.modules
            for name in [
                "av",
                "bitsandbytes",
                "cv2",
                "huggingface_hub",
                "model_downloader",
                "torch",
                "transformers",
            ]
        }
        self.assertFalse(any(unexpected.values()), unexpected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
