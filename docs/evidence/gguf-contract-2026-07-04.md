# GGUF Server Contract Evidence - 2026-07-04

## Command

```powershell
.\venv\Scripts\python.exe tools\gguf_contract_test.py
```

## Result

Result: passed.

The test starts a local mock OpenAI-compatible server and verifies
OmniDictate's GGUF backend contract:

- `GET /v1/models` is used to auto-select a model when no model name is
  configured.
- `POST /v1/chat/completions` is used for context/reasoning refinement.
- Image context is sent as `image_url` data URLs.
- Transcript/context instructions are sent as text.
- Raw audio keys such as `audio`, `input_audio`, and `audio_url` are not sent
  to the server.
- Pure transcription short-circuits to Whisper and does not call
  `/v1/chat/completions`.

## Boundary

This proves OmniDictate's request contract and privacy boundary. It does not
prove compatibility with a real llama.cpp, LM Studio, or other local server
runtime. A real server smoke remains required before claiming GGUF readiness.
