from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.base import BackendLoadResult
import main_gui


class FakeBackend:
    def __init__(self, load_result: BackendLoadResult):
        self.load_result = load_result
        self.loaded = False
        self.unloaded = False

    def load(self):
        self.loaded = True
        return self.load_result

    def unload(self):
        self.unloaded = True


class PreloadModelWorkerTest(unittest.TestCase):
    def tearDown(self):
        if hasattr(main_gui, "_original_create_backend_for_test"):
            main_gui.create_backend = main_gui._original_create_backend_for_test
            delattr(main_gui, "_original_create_backend_for_test")

    def _patch_backend(self, backend: FakeBackend):
        main_gui._original_create_backend_for_test = main_gui.create_backend
        main_gui.create_backend = lambda _settings: backend

    def test_preload_loads_and_unloads_backend(self):
        backend = FakeBackend(BackendLoadResult(True, "Gemma ready", ["warm cache"]))
        self._patch_backend(backend)
        settings = AppSettings(backend="gemma-4", gemma_model="google/gemma-4-E2B-it")
        worker = main_gui.ModelPreloadWorker(settings)
        statuses = []
        completed = []
        failed = []
        worker.status_updated.connect(statuses.append)
        worker.preload_completed.connect(completed.append)
        worker.preload_failed.connect(failed.append)

        worker.run()

        self.assertTrue(backend.loaded)
        self.assertTrue(backend.unloaded)
        self.assertIn("Preloading gemma-4-E2B-it...", statuses)
        self.assertIn("warm cache", statuses)
        self.assertEqual(completed, ["Gemma ready"])
        self.assertEqual(failed, [])

    def test_preload_failure_is_reported_and_unloaded(self):
        backend = FakeBackend(BackendLoadResult(False, "missing weights", []))
        self._patch_backend(backend)
        worker = main_gui.ModelPreloadWorker(AppSettings(backend="gemma-4"))
        completed = []
        failed = []
        worker.preload_completed.connect(completed.append)
        worker.preload_failed.connect(failed.append)

        worker.run()

        self.assertTrue(backend.loaded)
        self.assertTrue(backend.unloaded)
        self.assertEqual(completed, [])
        self.assertEqual(failed, ["missing weights"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
