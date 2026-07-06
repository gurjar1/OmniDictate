from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.gemma_gguf_backend import GemmaGGUFBackend


def _encode_probe_image() -> str:
    image = Image.new("RGB", (96, 64), (22, 94, 132))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _normalize_url(url: str) -> str:
    return GemmaGGUFBackend._normalize_base_url(url)


def _extract_models(payload: dict[str, Any]) -> list[str]:
    data = payload.get("data") or []
    return [str(item.get("id", "")).strip() for item in data if str(item.get("id", "")).strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe a real OpenAI-compatible GGUF server before running the full OmniDictate GGUF backend smoke."
    )
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1", help="OpenAI-compatible server base URL.")
    parser.add_argument("--model", default="", help="Model id to use. Defaults to the first /models entry.")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")
    parser.add_argument("--no-image", action="store_true", help="Send a text-only chat request instead of text plus image_url.")
    parser.add_argument("--print-payload", action="store_true", help="Print the chat payload for debugging.")
    parser.add_argument("--report-json", default="", help="Optional path for a JSON probe report.")
    return parser.parse_args()


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {
        "url": args.url,
        "base_url": "",
        "requested_model": args.model,
        "selected_model": "",
        "no_image": bool(args.no_image),
        "models": [],
        "status": "not-started",
        "response_text": "",
        "error": "",
    }

    try:
        import requests
    except Exception as exc:
        print(f"requests is unavailable: {exc}")
        report["status"] = "failed"
        report["error"] = f"requests is unavailable: {exc}"
        if args.report_json:
            _write_report(Path(args.report_json), report)
        return 2

    base_url = _normalize_url(args.url)
    report["base_url"] = base_url
    models_url = f"{base_url}/models"
    print(f"Probing models endpoint: {models_url}")
    try:
        models_response = requests.get(models_url, timeout=args.timeout)
        models_response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Could not reach GGUF server models endpoint: {exc}")
        print("Start a local OpenAI-compatible server first, or pass --url for the active server.")
        report["status"] = "failed"
        report["error"] = f"Could not reach GGUF server models endpoint: {exc}"
        if args.report_json:
            _write_report(Path(args.report_json), report)
        return 1
    models_payload = models_response.json()
    model_ids = _extract_models(models_payload)
    report["models"] = model_ids
    if not model_ids and not args.model:
        print("Server returned no models. Pass --model explicitly or load a model in the server.")
        report["status"] = "failed"
        report["error"] = "Server returned no models."
        if args.report_json:
            _write_report(Path(args.report_json), report)
        return 1

    model = args.model or model_ids[0]
    report["selected_model"] = model
    print(f"Using model: {model}")
    if model_ids:
        print("Models reported by server:")
        for model_id in model_ids:
            print(f"- {model_id}")

    content: list[dict[str, Any]] = []
    if not args.no_image:
        content.append({"type": "image_url", "image_url": {"url": _encode_probe_image()}})
    content.append(
        {
            "type": "text",
            "text": (
                "OmniDictate GGUF server probe. Reply with a short sentence "
                "confirming that text"
                + (" and image" if not args.no_image else "")
                + " input was received. Do not request audio."
            ),
        }
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a local transcription refinement smoke-test server."},
            {"role": "user", "content": content},
        ],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 64,
        "stream": False,
    }
    if args.print_payload:
        print(json.dumps(payload, indent=2)[:4000])

    chat_url = f"{base_url}/chat/completions"
    print(f"Probing chat endpoint: {chat_url}")
    try:
        chat_response = requests.post(chat_url, json=payload, timeout=args.timeout)
        chat_response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Could not complete GGUF server chat probe: {exc}")
        if not args.no_image:
            print("If the server is text-only or image support is not configured, retry with --no-image.")
        report["status"] = "failed"
        report["error"] = f"Could not complete GGUF server chat probe: {exc}"
        if args.report_json:
            _write_report(Path(args.report_json), report)
        return 1
    chat_payload = chat_response.json()
    choices = chat_payload.get("choices") or []
    if not choices:
        print("Server returned no chat completion choices.")
        report["status"] = "failed"
        report["error"] = "Server returned no chat completion choices."
        if args.report_json:
            _write_report(Path(args.report_json), report)
        return 1
    message = choices[0].get("message") or {}
    content_value = message.get("content")
    if isinstance(content_value, list):
        text = "\n".join(item.get("text", "") for item in content_value if isinstance(item, dict)).strip()
    else:
        text = str(content_value or "").strip()
    if not text:
        print("Server returned an empty chat completion.")
        report["status"] = "failed"
        report["error"] = "Server returned an empty chat completion."
        if args.report_json:
            _write_report(Path(args.report_json), report)
        return 1

    print("Server response:")
    print(text)
    report["status"] = "passed"
    report["response_text"] = text
    if args.report_json:
        _write_report(Path(args.report_json), report)
        print(f"Wrote report: {Path(args.report_json).resolve()}")
    print("GGUF server probe passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
