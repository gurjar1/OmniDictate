# Gemma E4B Preflight - 2026-07-05

Status: preflight tooling added; E4B live gate remains open.

## Purpose

Gemma 4 E2B has live local evidence. Gemma 4 E4B is still unverified because
local E4B weights have not been tested. This preflight separates local model
availability and runtime setup from the expensive live load/generation gate.

## Command

The normal one-command live gate is:

```powershell
.\venv\Scripts\python.exe tools\gemma_e4b_gate.py --model google/gemma-4-E4B-it --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gemma-e4b-gate-report.json
```

It runs the lower-level preflight, hybrid live smoke, and report audit
internally. Use `--dry-run` when documenting the intended command path without
loading E4B.

The first internal step is:

```powershell
.\venv\Scripts\python.exe tools\gemma_model_preflight.py --model google/gemma-4-E4B-it --require-local --report-json smoke_test_assets\gemma-e4b-preflight.json
```

Use `--require-local` when you want the command to fail unless local E4B
weights are present under `smoke_test_assets\models\gemma-4-E4B-it`.

The preflight missing-weight/report boundary is covered by:

```powershell
.\venv\Scripts\python.exe tools\gemma_model_preflight_test.py
```

That test uses a temporary empty model store and mocked runtime summaries. It
verifies that `--require-local` fails, writes a report, and keeps the local
weights/live-generation boundary explicit without downloading or loading E4B.

## Current Result

Result: passed as a preflight, not as a live model gate.

Current local state:

- Model id: `google/gemma-4-E4B-it`
- Local directory:
  `D:\OmniDictate - GUI\smoke_test_assets\models\gemma-4-E4B-it`
- Local weights: missing (`exists=false`, `files=0`, `has_safetensors=false`)
- Transformers: available, version `5.5.0`
- Gemma model API: `AutoModelForMultimodalLM`
- Torch: available, version `2.6.0+cu126`
- CUDA: available on `NVIDIA GeForce RTX 3060 Laptop GPU`
- GPU memory: 6,441,926,656 bytes

Interpretation: the installed runtime can attempt Gemma 4 E4B, but local E4B
weights are not present. This keeps the E4B live gate open.

## Passing Live Gate

After local weights are available, run at least the hybrid/context smoke:

```powershell
.\venv\Scripts\python.exe tools\gemma_smoke_test.py --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --runtime transformers --model google/gemma-4-E4B-it --quantization 4-bit --audio-mode hybrid-whisper --whisper-model tiny --duration 5 --expected "hello world this is a simple speech test" --min-word-ratio 0.75 --report-json smoke_test_assets\gemma-e4b-live-smoke.json
```

Native audio remains optional and experimental:

```powershell
.\venv\Scripts\python.exe tools\gemma_smoke_test.py --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --runtime transformers --model google/gemma-4-E4B-it --quantization 16-bit --audio-mode native-audio --whisper-model tiny --duration 5 --expected "hello world this is a simple speech test" --min-word-ratio 0.5
```

## Acceptance

- Local E4B model directory exists and contains weight files.
- Transformers exposes the Gemma multimodal model class.
- Hybrid/context smoke loads the model, uses the expected route, and matches
  the expected phrase.
- Device map, latency, warnings, and failure modes are recorded.
- `tools\gemma_e4b_gate_report_audit.py` passes on the saved preflight and
  live-smoke reports:

  ```powershell
  .\venv\Scripts\python.exe tools\gemma_e4b_gate_report_audit.py --preflight-report smoke_test_assets\gemma-e4b-preflight.json --smoke-report smoke_test_assets\gemma-e4b-live-smoke.json
  ```
- `tools\gemma_e4b_gate.py` writes
  `smoke_test_assets\gemma-e4b-gate-report.json` with `status: passed`.

`tools\gemma_e4b_gate_report_audit_test.py` covers passing reports, missing
local weights, non-hybrid/native-only smoke, visual-context misses, transcript
mismatches, and failed live-smoke reports without downloading or loading E4B.

Until that live smoke passes, E4B must remain labeled unverified in the UI and
release notes.
