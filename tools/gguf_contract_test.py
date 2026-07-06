from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_settings import AppSettings
from engines.base import ExecutionRoute, PromptMode, TargetAppContext, TranscriptionRequest, VisualContextSnapshot, VisualSource
from engines.gemma_gguf_backend import GemmaGGUFBackend


def _contains_key(payload, forbidden_keys: set[str]) -> bool:
    if isinstance(payload, dict):
        return any(key in forbidden_keys or _contains_key(value, forbidden_keys) for key, value in payload.items())
    if isinstance(payload, list):
        return any(_contains_key(item, forbidden_keys) for item in payload)
    return False


class _ContractHandler(BaseHTTPRequestHandler):
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
        self._send_json(200, {"data": [{"id": "mock-gemma-4-e2b-mmproj"}]})

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
        payload = json.loads(body.decode("utf-8"))
        self.__class__.requests_seen.append(payload)

        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": "not found"})
            return
        if _contains_key(payload, {"audio", "input_audio", "audio_url"}):
            self._send_json(400, {"error": "raw audio payload is not allowed"})
            return

        messages = payload.get("messages") or []
        user_message = next((message for message in messages if message.get("role") == "user"), {})
        content = user_message.get("content") or []
        has_image = any(item.get("type") == "image_url" and item.get("image_url", {}).get("url", "").startswith("data:image/png;base64,") for item in content)
        has_text = any(item.get("type") == "text" and "draft transcript" in item.get("text", "") for item in content)
        if not has_image or not has_text:
            self._send_json(400, {"error": "expected image_url and draft transcript text"})
            return

        self._send_json(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": "server polished transcript",
                        }
                    }
                ]
            },
        )


class _MockServer:
    def __init__(self):
        _ContractHandler.requests_seen = []
        self.server = HTTPServer(("127.0.0.1", 0), _ContractHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/v1"

    @property
    def requests_seen(self) -> list[dict]:
        return list(_ContractHandler.requests_seen)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        self.server.shutdown()
        self.thread.join(timeout=2.0)
        self.server.server_close()


def _build_request(prompt_mode: PromptMode = PromptMode.CONTEXT) -> TranscriptionRequest:
    image = Image.new("RGB", (64, 64), (20, 80, 140))
    return TranscriptionRequest(
        audio=np.ones(16000, dtype=np.float32),
        sample_rate=16000,
        language="en",
        prompt_mode=prompt_mode,
        visual_context=VisualContextSnapshot(
            source=VisualSource.ATTACHED_IMAGE,
            images=[image],
            description="Images: contract.png",
            metadata={"attachment_names": "contract.png"},
        ),
        target_app=TargetAppContext(title="GGUF contract test", process_name="unittest"),
        max_new_tokens=32,
    )


class GGUFContractTest(unittest.TestCase):
    def test_server_contract_sends_text_and_images_without_raw_audio(self):
        with _MockServer() as server:
            app_settings = AppSettings(
                backend="gemma-gguf-server",
                gguf_server_url=server.base_url,
                gguf_model_name="",
                gemma_hybrid_whisper_model="tiny",
            )
            backend = GemmaGGUFBackend(app_settings)

            def _fake_load_whisper_frontend():
                backend.whisper_frontend = object()
                return ["Fake Whisper frontend for contract test."]

            backend._load_whisper_frontend = _fake_load_whisper_frontend
            backend._transcribe_with_whisper_frontend = lambda _request: "draft transcript from whisper"

            load_result = backend.load()
            self.assertTrue(load_result.success, load_result.status_message)
            self.assertEqual(backend.server_model_name, "mock-gemma-4-e2b-mmproj")

            result = backend.transcribe(_build_request())

            self.assertEqual(result.execution_route, ExecutionRoute.GGUF_SERVER_REFINEMENT)
            self.assertTrue(result.used_visual_context)
            self.assertEqual(result.text, "server polished transcript")
            self.assertEqual(len(server.requests_seen), 1)
            self.assertFalse(_contains_key(server.requests_seen[0], {"audio", "input_audio", "audio_url"}))

    def test_pure_mode_short_circuits_to_whisper_and_skips_server_post(self):
        with _MockServer() as server:
            app_settings = AppSettings(
                backend="gemma-gguf-server",
                gguf_server_url=server.base_url,
                gguf_model_name="explicit-model",
                gemma_hybrid_whisper_model="tiny",
            )
            backend = GemmaGGUFBackend(app_settings)

            def _fake_load_whisper_frontend():
                backend.whisper_frontend = object()
                return ["Fake Whisper frontend for contract test."]

            backend._load_whisper_frontend = _fake_load_whisper_frontend
            backend._transcribe_with_whisper_frontend = lambda _request: "draft transcript from whisper"

            load_result = backend.load()
            self.assertTrue(load_result.success, load_result.status_message)

            result = backend.transcribe(_build_request(PromptMode.PURE))

            self.assertEqual(result.execution_route, ExecutionRoute.WHISPER_ONLY)
            self.assertEqual(result.text, "draft transcript from whisper")
            self.assertEqual(server.requests_seen, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
