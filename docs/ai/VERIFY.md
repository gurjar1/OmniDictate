# Verification

Use the quick gate before claiming code-level progress:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

The runner uses `.\venv\Scripts\python.exe` when present, otherwise `python`.

## Quick Gate

The quick gate should run without human input:

1. Python version check.
2. Compile key Python files and packages.
3. Route smoke tests in `tools\route_smoke_test.py`.
4. Worker behavior tests in `tools\worker_behavior_test.py`.
5. Threading lifecycle tests in `tools\threading_lifecycle_test.py`.
6. Hotkey listener tests in `tools\hotkey_listener_test.py`.
7. Baseline import-boundary tests in `tools\import_boundary_test.py`.
8. Packaging profile tests in `tools\packaging_profile_test.py`.
9. Runtime profile tests in `tools\runtime_profile_test.py`.
10. App update tests in `tools\app_updates_test.py`.
11. Whisper runtime CUDA detection tests in
   `tools\whisper_runtime_detection_test.py`.
12. UI contrast static tests in `tools\ui_contrast_static_test.py`.
13. UI transport state tests in `tools\ui_transport_state_test.py`.
14. Preload model worker tests in `tools\preload_model_worker_test.py`.
15. Release-readiness claim audit in `tools\release_readiness_audit.py`.
16. Release-readiness claim audit tests in `tools\release_readiness_audit_test.py`.
9. Artifact manifest byte/hash/dimension audit in
   `tools\artifact_manifest_audit.py`.
10. Open external-gate summary in `tools\open_gate_summary.py --strict`.
11. Open external-gate summary tests in `tools\open_gate_summary_test.py`.
12. Goal completion audit tests in `tools\goal_completion_audit_test.py`.
13. Goal completion audit in `tools\goal_completion_audit.py`.
14. Handoff next-action audit tests in
   `tools\handoff_next_action_audit_test.py`.
15. Handoff next-action audit in `tools\handoff_next_action_audit.py`.
16. Publication blocker audit tests in
   `tools\publication_blocker_audit_test.py`.
17. Release status report tests in `tools\release_status_report_test.py`.
18. Release decision matrix report tests in
   `tools\release_decision_matrix_report_test.py`.
19. Release snapshot freshness audit tests and current-report check in
   `tools\release_snapshot_freshness_audit_test.py` and
   `tools\release_snapshot_freshness_audit.py`.
20. Release scope decision audit tests and current decision check in
   `tools\release_scope_decision_audit_test.py` and
   `tools\release_scope_decision_audit.py`.
21. GitHub release preflight tests in `tools\github_release_preflight_test.py`.
22. External gate orchestrator tests in
   `tools\external_gate_orchestrator_test.py`.
23. External gate prerequisite audit tests in
   `tools\external_gate_prerequisite_audit_test.py`.
24. External gate closure audit tests in
   `tools\external_gate_closure_audit_test.py`.
25. Microphone evidence tooling tests in
   `tools\microphone_evidence_tooling_test.py`.
26. Physical microphone gate runner tests in
   `tools\physical_microphone_gate_test.py`.
27. Microphone gate report audit tests in
   `tools\microphone_gate_report_audit_test.py`.
28. Final release tooling tests in `tools\final_release_tooling_test.py`.
29. Final release gate audit tests in
   `tools\final_release_gate_audit_test.py`.
30. Final public release gate runner tests in
   `tools\final_public_release_gate_test.py`.
31. Alternative STT adapter tests in `tools\alternative_stt_adapter_test.py`.
32. GGUF server contract tests in `tools\gguf_contract_test.py`.
33. GGUF server probe tests in `tools\gguf_server_probe_test.py`.
34. GGUF gate report audit tests in `tools\gguf_gate_report_audit_test.py`.
35. GGUF real-server gate runner tests in
   `tools\gguf_real_server_gate_test.py`.
36. Gemma model preflight tests in `tools\gemma_model_preflight_test.py`.
37. Gemma E4B gate runner tests in `tools\gemma_e4b_gate_test.py`.
38. Gemma E4B gate report audit tests in
   `tools\gemma_e4b_gate_report_audit_test.py`.
39. Visual context smoke in `tools\visual_context_smoke.py`.
40. Microphone capture diagnostic compile check in
   `tools\microphone_capture_diagnostic.py`.
41. External gate orchestrator compile check in
   `tools\external_gate_orchestrator.py`.
42. External gate prerequisite audit compile check in
   `tools\external_gate_prerequisite_audit.py`.
43. External gate closure audit compile check in
   `tools\external_gate_closure_audit.py`.
44. Physical microphone gate runner compile check in
   `tools\physical_microphone_gate.py`.
45. Microphone gate report audit compile check in
   `tools\microphone_gate_report_audit.py`.
46. GGUF real-server probe compile check in `tools\gguf_server_probe.py`.
47. GGUF gate report audit compile check in `tools\gguf_gate_report_audit.py`.
48. GGUF real-server gate runner compile check in
   `tools\gguf_real_server_gate.py`.
49. Gemma model preflight compile check in `tools\gemma_model_preflight.py`.
50. Gemma E4B gate runner compile check in `tools\gemma_e4b_gate.py`.
51. Gemma E4B gate report audit compile check in
   `tools\gemma_e4b_gate_report_audit.py`.
52. STT adapter benchmark compile check in `tools\stt_adapter_benchmark.py`.
53. Final release preflight compile check in `tools\final_release_preflight.py`.
54. Final release gate audit compile check in
   `tools\final_release_gate_audit.py`.
55. Final public release gate runner compile check in
   `tools\final_public_release_gate.py`.
56. Publication blocker audit compile check in
   `tools\publication_blocker_audit.py`.
57. Release status report compile check in `tools\release_status_report.py`.
58. Release decision matrix report compile check in
   `tools\release_decision_matrix_report.py`.
59. Release snapshot freshness audit compile check in
   `tools\release_snapshot_freshness_audit.py`.
60. Release scope decision audit compile check in
   `tools\release_scope_decision_audit.py`.
61. GitHub release preflight compile check in
   `tools\github_release_preflight.py`.
62. Goal completion audit compile check in `tools\goal_completion_audit.py`.
63. Handoff next-action audit compile check in
   `tools\handoff_next_action_audit.py`.
64. Open-gate summary compile check in `tools\open_gate_summary.py`.
65. Gemma processor-only smoke if local processor metadata is available.
66. Qt offscreen UI construction smoke.

## Live Gates

Run these before claiming release readiness:

1. Whisper live sample: transcribe a known local WAV file with the selected
   Whisper model and compare expected text.
2. Microphone live smoke: VAD and PTT both capture, transcribe, and type into
   Notepad without typing into OmniDictate itself. Active-window typing can be
   checked separately with `tools\live_typing_smoke.py`, and the non-device
   VAD-to-typing loop can be checked with `tools\full_loop_synthetic_smoke.py`.
3. Gemma Transformers live smoke: E2B hybrid context mode loads, refines a
   short sample, and unloads cleanly.
4. Gemma native audio live smoke: E2B native audio transcribes a short sample
   using official prompt structure.
5. GGUF server smoke: local server returns `/models`, accepts image+text chat
   completion, and reports the expected route.
6. Visual context smoke: active-window screenshot, full-screen screenshot,
   image attachment, video-frame attachment, and webcam frame all fail softly
   when unavailable.
7. Packaging smoke: PyInstaller build launches on a clean machine profile.
8. Installer smoke: Inno installer installs, launches, uninstalls, and leaves
   no bundled model cache behind.

## Focused Whisper Gate

Use this while restoring `v2.0.2` parity:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_whisper.ps1 -Model tiny
```

This generates a short Windows SAPI WAV fixture at runtime and verifies that
`WhisperBackend` can load a Faster-Whisper model, transcribe the audio, and
return the `Whisper only` route. Use `-Model large-v3-turbo` before a release
candidate if that is the default release model.

## Current Evidence

Latest verified quick checks were performed on 2026-07-06 in
`D:\OmniDictate - GUI`.

Command:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed after adding the live typing, synthetic full-loop,
global-hotkey, live-microphone, asserted Gemma smoke, and GGUF contract test
scripts, plus the E2B/E4B UI wording update. Physical microphone, E4B, real
GGUF server, and release-ready installer gates remain open.

Latest rerun after the typing-history discard, public Settings readability,
visible Whisper-only copy guard, and README package-dependency updates also
passed:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed. It compiled `tools\live_microphone_smoke.py` and reran route,
worker behavior, hotkey listener, GGUF contract, Gemma processor, and Qt UI
smokes successfully.

Latest rerun after the lazy-import packaging profile and import-boundary test:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed. The quick gate now includes
`tools\import_boundary_test.py`, which verifies that baseline `main_gui` and
`core_logic` imports do not eagerly load `torch`, `transformers`,
`bitsandbytes`, `cv2`, `av`, `model_downloader`, or `huggingface_hub`.

Latest rerun after adding visual context smoke and the native UI screenshot
mode:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed. The quick gate now verifies generated image attachment,
generated video-frame sampling, active-window screen capture, full-screen
screen capture, and webcam fail-soft/capture behavior.

Latest rerun after adding microphone capture diagnostics:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed. The quick gate now compiles
`tools\microphone_capture_diagnostic.py`; it does not record from the physical
microphone during normal non-interactive verification.

Alternative STT adapter command:

```powershell
.\venv\Scripts\python.exe tools\alternative_stt_adapter_test.py
```

Result: passed. The test uses a fake Transformers ASR pipeline, verifies the
adapter request/response shape, and reports route `Alternative STT` without
downloading any model.

Alternative STT live Moonshine command:

```powershell
.\venv\Scripts\python.exe tools\alternative_stt_smoke.py --model UsefulSensors/moonshine-tiny --min-word-ratio 0.6 --keep-audio
```

Result: passed. `UsefulSensors/moonshine-tiny` loaded through Transformers,
reported route `Alternative STT`, latency `1.83s`, and matched 8/8 expected
words. Hugging Face emitted a Windows symlink-cache warning because Developer
Mode/admin symlink support is not enabled.

Whisper comparison commands:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_whisper.ps1 -Model large-v3-turbo
powershell -ExecutionPolicy Bypass -File tools\verify_whisper.ps1 -Model tiny
```

Result: both passed on the same generated fixture style. `large-v3-turbo`
reported latency `0.69s` and 8/8 expected words; `tiny` reported latency
`0.63s` and 8/8 expected words.

The quick gate now includes headless worker behavior tests for punctuation and
filter routing, PTT release queueing, VAD silence-after-speech queueing, and
the own-window typing guard.

Focused Whisper command:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_whisper.ps1 -Model tiny
```

Result: passed. Transcript matched 8/8 expected words from the generated WAV
fixture.

Release/default Whisper command:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_whisper.ps1 -Model large-v3-turbo
```

Result: passed. Transcript matched 8/8 expected words from the generated WAV
fixture.

Focused live typing command:

```powershell
.\venv\Scripts\python.exe tools\live_typing_smoke.py
```

Result: passed. The smoke opened Notepad, confirmed queued text was held while
the target window was treated as OmniDictate, then typed the text into Notepad
through the worker typing thread.

Synthetic full-loop command:

```powershell
.\venv\Scripts\python.exe tools\full_loop_synthetic_smoke.py --model large-v3-turbo
```

Result: passed. Generated speech flowed through VAD, `large-v3-turbo`,
transcription routing, and the worker typing thread into Notepad. The saved
Notepad text matched 8/8 expected words.

Focused global hotkey command:

```powershell
.\venv\Scripts\python.exe tools\global_hotkey_smoke.py
```

Result: passed. The smoke verified PTT and Ctrl+1/2/3 events through the real
`pynput` listener. This also fixed and covered a Windows VK-code regression in
Ctrl+1/2/3 mode switching.

Focused live microphone command:

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode both --timeout 28
```

Result: blocked before recording. PortAudio/sounddevice could not open the
local default Realtek microphone input. This older result is superseded by the
later permission-granted run below. See
`docs/evidence/live-microphone-audio-device-2026-07-04.md`.

Updated live microphone command:

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode both --timeout 28
```

Result: partially verified after microphone permission was granted. The Realtek
microphone opened, VAD recorded, queued, and transcribed one utterance. The
phrase assertion failed because the transcript was `We're open to the world.`
instead of `hello world this is a simple speech test` (1/8 expected words), and
PTT was not reached. The smoke tool now avoids repeatedly checking the same
mismatched transcript and supports `--capture-only` for hardware diagnostics.

Follow-up capture-only diagnostic:

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode vad --timeout 16 --capture-only
```

Result: failed to capture a new transcript during the short automated run, but
the smoke exited cleanly with a single timeout instead of repeatedly checking a
stale mismatch. The physical microphone gate remains open.

Physical microphone capture-level diagnostic:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 3 --output smoke_test_assets\microphone\diagnostic-noninteractive.wav
```

Result: failed as designed because the non-interactive recording was
near-silent: RMS `0.00021`, peak `0.00119`, active `0%`, clipping `0.00%`.
This proves the default Realtek input can open and save a WAV while showing
that this run did not contain speech-level audio.

Evidence-only quiet baseline:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 3 --allow-low-level --output smoke_test_assets\microphone\diagnostic-quiet-baseline.wav
```

Result: passed in collection mode: RMS `0.00022`, peak `0.00101`, active
`0%`, clipping `0.00%`.

Saved microphone WAV revalidation:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --input smoke_test_assets\microphone\diagnostic-quiet-baseline.wav --allow-low-level --report-json smoke_test_assets\microphone\diagnostic-quiet-baseline-report.json
```

Result: passed. The existing quiet baseline WAV was reloaded without opening
the microphone, stats were recomputed, and a JSON report was written. This
does not close the physical speech gate; it provides a repeatable way to
verify a captured spoken WAV after the human recording step.

Guided spoken capture command:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 7 --prompt --countdown 3 --model large-v3-turbo --output smoke_test_assets\microphone\spoken-phrase-large-v3-turbo.wav
```

Result: command path documented on 2026-07-05. The `--prompt` flag prints the
exact expected phrase, waits for the countdown, and then records. JSON reports
include `prompted` and `expected` fields. This lowers the human coordination
needed for the open physical microphone gate, but the gate remains open until
a spoken WAV and the VAD/PTT manual smoke both pass.

Post-saved-WAV diagnostic quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
.\venv\Scripts\python.exe tools\release_readiness_audit.py
```

Result: passed on 2026-07-05 after adding `--input` and `--report-json` to
`tools\microphone_capture_diagnostic.py`.

Fresh release-default Whisper gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_whisper.ps1 -Model large-v3-turbo
```

Result: passed on 2026-07-05. `large-v3-turbo` loaded, returned route
`Whisper only`, reported latency `0.60s`, and matched 8/8 expected words:
`Hello world this is a simple speech test.`

Fresh release-default installer smoke:

```powershell
powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1 -InstallerPath smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe -InstallDir "$env:LOCALAPPDATA\OmniDictate" -UseInstallerDefaults
```

Result: passed on 2026-07-05. The installer used its defaults to install to
`C:\Users\kapil\AppData\Local\OmniDictate`, launched the installed executable,
uninstalled, and removed the installed payload.

Artifact manifest and manifest-aware release audit:

```powershell
Get-FileHash smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe -Algorithm SHA256
.\venv\Scripts\python.exe tools\package_size_audit.py smoke_test_assets\packaging\dist-whisper\OmniDictate --top 8 --fail-over-mb 300
.\venv\Scripts\python.exe tools\artifact_manifest_audit.py
.\venv\Scripts\python.exe tools\release_readiness_audit.py
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05 after adding
`docs\release\ARTIFACT_MANIFEST_3.0.0-whisper.md`. The manifest records the
current smoke installer, packaged executable, packaged first-run screenshot,
sizes, SHA256 hashes, screenshot dimensions, and latest release gate evidence.
`tools\artifact_manifest_audit.py` recomputes those local file sizes, SHA256
hashes, and screenshot dimensions. The release-readiness audit verifies that
the manifest exists, records that audit tool, and that the release notes point
to it.

Publishing runbook and versioning audit:

```powershell
.\venv\Scripts\python.exe tools\release_readiness_audit.py
```

Result: passed on 2026-07-05 after adding
`docs\release\PUBLISHING_RUNBOOK_3.0.0.md`. The runbook documents `v3.0.0`
as the recommended public tag, `OmniDictate_Setup_v3.0.0.exe` as the
recommended final installer, and keeps `3.0.0-whisper-release-smoke` as a
local evidence suffix only.

Post-publishing-runbook quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate included the versioning-aware
`tools\release_readiness_audit.py` check.

Release-doc git hygiene:

```powershell
.\venv\Scripts\python.exe tools\release_readiness_audit.py
git check-ignore -v docs\release\RELEASE_CHECKLIST_3.0.0-whisper.md
```

Result: passed on 2026-07-05. `.gitignore` now uses `/release/` so the root
artifact directory remains ignored while `docs\release` documentation is
visible to git. The release-readiness audit also checks that no forbidden
`smoke_test_assets`, model cache, or downloaded-weight paths are staged.

Release-note honesty audit:

```powershell
.\venv\Scripts\python.exe tools\release_readiness_audit.py
```

Result: passed on 2026-07-05 after adding checks that the release notes state
the package is Whisper-only and keep Gemma/GGUF/alternative-STT/microphone
gates honest.

Gemma E2B hybrid/context command:

```powershell
.\venv\Scripts\python.exe tools\gemma_smoke_test.py --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --runtime transformers --model google/gemma-4-E2B-it --quantization 4-bit --audio-mode hybrid-whisper --whisper-model tiny --duration 5 --expected "hello world this is a simple speech test" --min-word-ratio 0.75
```

Result: passed. Route `Whisper -> Gemma`, visual context used, device map
`cuda:0`, latency `10.47s`, 8/8 expected words.

Gemma E2B native-audio command:

```powershell
.\venv\Scripts\python.exe tools\gemma_smoke_test.py --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --runtime transformers --model google/gemma-4-E2B-it --quantization 16-bit --audio-mode native-audio --whisper-model tiny --duration 5 --expected "hello world this is a simple speech test" --min-word-ratio 0.5
```

Result: passed but slow. Route `Native Gemma audio`, visual context used,
device map `cpu`, latency `246.39s`, 8/8 expected words. See
`docs/evidence/gemma-transformers-live-2026-07-04.md`.

Gemma E4B preflight command:

```powershell
.\venv\Scripts\python.exe tools\gemma_model_preflight.py --model google/gemma-4-E4B-it --report-json smoke_test_assets\gemma-e4b-preflight.json
```

Result: passed as a preflight on 2026-07-05. Transformers `5.5.0`,
`AutoModelForMultimodalLM`, Torch `2.6.0+cu126`, and CUDA on RTX 3060 Laptop
GPU are available. Local E4B weights were missing under
`smoke_test_assets\models\gemma-4-E4B-it`, so the live E4B gate remains open
until local weights are available and `tools\gemma_smoke_test.py` passes for
E4B. See
`docs\evidence\gemma-e4b-preflight-2026-07-05.md`.

Post-Gemma-E4B-preflight quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
.\venv\Scripts\python.exe tools\release_readiness_audit.py
```

Result: passed on 2026-07-05 after adding the Gemma E4B preflight tooling and
compile check.

E4B-preflight-aware release audit:

```powershell
.\venv\Scripts\python.exe tools\release_readiness_audit.py
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05 after making
`docs\evidence\gemma-e4b-preflight-2026-07-05.md` required release evidence
and checking that it keeps E4B live generation open until local weights and
generation smoke pass.

Gemma E4B preflight tooling test:

```powershell
.\venv\Scripts\python.exe tools\gemma_model_preflight_test.py
```

Result: passed on 2026-07-05. The test uses a temporary empty model store and
mocked runtime summaries to prove that `--require-local` fails, writes a JSON
report, and preserves the missing-local-weights boundary without downloading
or loading E4B.

Gemma E4B gate report audit:

```powershell
.\venv\Scripts\python.exe tools\gemma_e4b_gate_report_audit_test.py
```

Result: passed on 2026-07-05. The audit requires a preflight report proving
local E4B safetensors plus a passing `gemma_smoke_test.py --runtime
transformers --model google/gemma-4-E4B-it --audio-mode hybrid-whisper
--report-json` report. It rejects missing weights, native-only/non-hybrid
smokes, non-`Whisper -> Gemma` routes, missing visual context, transcript
mismatches, and failed live-smoke reports.

Gemma E4B gate runner:

```powershell
.\venv\Scripts\python.exe tools\gemma_e4b_gate_test.py
.\venv\Scripts\python.exe tools\gemma_e4b_gate.py --dry-run --report-json smoke_test_assets\gemma-e4b-gate-dry-run.json
```

Result: passed on 2026-07-05. The runner gives the E4B live gate a single
command while preserving the local-weight preflight, hybrid live smoke, and
report-audit evidence chain. The dry run writes command intent without loading
E4B.

Post-Gemma-E4B-gate-report-audit quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate now runs
`tools\gemma_e4b_gate_report_audit_test.py`, compile-checks
`tools\gemma_e4b_gate_report_audit.py`, and `tools\open_gate_summary.py
--strict` includes the E4B preflight report, live smoke report, and report
audit as the E4B gate sequence.

Post-Gemma-E4B-gate-runner quick gate:

```powershell
.\venv\Scripts\python.exe tools\gemma_e4b_gate_test.py
.\venv\Scripts\python.exe tools\gemma_e4b_gate.py --dry-run --report-json smoke_test_assets\gemma-e4b-gate-dry-run.json
.\venv\Scripts\python.exe -m py_compile tools\gemma_e4b_gate.py
.\venv\Scripts\python.exe tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate now runs
`tools\gemma_e4b_gate_test.py`, compile-checks `tools\gemma_e4b_gate.py`, and
`tools\open_gate_summary.py --strict` shows the one-command E4B gate while
keeping the gate open until local E4B weights and live generation pass.

Post-Gemma-E4B-preflight-test quick gate:

```powershell
.\venv\Scripts\python.exe tools\gemma_model_preflight_test.py
.\venv\Scripts\python.exe tools\release_readiness_audit.py
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate now runs
`tools\gemma_model_preflight_test.py` after the GGUF server probe tests.

Open-gate summary:

```powershell
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
.\venv\Scripts\python.exe tools\open_gate_summary.py --json --strict
```

Result: passed on 2026-07-05. At that point the tool reported four external
gates: physical microphone phrase-match VAD/PTT, Gemma E4B local weights/live
generation, real GGUF/OpenAI-compatible server, and final public `v3.0.0`
artifact rebuild. The final public artifact gate is now closed; current open
gate truth comes from the latest `tools\open_gate_summary.py --strict` entry.
Strict mode fails only if the coordination docs stop carrying the open-gate
markers; it does not require human microphone input, model weights, or a
running local GGUF server.

STT research refresh:

```powershell
.\venv\Scripts\python.exe -m py_compile tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\release_readiness_audit.py
```

Result: passed on 2026-07-05 after refreshing
`docs\research\STT_MODEL_RESEARCH_2026.md` with current primary model-card/docs
sources for NVIDIA Nemotron 3.5 ASR, GLM-ASR-Nano, MOSS-Transcribe, and
Microsoft VibeVoice-ASR. The release-readiness audit now checks that the
research doc still preserves the baseline decision: Whisper remains default,
new ASR models stay behind adapter spikes, and heavier runtimes stay out of
the default installer.

Alternative-STT acceptance audit:

```powershell
.\venv\Scripts\python.exe tools\release_readiness_audit.py
```

Result: passed on 2026-07-05 after adding measurable promotion criteria to
the research doc and product spec. The audit now protects the requirement that
a candidate must match accuracy, improve a named product metric, preserve lazy
imports and package boundaries, record cache/Windows-warning evidence, and
finish with a keep/defer/reject decision before visible UI or release
promotion.

Alternative-STT benchmark harness:

```powershell
.\venv\Scripts\python.exe tools\stt_adapter_benchmark.py --whisper-model large-v3-turbo --candidate-model UsefulSensors/moonshine-tiny --runs 3 --report-json smoke_test_assets\stt-benchmarks\moonshine-tiny-vs-large-v3-turbo.json
```

Result: tool added on 2026-07-05 and compile-checked in the quick gate. It
runs Whisper and an optional Transformers ASR candidate on the same fixture,
reports median latency and word-match ratio, and emits a decision string for
the promotion criteria. The quick gate compiles the tool but does not run a
live candidate model or download model weights.

Baseline-only smoke:

```powershell
.\venv\Scripts\python.exe tools\stt_adapter_benchmark.py --whisper-model tiny --runs 1 --report-json smoke_test_assets\stt-benchmarks\baseline-tiny-smoke.json
```

Result: passed on 2026-07-05. Whisper `tiny` loaded, matched 100% of expected
words, reported `0.34s` latency for the single run, emitted decision
`baseline-only`, and wrote the JSON report under ignored `smoke_test_assets`.

Moonshine benchmark:

```powershell
.\venv\Scripts\python.exe tools\stt_adapter_benchmark.py --whisper-model large-v3-turbo --candidate-model UsefulSensors/moonshine-tiny --runs 3 --whisper-package-dir smoke_test_assets\packaging\dist-whisper\OmniDictate --check-import-boundary --check-command-routing --command-check "comma=," --command-check "period=." --report-json smoke_test_assets\stt-benchmarks\moonshine-tiny-vs-large-v3-turbo.json --keep-audio
```

Result: passed on 2026-07-05. Whisper `large-v3-turbo` median latency was
`0.47s`, Moonshine-tiny median latency was `0.31s`, both had 100% word match,
candidate cache footprint was 12 files / 110,376,063 bytes, Whisper-only
package-boundary and baseline import-boundary checks passed, and the decision
was `candidate-meets-latency-promotion-bar`. Command-routing checks also
passed: spoken `comma` transcribed as `Comma.` and routed to `,`; spoken
`period` transcribed as `Period.` and routed to `.`. The report emitted
`promotion_ready: false` with blockers for physical microphone snippets and
release UI approval.

Physical microphone Moonshine follow-up:

```powershell
.\venv\Scripts\python.exe tools\stt_adapter_benchmark.py --audio smoke_test_assets\microphone\spoken-phrase-large-v3-turbo.wav --audio-source physical-microphone --whisper-model large-v3-turbo --candidate-model UsefulSensors/moonshine-tiny --runs 3 --whisper-package-dir smoke_test_assets\packaging\dist-whisper\OmniDictate --check-import-boundary --check-command-routing --command-check "comma=," --command-check "period=." --report-json smoke_test_assets\stt-benchmarks\moonshine-tiny-physical-mic.json
```

Result: command path documented on 2026-07-05. It remains open until a saved
spoken physical microphone WAV exists and passes the benchmark with
`--audio-source physical-microphone`.

GGUF contract command:

```powershell
.\venv\Scripts\python.exe tools\gguf_contract_test.py
```

Result: passed. The test starts a local mock OpenAI-compatible server, verifies
`/v1/models` auto-selection, verifies `/v1/chat/completions` receives image
data URLs plus transcript text, verifies raw audio is not sent, and verifies
Pure transcription short-circuits without a server POST.

GGUF real-server probe:

```powershell
.\venv\Scripts\python.exe tools\gguf_server_probe.py --url http://127.0.0.1:8080/v1
```

Result: tool added and compile-checked. A local run against
`http://127.0.0.1:8080/v1` failed cleanly because no server was listening; this
is expected and does not close the real-server gate. Use
`docs\evidence\gguf-real-server-runbook-2026-07-05.md` for the full real
server gate. Passing this probe is a diagnostic prerequisite, not a substitute
for the full `tools\gemma_smoke_test.py --runtime gguf-server` backend smoke.

GGUF server probe tooling test:

```powershell
.\venv\Scripts\python.exe tools\gguf_server_probe_test.py
```

Result: passed on 2026-07-05. The test starts a mock OpenAI-compatible server,
exercises `tools\gguf_server_probe.py` with image+text and text-only payloads,
verifies the JSON report shape, and checks that raw audio keys are not sent.
This protects the probe/report tooling but does not close the real-server gate.

GGUF gate report audit:

```powershell
.\venv\Scripts\python.exe tools\gguf_gate_report_audit_test.py
```

Result: passed on 2026-07-05. The audit requires a named real server
implementation plus both saved reports: `gguf_server_probe.py --report-json`
and `gemma_smoke_test.py --runtime gguf-server --report-json`. It rejects mock
server labels, failed probes, URL mismatches, non-GGUF routes, missing visual
context, and transcript mismatches.

GGUF real-server gate runner:

```powershell
.\venv\Scripts\python.exe tools\gguf_real_server_gate_test.py
.\venv\Scripts\python.exe tools\gguf_real_server_gate.py --server-implementation "LM Studio" --dry-run --report-json smoke_test_assets\gguf\real-server-gate-dry-run.json
.\venv\Scripts\python.exe -m py_compile tools\gguf_real_server_gate.py
```

Result: passed on 2026-07-05. The runner gives the real GGUF/OpenAI-compatible
server gate a single command while preserving the direct probe, full
`--runtime gguf-server` backend smoke, and report-audit evidence chain. It
rejects mock server labels even in dry-run mode and does not contact a server
unless `--dry-run` is omitted.

Post-GGUF-gate-report-audit quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate now runs
`tools\gguf_gate_report_audit_test.py`, compile-checks
`tools\gguf_gate_report_audit.py`, and `tools\open_gate_summary.py --strict`
includes the direct probe, full GGUF backend smoke report, and report audit as
the real-server gate sequence.

Post-GGUF-real-server-gate-runner quick gate:

```powershell
.\venv\Scripts\python.exe tools\gguf_real_server_gate_test.py
.\venv\Scripts\python.exe tools\gguf_real_server_gate.py --server-implementation "LM Studio" --dry-run --report-json smoke_test_assets\gguf\real-server-gate-dry-run.json
.\venv\Scripts\python.exe -m py_compile tools\gguf_real_server_gate.py
.\venv\Scripts\python.exe tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate now runs
`tools\gguf_real_server_gate_test.py`, compile-checks
`tools\gguf_real_server_gate.py`, and `tools\open_gate_summary.py --strict`
shows the one-command real GGUF server gate while keeping the gate open until
the command passes against a named real local server.

Post-GGUF-probe-test quick gate:

```powershell
.\venv\Scripts\python.exe tools\gguf_server_probe_test.py
.\venv\Scripts\python.exe tools\release_readiness_audit.py
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate now runs
`tools\gguf_server_probe_test.py` after the GGUF contract tests.

PyInstaller packaging command:

```powershell
.\venv\Scripts\pyinstaller.exe --noconfirm --distpath smoke_test_assets\packaging\dist --workpath smoke_test_assets\packaging\build OmniDictate.spec
```

Result: passed. Output under
`smoke_test_assets\packaging\dist\OmniDictate` contains 5,307 files totaling
4,793,231,892 bytes. Packaged `OmniDictate.exe` launch smoke passed.

Inno split installer compile command:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DSourceDir='smoke_test_assets\packaging\dist\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-split-fast' /DCompressionMode=none /DSolidCompressionMode=no /DDiskSpanningMode=yes /DDiskSliceSizeMode=2000000000 /DSlicesPerDiskMode=10 OmniDictate_Setup.iss
```

Result: passed. Output is one setup launcher plus three `.bin` slices totaling
4,796,031,102 bytes. Installer install/uninstall smoke remains open because
the script requires admin privileges. See
`docs/evidence/packaging-2026-07-04.md`.

Whisper-only packaging profile command:

```powershell
$env:OMNIDICTATE_PACKAGE_PROFILE='whisper-only'
.\venv\Scripts\pyinstaller.exe --clean --noconfirm --distpath smoke_test_assets\packaging\dist-whisper --workpath smoke_test_assets\packaging\build-whisper OmniDictate.spec
```

Result: passed. Bundle size is 233,985,891 bytes. The packaged
`OmniDictate.exe` launch smoke passed.

Whisper-only single-file Inno compile command:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0-whisper-smoke' /DSourceDir='smoke_test_assets\packaging\dist-whisper\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-fast' /DCompressionMode=none /DSolidCompressionMode=no OmniDictate_Setup.iss
```

Result: passed. Output file
`smoke_test_assets\packaging\installer-whisper-fast\OmniDictate_Setup_v3.0.0-whisper-smoke.exe`
is 236,259,929 bytes. Installer install/uninstall remains open because the
script requires admin privileges.

Per-user Whisper-only installer compile command:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0-whisper-user-smoke' /DSourceDir='smoke_test_assets\packaging\dist-whisper\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-user-smoke' /DCompressionMode=none /DSolidCompressionMode=no /DPrivilegesRequiredMode=lowest /DDefaultDir='{localappdata}\OmniDictateSmoke' /DArchitecturesInstallMode=x64compatible OmniDictate_Setup.iss
```

Result: passed.

Reusable installer smoke command:

```powershell
powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1
```

Result: passed. The smoke silently installed to
`C:\Users\kapil\AppData\Local\OmniDictateSmoke`, launched the installed app for
12 seconds, silently uninstalled, and verified the installed payload was gone.

Release-default Whisper-only installer compile:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0-whisper-release-smoke' /DSourceDir='smoke_test_assets\packaging\dist-whisper\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-release-smoke' /DCompressionMode=none /DSolidCompressionMode=no OmniDictate_Setup.iss
```

Result: passed after adding the optional alternative STT adapter. Output size:
236,263,090 bytes.

Release-default installer smoke:

```powershell
powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1 -InstallerPath smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe -InstallDir "$env:LOCALAPPDATA\OmniDictate" -UseInstallerDefaults
```

Result: passed. The smoke did not pass `/CURRENTUSER` or `/DIR`; the installer
defaulted to `%LOCALAPPDATA%\OmniDictate`, launched the installed app,
uninstalled it, and removed the install directory.

Visual context smoke command:

```powershell
.\venv\Scripts\python.exe tools\visual_context_smoke.py
```

Result: passed. Image attachment, video-frame sampling, active-window screen
capture, full-screen capture, and webcam fail-soft/capture behavior were
verified. See `docs/evidence/visual-context-and-ui-2026-07-04.md`.

Native UI screenshot command:

```powershell
.\venv\Scripts\python.exe tools\ui_smoke_test.py --platform native --screenshot smoke_test_assets\ui\qt-window-smoke-native.png
```

Result: passed. The native Windows screenshot renders readable text. Offscreen
Qt screenshots can show square glyph boxes and should not be treated as the
authoritative visual-font gate.

Settings screenshot commands:

```powershell
.\venv\Scripts\python.exe tools\ui_smoke_test.py --platform native --page settings --backend faster-whisper --prompt-mode pure --screenshot smoke_test_assets\ui\settings-whisper-pure.png
.\venv\Scripts\python.exe tools\ui_smoke_test.py --platform native --page settings --backend gemma-4 --prompt-mode context --gemma-audio-mode hybrid-whisper --screenshot smoke_test_assets\ui\settings-gemma-hybrid-context.png
.\venv\Scripts\python.exe tools\ui_smoke_test.py --platform native --page settings --backend gemma-gguf-server --prompt-mode context --screenshot smoke_test_assets\ui\settings-gguf-context.png
```

Result: passed. Native Windows settings screenshots rendered readable text for
Whisper-only/Pure, Gemma hybrid/context, and GGUF context variants.

Latest Whisper-only packaging rebuild command:

```powershell
$env:OMNIDICTATE_PACKAGE_PROFILE='whisper-only'
.\venv\Scripts\pyinstaller.exe --clean --noconfirm --distpath smoke_test_assets\packaging\dist-whisper --workpath smoke_test_assets\packaging\build-whisper OmniDictate.spec
```

Historical result: passed after adding the optional alternative STT adapter.
That earlier smoke bundle was 233,989,044 bytes and did not contain
`transformers`, `torch`, `bitsandbytes`, or `cv2`. The current final public
artifact intentionally includes PyAV and Hugging Face Hub because
Faster-Whisper needs them in the packaged runtime.

Latest per-user installer compile command:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0-whisper-user-smoke' /DSourceDir='smoke_test_assets\packaging\dist-whisper\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-user-smoke' /DCompressionMode=none /DSolidCompressionMode=no /DPrivilegesRequiredMode=lowest /DDefaultDir='{localappdata}\OmniDictateSmoke' /DArchitecturesInstallMode=x64compatible OmniDictate_Setup.iss
```

Result: passed.

Packaged app screenshot smoke:

```powershell
.\venv\Scripts\python.exe tools\packaged_app_smoke.py
```

Result: passed. The smoke installed the per-user Whisper-only installer,
launched the installed app, saved
`smoke_test_assets\ui\packaged-whisper-main.png`, silently uninstalled, and
verified `C:\Users\kapil\AppData\Local\OmniDictateSmoke` was removed.

Latest isolated first-run packaged app screenshot smoke:

```powershell
.\venv\Scripts\python.exe tools\packaged_app_smoke.py --screenshot smoke_test_assets\ui\packaged-whisper-first-run.png
```

Result: passed. The smoke launched the installed app with a unique temporary
`OMNIDICTATE_SETTINGS_APP` value, saved
`smoke_test_assets\ui\packaged-whisper-first-run.png`, cleaned the temporary
settings key, silently uninstalled, and verified
`C:\Users\kapil\AppData\Local\OmniDictateSmoke` was removed. The screenshot
shows the expected first-run baseline: Faster-Whisper, Pure transcription,
Whisper-only path, context off, and `large-v3-turbo`.

Release-candidate documentation:

```text
docs\release\RELEASE_CHECKLIST_3.0.0-whisper.md
docs\release\RELEASE_NOTES_DRAFT_3.0.0-whisper.md
```

Result: added. These docs define the verified public package as Whisper-only,
list the exact open gates before tagging, and keep Gemma, GGUF, and
alternative STT out of the baseline installer.

Post-release-doc quick gate:

```powershell
git diff --check
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. `git diff --check` reported only existing CRLF
normalization warnings for `.gitignore`, `core_logic.py`,
`hotkey_listener.py`, and `main_gui.py`. The quick gate passed after compile,
route, worker behavior, hotkey listener, import-boundary, alternative STT
adapter, GGUF contract, visual context, microphone diagnostic compile, Gemma
processor, and Qt UI checks. The visual context smoke emitted local virtual
camera vendor logs, but the test completed successfully.

Post-audit/README quick gate:

```powershell
git diff --check
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05 after adding the goal completion audit, refreshing
STT research notes, and aligning README package/model-download wording with
the verified Whisper-only baseline. `git diff --check` again reported only the
existing CRLF normalization warnings for `.gitignore`, `core_logic.py`,
`hotkey_listener.py`, and `main_gui.py`. The quick gate completed
successfully; visual context smoke again emitted local virtual camera vendor
logs but passed.

Release-readiness audit command:

```powershell
.\venv\Scripts\python.exe tools\release_readiness_audit.py
```

Result: passed. The audit verifies that required recovery docs exist, the
completion audit still keeps known live gates open, release checklist state is
honest, README packaging wording matches the Whisper-only baseline, installer
defaults are per-user, local model artifacts are ignored, and the optional
Whisper-only package artifacts remain within the configured size/package
policy when present.

Post-release-audit quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05 with `tools\release_readiness_audit.py` included
as a normal quick-gate step. Visual context smoke emitted local virtual camera
vendor logs but completed successfully.

Post-GGUF-probe quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
.\venv\Scripts\python.exe tools\release_readiness_audit.py
```

Result: passed on 2026-07-05 after adding `tools\gguf_server_probe.py` and the
real-server runbook. The quick gate compiles the probe but does not require a
live GGUF server. The release-readiness audit also passed after the new GGUF
documentation.

Final local recovery-gate rerun after the STT benchmark `--audio-source`
reporting update:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
git diff --check
git diff --cached --name-only
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
```

Result: passed on 2026-07-05. The quick gate completed successfully in about
61 seconds. `git diff --check` reported only the existing CRLF normalization
warnings for `.gitignore`, `core_logic.py`, `hotkey_listener.py`, and
`main_gui.py`. `git diff --cached --name-only` returned no staged files.
`tools\open_gate_summary.py --strict` still reported exactly four open
external gates at that point: physical microphone phrase-match VAD/PTT, Gemma
E4B local weights/live generation, real GGUF/OpenAI-compatible server, and
final public `v3.0.0` artifact rebuild.

The same quick gate passed again on 2026-07-05 after updating
`docs\evidence\live-microphone-audio-device-2026-07-04.md` with the user's
repeated-mismatch/Ctrl+C output. The open physical microphone gate remains a
quality/phrase-match/PTT gate, not a device-open gate.

Prompted microphone diagnostic path:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 0.2 --prompt --countdown 0 --allow-low-level --output smoke_test_assets\microphone\prompt-path-smoke.wav --report-json smoke_test_assets\microphone\prompt-path-smoke-report.json
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The focused smoke opened the Realtek microphone,
printed the expected phrase, recorded a short low-level sample, and wrote a
JSON report with `prompted: true` and `expected: hello world this is a simple
speech test`. The full quick gate passed afterward, and
`tools\open_gate_summary.py --strict` now prints the guided capture command
for the open physical microphone gate.

Guided VAD/PTT loop evidence command:

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model large-v3-turbo --mode both --timeout 40 --manual --countdown 3 --max-transcripts 1 --report-json smoke_test_assets\microphone\live-loop-large-v3-turbo-report.json
```

Result: command path documented on 2026-07-05. The tool now prints a countdown
for each manual VAD/PTT phase and writes a JSON report for pass, failure, or
interruption with model, mode, expected phrase, per-mode passing results, all
worker transcripts, statuses, worker errors, selected `device`,
`max_transcripts`, `outcome`, `failed_mode`, and failure text. It now fails
after one mismatched transcript by default so a bad phrase run does not require
Ctrl+C. If the intended input is not the Windows default, append
`--device <numeric sounddevice input index>`. Use a device display name only
when the inventory shows it is unique. The gate remains open until this
command passes on real speech.

Post-guided-loop quick gate:

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --help
.\venv\Scripts\python.exe tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. `--help` shows `--countdown` and
`--report-json`, the release-readiness audit passed, and
`open_gate_summary.py --strict` now prints the full command sequence for each
open external gate. The full quick gate passed afterward.

Microphone evidence tooling tests:

```powershell
.\venv\Scripts\python.exe tools\microphone_evidence_tooling_test.py
```

Result: passed on 2026-07-05. The tests cover live-loop JSON report shape,
failed-report mode/transcript evidence, manual prompt wording, the three-step
physical microphone open-gate sequence, and `Next`/`Then` output from
`tools\open_gate_summary.py --strict` without opening a microphone.

Post-microphone-evidence-test quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate now runs
`tools\microphone_evidence_tooling_test.py` after the open-gate summary.

Post-artifact-manifest-audit quick gate:

```powershell
.\venv\Scripts\python.exe tools\artifact_manifest_audit.py
.\venv\Scripts\python.exe tools\release_readiness_audit.py
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The focused artifact audit recomputed local
artifact sizes, SHA256 hashes, and packaged screenshot dimensions. The full
quick gate now runs `tools\artifact_manifest_audit.py` after the
release-readiness audit.

Final release preflight:

```powershell
.\venv\Scripts\python.exe tools\final_release_preflight.py
```

Result: passed on 2026-07-05. The tool checked static prerequisites for the
final public `v3.0.0` build and printed the final PyInstaller, Inno Setup,
installer smoke, package-size audit, and hash commands without building or
publishing.

Post-final-release-preflight quick gate:

```powershell
.\venv\Scripts\python.exe tools\final_release_preflight.py --json
.\venv\Scripts\python.exe tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The JSON preflight reported `ready-to-run` with
no failures, the release audit passed, the open-gate summary now points at
`tools\final_release_preflight.py` and the final `dist-whisper-final` /
`installer-whisper-final` paths, and the full quick gate passed afterward.

Final release tooling tests:

```powershell
.\venv\Scripts\python.exe tools\final_release_tooling_test.py
```

Result: passed on 2026-07-05. The tests verify that the final preflight uses
the public `OmniDictate_Setup_v3.0.0.exe` name, final artifact directories,
no local smoke suffix, a valid JSON payload, and an open-gate final release
sequence aligned with the preflight paths.

Final release gate audit tests:

```powershell
.\venv\Scripts\python.exe tools\final_release_gate_audit_test.py
```

Result: passed on 2026-07-05. The tests prove that final publication evidence
requires a matching preflight report, non-smoke `OmniDictate_Setup_v3.0.0.exe`
installer name, nonempty final bundle and installer, size limits, SHA256
recording, and a durable `final-release-gate-report.json`.

Final public release gate runner:

```powershell
.\venv\Scripts\python.exe tools\final_public_release_gate_test.py
.\venv\Scripts\python.exe tools\final_public_release_gate.py --dry-run --report-json smoke_test_assets\packaging\final-public-release-gate-dry-run.json
.\venv\Scripts\python.exe -m py_compile tools\final_public_release_gate.py
```

Result: passed on 2026-07-05. The runner gives the final
public release artifact gate a single command while preserving final preflight,
Whisper-only PyInstaller, Inno Setup, packaged Whisper runtime smoke,
installer smoke, package-size audit, installer hash, and final artifact audit
as internal steps. The dry run writes command intent without building
artifacts.

Post-final-release-gate-audit quick gate:

```powershell
.\venv\Scripts\python.exe tools\final_release_gate_audit_test.py
.\venv\Scripts\python.exe tools\final_release_tooling_test.py
.\venv\Scripts\python.exe -m py_compile tools\final_release_preflight.py tools\final_release_gate_audit.py
.\venv\Scripts\python.exe tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
.\venv\Scripts\python.exe tools\goal_completion_audit.py
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The full quick gate now runs
`tools\final_release_gate_audit_test.py` after
`tools\final_release_tooling_test.py`, compiles
`tools\final_release_gate_audit.py`, runs
`tools\final_public_release_gate_test.py`, compile-checks
`tools\final_public_release_gate.py`, and the open-gate summary now shows the
one-command final public release gate.

Goal completion audit:

```powershell
.\venv\Scripts\python.exe tools\goal_completion_audit_test.py
.\venv\Scripts\python.exe tools\goal_completion_audit.py
```

Result: passed on 2026-07-05. The audit verifies that
`docs\ai\COMPLETION_AUDIT.md` still maps the original recovery objective,
keeps the physical microphone, Gemma E4B, and real GGUF server rows
incomplete, agrees with the open gates from `tools\open_gate_summary.py`, and
now rejects a saved `release-decision-matrix.json` that claims publish-ready
state while those three release-scope gates are still pending.

Post-goal-completion-audit quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate now runs
`tools\goal_completion_audit.py` immediately after
`tools\open_gate_summary.py --strict`, and the physical microphone open-gate
command now includes `--max-transcripts 1` for bounded mismatch handling.

Post-failed-microphone-report quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The live microphone report schema now records
all worker transcripts and `failed_mode` for failed or interrupted runs, and
`tools\microphone_evidence_tooling_test.py` covers that evidence path without
opening the microphone.

Physical microphone gate runner:

```powershell
.\venv\Scripts\python.exe tools\physical_microphone_gate_test.py
.\venv\Scripts\python.exe tools\physical_microphone_gate.py --dry-run --device 1 --report-json smoke_test_assets\microphone\physical-gate-dry-run.json
.\venv\Scripts\python.exe tools\physical_microphone_run_card_test.py
.\venv\Scripts\python.exe tools\physical_microphone_run_card.py --report-json smoke_test_assets\microphone\physical-gate-dry-run.json
```

Result: passed on 2026-07-05. The runner gives the physical microphone gate a
single guided command while preserving the prompted capture, saved-WAV
revalidation, VAD/PTT live-loop report, and report-audit evidence chain. The
dry run writes command intent without opening the microphone, and its JSON now
includes structured `manual_prompt` metadata: phrase, selected device,
countdown, recording duration, live-loop timeout, required VAD/PTT modes, and
the pass rule. The run-card tool prints that JSON as terminal-ready human
instructions plus the top-level physical gate command.

Microphone gate report audit:

```powershell
.\venv\Scripts\python.exe tools\microphone_gate_report_audit_test.py
```

Result: passed on 2026-07-05. The new validator rejects unprompted,
low-level, mismatched, failed, or VAD-only/PTT-only microphone reports and
passes only when the saved capture report and live-loop report together prove
prompted speech, healthy audio levels, matching transcription, passing VAD,
passing PTT, and no worker errors.

Post-microphone-gate-report-audit quick gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate now runs
`tools\microphone_gate_report_audit_test.py`, compile-checks
`tools\microphone_gate_report_audit.py`, and `tools\open_gate_summary.py
--strict` includes the report audit as the final physical microphone proof
step.

Post-physical-microphone-gate-runner quick gate:

```powershell
.\venv\Scripts\python.exe tools\physical_microphone_gate_test.py
.\venv\Scripts\python.exe tools\physical_microphone_run_card_test.py
.\venv\Scripts\python.exe tools\microphone_evidence_tooling_test.py
.\venv\Scripts\python.exe tools\physical_microphone_gate.py --dry-run --device 1 --report-json smoke_test_assets\microphone\physical-gate-dry-run.json
.\venv\Scripts\python.exe tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
.\venv\Scripts\python.exe tools\goal_completion_audit.py
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The quick gate now runs
`tools\physical_microphone_gate_test.py` after microphone evidence tooling,
compile-checks `tools\physical_microphone_gate.py`, and
`tools\open_gate_summary.py --strict` shows the one-command physical
microphone gate while keeping the gate open until a human spoken run passes.
The runner accepts `--device` and forwards it to both physical capture and
live VAD/PTT loop evidence. Saved-WAV revalidation records that selected input
as report metadata, and `tools\microphone_gate_report_audit.py` rejects a
capture/live-loop device mismatch when both reports declare one.

Physical microphone reuse-capture retry path:

```powershell
.\venv\Scripts\python.exe tools\physical_microphone_gate_test.py
.\venv\Scripts\python.exe tools\physical_microphone_gate.py --dry-run --reuse-capture --report-json smoke_test_assets\microphone\physical-gate-reuse-dry-run.json
.\venv\Scripts\python.exe -m py_compile tools\physical_microphone_gate.py
```

Result: passed on 2026-07-05. The physical microphone gate now supports
`--reuse-capture` for the case where the prompted saved-WAV capture and capture
report already passed but the VAD/PTT live loop needs another attempt. The
reuse path skips capture/revalidation, runs the live loop plus final audit, and
fails before opening the microphone if the saved WAV or capture report is
missing.

Physical microphone audio-device inventory:

```powershell
.\venv\Scripts\python.exe tools\microphone_evidence_tooling_test.py
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --list-devices --report-json smoke_test_assets\microphone\audio-device-inventory.json
.\venv\Scripts\python.exe -m py_compile tools\microphone_capture_diagnostic.py tools\microphone_evidence_tooling_test.py
```

Result: passed on 2026-07-05 after normalizing PortAudio default-device
metadata for JSON output. The command lists input-capable devices without
recording audio and writes `smoke_test_assets\microphone\audio-device-inventory.json`
so the next physical gate attempt can choose an explicit `--device` when the
Windows default input is ambiguous. The saved inventory currently recommends
numeric `--device 1` and warns about duplicate Realtek input names.

E4B/GGUF local fixture fast-fail checks:

```powershell
.\venv\Scripts\python.exe tools\gemma_e4b_gate_test.py
.\venv\Scripts\python.exe tools\gguf_real_server_gate_test.py
.\venv\Scripts\python.exe -m py_compile tools\gemma_e4b_gate.py tools\gguf_real_server_gate.py
```

Result: passed on 2026-07-05. The E4B and GGUF real-server gate runners now
validate local audio/image fixtures before loading E4B or contacting a server,
write failed JSON reports for missing fixtures, and keep `results: []` for
those local prerequisite failures.

Release scope-out authorization audit:

```powershell
.\venv\Scripts\python.exe tools\release_scope_decision_audit_test.py
.\venv\Scripts\python.exe tools\publication_blocker_audit_test.py
.\venv\Scripts\python.exe tools\release_scope_decision_audit.py
.\venv\Scripts\python.exe -m py_compile tools\release_scope_decision_audit.py tools\publication_blocker_audit.py
```

Result: passed on 2026-07-05. A future `scoped-out` release-scope decision now
requires dated `User authorized ... on YYYY-MM-DD` text plus a dated
`Updated ... on YYYY-MM-DD` release-note/checklist marker; vague approval text
does not remove a publication blocker.

Release status next recommended command:

```powershell
.\venv\Scripts\python.exe tools\release_status_report_test.py
.\venv\Scripts\python.exe tools\release_status_report.py --report-json smoke_test_assets\packaging\release-status-report.json
.\venv\Scripts\python.exe -m py_compile tools\release_status_report.py
```

Result: passed on 2026-07-05. The release status report now exposes
`next_preparation_command`, `next_preparation_commands`,
`next_recommended_command`, and `next_recommended_commands`. With the current
audio-device inventory, the preparation command prints the physical microphone
run card and the first recommended command plus physical open-gate payload both
use numeric `--device 1`.

Handoff recommended-command guard:

```powershell
.\venv\Scripts\python.exe tools\handoff_next_action_audit_test.py
.\venv\Scripts\python.exe tools\handoff_next_action_audit.py
.\venv\Scripts\python.exe -m py_compile tools\handoff_next_action_audit.py
```

Result: passed on 2026-07-05. The handoff next-action audit now reads
`tools\release_status_report.py` output and fails if `docs\ai\HANDOFF.md`
does not include the current `next_recommended_command`.

External gate orchestrator:

```powershell
.\venv\Scripts\python.exe tools\external_gate_orchestrator_test.py
.\venv\Scripts\python.exe tools\external_gate_orchestrator.py --report-json smoke_test_assets\external-gates-dry-run.json
.\venv\Scripts\python.exe -m py_compile tools\external_gate_orchestrator.py
```

Result: passed on 2026-07-05. The orchestrator dry-runs the physical
microphone, Gemma E4B, and real GGUF server gate runners by default and
writes one aggregate report. With the saved audio-device inventory, the
default physical microphone dry-run now passes numeric `--device 1`; use
`--microphone-device <numeric sounddevice input index>` as an explicit
override. Use a device display name only when the inventory shows it is unique.
Real gate execution is opt-in with `--execute`, so the normal quick gate can
prove command wiring without opening the microphone, downloading weights,
requiring a GGUF server, or rebuilding the public installer.

Post-external-gate-orchestrator quick gate:

```powershell
.\venv\Scripts\python.exe tools\external_gate_orchestrator.py --report-json smoke_test_assets\external-gates-dry-run.json
.\venv\Scripts\python.exe tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
.\venv\Scripts\python.exe tools\goal_completion_audit.py
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The full quick gate now runs
`tools\external_gate_orchestrator_test.py` and compile-checks
`tools\external_gate_orchestrator.py`. `tools\goal_completion_audit.py` still
reports the objective open with the physical microphone gate pending.

Final public artifact gate:

```powershell
.\venv\Scripts\python.exe tools\final_public_release_gate_test.py
.\venv\Scripts\python.exe -m py_compile tools\final_public_release_gate.py tools\file_sha256.py
.\venv\Scripts\python.exe tools\final_public_release_gate.py --report-json smoke_test_assets\packaging\final-public-release-gate-report.json
```

Result: passed on 2026-07-05 after two runner fixes. The first real run
proved preflight, PyInstaller, and Inno Setup, then failed because the runner
passed literal `$env:LOCALAPPDATA\OmniDictate` to `installer_smoke.ps1`. The
second run reached installer smoke, size audit, and then failed because the
standalone `Get-FileHash` subprocess could not resolve that cmdlet. The final
runner now passes a concrete install directory, opts into
`-AllowRemoveExisting` for repeatable installer smokes after partial failures,
and uses `tools\file_sha256.py` for SHA256 output.

Final artifact evidence:

```text
bundle: smoke_test_assets\packaging\dist-whisper-final\OmniDictate
bundle_bytes: 322225944
installer: smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe
installer_bytes: 324505897
installer_sha256: 3DD9CF5CD1E172D41208DDD3BDC3380A5A18BA1DDBA4BD5F3CE7FDEA2CEA10A5
final_release_gate_audit: ready
final_public_release_gate: passed
```

Post-final-public-artifact quick gate:

```powershell
.\venv\Scripts\python.exe tools\artifact_manifest_audit.py
.\venv\Scripts\python.exe tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\goal_completion_audit.py
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The open-gate summary now reports three
remaining external gates: physical microphone phrase-match VAD/PTT, Gemma E4B
local weights/live generation, and real GGUF/OpenAI-compatible server.

Post-three-gate-stale-doc guard:

```powershell
.\venv\Scripts\python.exe tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
.\venv\Scripts\python.exe tools\goal_completion_audit.py
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The release-readiness audit now rejects
current-sounding stale phrases that claim four current open gates or an
unrebuilt final public artifact.

Post-final-artifact-checklist-alignment quick gate:

```powershell
.\venv\Scripts\python.exe tools\release_readiness_audit.py
.\venv\Scripts\python.exe tools\artifact_manifest_audit.py
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed on 2026-07-05. The release checklist now leads with the final
public installer evidence instead of the earlier smoke artifact, and the
release-readiness audit requires the final installer size and SHA256 markers.

Publication blocker audit:

```powershell
.\venv\Scripts\python.exe tools\publication_blocker_audit_test.py
.\venv\Scripts\python.exe tools\publication_blocker_audit.py --json --report-json smoke_test_assets\packaging\publication-blockers.json
.\venv\Scripts\python.exe -m py_compile tools\publication_blocker_audit.py
```

Result: passed on 2026-07-05. The audit confirmed the final public artifact
reports are passed/ready and wrote a `blocked` report with exactly three
remaining publication blockers: physical microphone phrase-match VAD/PTT,
Gemma E4B live generation, and real GGUF server. The JSON report now includes
`schema_version`, `generated_at_utc`, and `open_gate_details` with evidence
paths plus next commands for each blocker. It also records
`scope_decisions_doc` and `scope_gate_statuses`; `pending` release-scope
decision rows remain blockers, while future `proven` or authorized
`scoped-out` rows are the machine-readable path to remove a gate from the
publication blocker report.

ASR source-refresh audit:

```powershell
.\venv\Scripts\python.exe tools\release_readiness_audit.py
```

Result: passed on 2026-07-05 after adding the live ASR source refresh,
evaluation lanes, IBM Granite Speech rich-transcript boundary, D013, and
updated alternative-STT product acceptance markers.

Objective evidence matrix audit:

```powershell
.\venv\Scripts\python.exe tools\goal_completion_audit.py
```

Result: passed on 2026-07-05 after adding the Objective Evidence Matrix to
`docs\ai\COMPLETION_AUDIT.md`. The audit now requires proof standards,
authoritative evidence, and closure conditions for the original objective
requirements while keeping physical microphone, Gemma E4B, and real GGUF
incomplete.

Phase 4 release execution checklist audit:

```powershell
.\venv\Scripts\python.exe tools\release_readiness_audit.py
```

Result: passed on 2026-07-05 after adding
`docs\implementation-plans-and-checklists\phase-4-release-execution.md`.
The audit now requires the checklist to keep the physical microphone, E4B,
real GGUF, and publication-decision sequence explicit.

Release status report:

```powershell
.\venv\Scripts\python.exe tools\release_status_report_test.py
.\venv\Scripts\python.exe tools\release_status_report.py --json --report-json smoke_test_assets\packaging\release-status-report.json
.\venv\Scripts\python.exe -m py_compile tools\release_status_report.py
```

Result: passed on 2026-07-05. The reporter produced a valid `blocked`
status with final artifact status `ready`, final public report status
`passed`, the current installer SHA256, the aggregate external-gate dry-run
command, the inventory-backed microphone default, the selected-microphone
dry-run variant, the physical microphone run-card preparation command, and the
remaining technical gates with their release-scope statuses. The JSON report now includes `schema_version` and
`generated_at_utc` metadata, and nests the timestamped publication blocker
snapshot whose `open_gate_details` use the same inventory-backed physical
microphone command.

Release decision matrix report:

```powershell
.\venv\Scripts\python.exe tools\external_gate_prerequisite_audit_test.py
.\venv\Scripts\python.exe tools\external_gate_prerequisite_audit.py --json --report-json smoke_test_assets\external-gate-prerequisites.json
.\venv\Scripts\python.exe tools\release_decision_matrix_report_test.py
.\venv\Scripts\python.exe tools\release_decision_matrix_report.py --json --report-json smoke_test_assets\packaging\release-decision-matrix.json
.\venv\Scripts\python.exe -m py_compile tools\external_gate_prerequisite_audit.py
.\venv\Scripts\python.exe -m py_compile tools\release_decision_matrix_report.py
```

Result: passed on 2026-07-05. The prerequisite audit writes a no-live-side-effect
snapshot of missing fixture/report/model prerequisites. The matrix writes one
compact `blocked` report with final artifact readiness, saved GitHub preflight
state, one pending release-scope gate plus two scoped-out technical gates, evidence paths, prerequisite
gaps, closure reports, closure-audit commands, inventory-backed dry-run
commands, run-card preparation commands, and real closure commands.

Release snapshot freshness audit:

```powershell
.\venv\Scripts\python.exe tools\release_snapshot_freshness_audit_test.py
.\venv\Scripts\python.exe tools\release_snapshot_freshness_audit.py --json
.\venv\Scripts\python.exe -m py_compile tools\release_snapshot_freshness_audit.py
```

Result: passed on 2026-07-05. The audit recomputes the publication blocker,
release status, GitHub release preflight, external-gate dry-run, and release
prerequisite and decision matrix reports in memory, ignores only
`generated_at_utc`, and fails if the saved JSON snapshots have stale gate
lists, artifact state, installer hashes, remote tag state, GitHub preflight
scope blockers, external-gate `release_scope_status` values, prerequisite
rows, matrix rows, or dry-run command shapes.

Open-gate summary scope status:

```powershell
.\venv\Scripts\python.exe tools\open_gate_summary_test.py
.\venv\Scripts\python.exe tools\open_gate_summary.py --json --strict
.\venv\Scripts\python.exe -m py_compile tools\open_gate_summary.py
```

Result: passed on 2026-07-05. The open-gate summary now includes
`scope_decisions_doc`, `release_scope_status: pending` for physical microphone,
and `release_scope_status: scoped-out` for Gemma E4B / real GGUF. It injects the inventory-backed numeric `--device 1` into the physical
microphone command so the summary matches the release-status recommendation.
and the text output prints `Scope: pending` or `Scope: scoped-out` before the evidence/dependency
details.

Release scope decision audit:

```powershell
.\venv\Scripts\python.exe tools\release_scope_decision_audit_test.py
.\venv\Scripts\python.exe tools\release_scope_decision_audit.py
.\venv\Scripts\python.exe -m py_compile tools\release_scope_decision_audit.py
```

Result: passed on 2026-07-05. The audit validates
`docs\release\RELEASE_SCOPE_DECISIONS_3.0.0.md`, keeps the physical
microphone gate marked `pending`, keeps Gemma E4B and real GGUF marked
`scoped-out`, and rejects any `scoped-out` decision unless it carries explicit
user authorization and a release note/checklist update marker.

GitHub release preflight:

```powershell
.\venv\Scripts\python.exe tools\github_release_preflight_test.py
.\venv\Scripts\python.exe tools\github_release_preflight.py --json --report-json smoke_test_assets\packaging\github-release-preflight.json
.\venv\Scripts\python.exe -m py_compile tools\github_release_preflight.py
```

Result: passed on 2026-07-05. The preflight queried the remote tag state,
found the last public `v2.0.2` tag visible, kept `v3.0.0` unavailable for a
future release, and wrote a valid `blocked` report because the release status
still has three open release-scope gates. The JSON report now includes
`schema_version`, `generated_at_utc`, `scope_gate_statuses`, and
`pending_release_scope_gates` at the top level so GitHub publication preflight
shows the same blockers as the local publication audit.

Handoff next-action audit:

```powershell
.\venv\Scripts\python.exe tools\handoff_next_action_audit_test.py
.\venv\Scripts\python.exe tools\handoff_next_action_audit.py
.\venv\Scripts\python.exe -m py_compile tools\handoff_next_action_audit.py
```

Result: passed on 2026-07-05. The audit verifies that
`docs\ai\HANDOFF.md` still points at the Phase 4 checklist, GitHub release
preflight, release status report, publication blocker report, external-gate
dry run, physical
microphone gate, E4B gate, real GGUF gate, and normal quick verification.

Preload model worker quick gate:

```powershell
.\venv\Scripts\python.exe tools\preload_model_worker_test.py
```

Result: added on 2026-07-05. The test uses a fake backend to verify that launch
preload loads the selected backend, emits success/failure status, and unloads
without opening the microphone or requiring real Gemma weights.
