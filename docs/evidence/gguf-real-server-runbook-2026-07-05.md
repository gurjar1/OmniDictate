# GGUF Real Server Runbook - 2026-07-05

Status: runbook added; real server smoke not yet executed.

## Purpose

The mock GGUF contract test proves OmniDictate's request shape and privacy
boundary, but it does not prove compatibility with a real local runtime. This
runbook defines the remaining real-server gate.

## Supported Server Contract

The server must expose an OpenAI-compatible API:

- `GET /v1/models`
- `POST /v1/chat/completions`

For context/reasoning refinement, OmniDictate sends transcript text plus
optional `image_url` data URLs. It does not send raw audio to the server.

## Step 1 - Start A Local Server

Start one OpenAI-compatible local server with a loaded model. Examples:

- LM Studio local server with a multimodal model loaded.
- llama.cpp `llama-server` with a compatible multimodal model and projector.
- Any other local server that accepts OpenAI-style chat completions with
  `image_url` content.

Default OmniDictate URL:

```text
http://127.0.0.1:8080/v1
```

## Step 2 - Run The One-Command Gate

After the server is running, use the wrapper command first:

```powershell
.\venv\Scripts\python.exe tools\gguf_real_server_gate.py --url http://127.0.0.1:8080/v1 --server-implementation "LM Studio" --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gguf\real-server-gate-report.json
```

Replace `"LM Studio"` with the real server implementation in use. The command
rejects mock labels, runs the direct API probe, runs the full OmniDictate
`--runtime gguf-server` backend smoke, and then audits the saved reports. Use
`--dry-run` to record the intended command path without contacting a server.

## Step 3 - Probe The Server API Internally

The first internal step is:

```powershell
.\venv\Scripts\python.exe tools\gguf_server_probe.py --url http://127.0.0.1:8080/v1
```

If the server does not support image payloads, first diagnose with:

```powershell
.\venv\Scripts\python.exe tools\gguf_server_probe.py --url http://127.0.0.1:8080/v1 --no-image
```

For durable evidence, include `--report-json`:

```powershell
.\venv\Scripts\python.exe tools\gguf_server_probe.py --url http://127.0.0.1:8080/v1 --report-json smoke_test_assets\gguf\real-server-probe.json
```

Acceptance:

- `/v1/models` returns at least one model, or `--model` is provided.
- `/v1/chat/completions` returns non-empty text.
- The server does not require or receive raw audio.

Current local result without a server running:

```powershell
.\venv\Scripts\python.exe tools\gguf_server_probe.py --url http://127.0.0.1:8080/v1 --timeout 3
```

Result: failed cleanly as expected because no local server was listening on
`127.0.0.1:8080`. The tool reported that it could not reach `/v1/models` and
instructed the user to start a local OpenAI-compatible server or pass the
active server URL.

The probe report format is covered by `tools\gguf_server_probe_test.py`, which
starts a mock OpenAI-compatible server, verifies image and text payloads, checks
that raw audio is not sent, and validates the JSON report shape. This still
does not close the real-server gate.

## Step 4 - Run The Full OmniDictate GGUF Backend Smoke Internally

After the direct probe passes, run the full backend path against the same
server. Use any known short WAV/image fixture with expected text:

```powershell
.\venv\Scripts\python.exe tools\gemma_smoke_test.py `
  --runtime gguf-server `
  --gguf-url http://127.0.0.1:8080/v1 `
  --audio smoke_test_assets\gemma_live_smoke.wav `
  --image smoke_test_assets\gemma_live_smoke.png `
  --whisper-model tiny `
  --expected "hello world this is a simple speech test" `
  --min-word-ratio 0.6 `
  --report-json smoke_test_assets\gguf\real-server-smoke.json
```

Acceptance:

- Backend load succeeds.
- Route is `Whisper -> GGUF server`.
- Visual context is used when an image is attached.
- Output is non-empty and matches the expected phrase at the configured ratio.
- Failures are recorded with the server implementation, model id, URL, command,
  and response/error text.

## Step 5 - Audit The Saved Reports Internally

After the direct probe and backend smoke both pass, audit the two reports with
the real server implementation name:

```powershell
.\venv\Scripts\python.exe tools\gguf_gate_report_audit.py --probe-report smoke_test_assets\gguf\real-server-probe.json --smoke-report smoke_test_assets\gguf\real-server-smoke.json --server-implementation "LM Studio"
```

Acceptance:

- The server implementation is a named real local server, not a mock.
- The direct probe passed, selected a model, and returned non-empty text.
- The backend smoke passed with `runtime: gguf-server`.
- The backend smoke URL matches the direct probe URL.
- Route is `GGUF server refinement`.
- Visual context was used.
- Output matches the expected phrase at the configured ratio.
- `tools\gguf_real_server_gate.py` writes
  `smoke_test_assets\gguf\real-server-gate-report.json` with `status:
  passed`.

`tools\gguf_gate_report_audit_test.py` covers passing reports, mock-label
rejection, URL/route/context/text mismatches, and failed probe reports without
requiring a live server.

## Current Boundary

This gate remains open until the commands above pass against a named real
server implementation and `tools\gguf_gate_report_audit.py` passes on the
saved direct-probe and backend-smoke reports. The mock contract test and direct
probe tool are not a substitute for the full backend smoke.
