from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import gguf_server_probe


class _ProbeHandler(BaseHTTPRequestHandler):
    requests_seen: list[dict] = []

    def log_message(self, _format, *_args):
        return

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/v1/models":
            self._send_json(404, {"error": "not found"})
            return
        self._send_json(200, {"data": [{"id": "mock-vision-gguf"}]})

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
        payload = json.loads(body.decode("utf-8"))
        self.__class__.requests_seen.append(payload)
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": "not found"})
            return
        self._send_json(200, {"choices": [{"message": {"content": "mock gguf probe response"}}]})


class _MockServer:
    def __init__(self):
        _ProbeHandler.requests_seen = []
        self.server = HTTPServer(("127.0.0.1", 0), _ProbeHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/v1"

    @property
    def requests_seen(self) -> list[dict]:
        return list(_ProbeHandler.requests_seen)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        self.server.shutdown()
        self.thread.join(timeout=2.0)
        self.server.server_close()


def _contains_key(payload, forbidden_keys: set[str]) -> bool:
    if isinstance(payload, dict):
        return any(key in forbidden_keys or _contains_key(value, forbidden_keys) for key, value in payload.items())
    if isinstance(payload, list):
        return any(_contains_key(item, forbidden_keys) for item in payload)
    return False


class GGUFServerProbeTest(unittest.TestCase):
    def test_probe_passes_against_openai_compatible_mock_and_writes_report(self):
        with _MockServer() as server, tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "gguf-probe.json"
            original_argv = sys.argv
            sys.argv = [
                "gguf_server_probe.py",
                "--url",
                server.base_url,
                "--timeout",
                "3",
                "--report-json",
                str(report_path),
            ]
            try:
                rc = gguf_server_probe.main()
            finally:
                sys.argv = original_argv

            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["selected_model"], "mock-vision-gguf")
        self.assertEqual(payload["models"], ["mock-vision-gguf"])
        self.assertFalse(payload["no_image"])
        self.assertEqual(payload["response_text"], "mock gguf probe response")
        self.assertEqual(payload["error"], "")
        self.assertEqual(len(server.requests_seen), 1)
        self.assertFalse(_contains_key(server.requests_seen[0], {"audio", "input_audio", "audio_url"}))
        user_content = server.requests_seen[0]["messages"][1]["content"]
        self.assertTrue(any(item.get("type") == "image_url" for item in user_content))

    def test_no_image_probe_omits_image_url(self):
        with _MockServer() as server, tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "gguf-probe-no-image.json"
            original_argv = sys.argv
            sys.argv = [
                "gguf_server_probe.py",
                "--url",
                server.base_url,
                "--no-image",
                "--report-json",
                str(report_path),
            ]
            try:
                rc = gguf_server_probe.main()
            finally:
                sys.argv = original_argv

            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertTrue(payload["no_image"])
        user_content = server.requests_seen[0]["messages"][1]["content"]
        self.assertFalse(any(item.get("type") == "image_url" for item in user_content))


if __name__ == "__main__":
    unittest.main(verbosity=2)
