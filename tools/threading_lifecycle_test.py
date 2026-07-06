from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ThreadingLifecycleTest(unittest.TestCase):
    def test_dictation_stop_does_not_use_blocking_qt_invocation(self):
        source = (ROOT / "main_gui.py").read_text(encoding="utf-8")

        self.assertIn("Qt.ConnectionType.QueuedConnection", source)
        self.assertNotIn("BlockingQueuedConnection", source)

    def test_worker_signals_stop_completion_and_drops_queued_requests(self):
        source = (ROOT / "core_logic.py").read_text(encoding="utf-8")

        self.assertIn("stop_completed = Signal()", source)
        self.assertIn("self.stop_completed.emit()", source)
        self.assertIn("self._clear_queue(self.request_queue)", source)
        self.assertIn("while not self.stop_inference_event.is_set():", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
