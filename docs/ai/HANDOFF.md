# OmniDictate Handoff

Date: 2026-07-06
Owner: Codex
Repo: `D:\OmniDictate - GUI`

## Current Goal

Recover the incomplete Gemma-era OmniDictate work, compare it to the
known-good `v2.0.2` release, decide whether the direction is salvageable, and
prepare the next phase with documentation, acceptance criteria, and automated
verification.

## Current State

- `main` is at `7d32a12` (`v2.0.2`, also `origin/main`).
- All Gemma-era work is local/uncommitted.
- Modified tracked files: `OmniDictate.spec`, `OmniDictate_Setup.iss`,
  `README.md`, `core_logic.py`, `hotkey_listener.py`, `main_gui.py`,
  `requirements.txt`, `style.qss`, `.gitignore`.
- New local code/docs include `app_settings.py`, `engines/`,
  `model_downloader.py`, `tools/`, and `docs/`.
- Large model caches exist locally and must not be committed.

## Findings

- The Gemma direction is not fundamentally wrong. Official Gemma 4 E2B/E4B
  docs now support audio ASR and audio translation.
- The local code has a reasonable backend abstraction:
  `WhisperBackend`, `Gemma4Backend`, and `GemmaGGUFBackend`.
- The safe product spine remains Whisper-only dictation.
- Gemma should remain experimental until live model/audio gates pass.
- Earlier Gemma recovery planning contained stale advice. Treat it as history,
  not canonical release truth.
- The copied `docs/loop-principle` content was from another repo; use the
  OmniDictate-specific docs in `docs/ai/`.

## Verified This Turn

- `git status --short --branch`
- `.\venv\Scripts\python.exe tools\route_smoke_test.py`
- `.\venv\Scripts\python.exe -m compileall app_settings.py core_logic.py hotkey_listener.py main_gui.py model_downloader.py engines tools`
- Offscreen Qt window construction with `OmniDictateApp(start_hotkeys=False)`
- Gemma processor-only audio smoke using local `Gemma4Processor` metadata
- Gemma processor-only audio+image smoke using local metadata
- `transformers 5.5.0` exposes `AutoModelForMultimodalLM`
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding the quick gate runner
- `powershell -ExecutionPolicy Bypass -File tools\verify_whisper.ps1 -Model tiny`
  passed with a generated Windows SAPI WAV fixture
- `.\venv\Scripts\python.exe tools\worker_behavior_test.py` passed
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding worker behavior tests to the quick gate
- Headless worker tests verify punctuation/filter routing, PTT release queueing,
  VAD silence-after-speech queueing, and the own-window typing guard
- `powershell -ExecutionPolicy Bypass -File tools\verify_whisper.ps1 -Model large-v3-turbo`
  passed with the generated Windows SAPI WAV fixture
- `.\venv\Scripts\python.exe tools\live_typing_smoke.py` passed by opening
  Notepad, holding text while the target was treated as OmniDictate, then
  typing into Notepad through the worker typing thread
- `.\venv\Scripts\python.exe tools\full_loop_synthetic_smoke.py --model large-v3-turbo`
  passed: generated speech flowed through VAD, Whisper, text routing, and the
  worker typing thread into Notepad with an 8/8 expected-word match
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding the live typing and synthetic full-loop smoke scripts
- `.\venv\Scripts\python.exe tools\global_hotkey_smoke.py` passed after fixing
  Ctrl+1/2/3 handling for Windows virtual-key events
- `.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode both --timeout 28`
  was attempted and blocked because PortAudio/sounddevice could not open the
  local Realtek microphone input; see
  `docs/evidence/live-microphone-audio-device-2026-07-04.md`
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding hotkey listener tests, global-hotkey smoke, and live-microphone
  smoke tooling
- `.\venv\Scripts\python.exe tools\gemma_smoke_test.py ... --audio-mode hybrid-whisper`
  passed for local Gemma 4 E2B 4-bit with an image fixture: route
  `Whisper -> Gemma`, `cuda:0`, 10.47s generation latency, 8/8 expected words
- `.\venv\Scripts\python.exe tools\gemma_smoke_test.py ... --audio-mode native-audio`
  passed for local Gemma 4 E2B 16-bit with an image fixture: route
  `Native Gemma audio`, CPU device map, 246.39s generation latency, 8/8
  expected words
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding asserted Gemma smoke output checks and R2 evidence docs
- `.\venv\Scripts\python.exe tools\gguf_contract_test.py` passed with a mock
  OpenAI-compatible server: `/v1/models` auto-selection, image+text chat
  payload, no raw audio in the server request, and Pure-mode server bypass
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding GGUF server contract tests to the quick gate
- `main_gui.py` now labels Gemma 4 E2B as the verified local path and Gemma 4
  E4B as unverified in the model selector copy/tooltips
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after the E2B/E4B UI wording update
- User reran
  `.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode both --timeout 28`
  after granting microphone permission. The Realtek microphone opened, VAD
  recorded, queued, and transcribed one utterance, but the transcript was
  `We're open to the world.` versus expected `hello world this is a simple
  speech test` (1/8 expected words). PTT was not reached because the VAD phase
  failed the phrase assertion.
- `tools\live_microphone_smoke.py` was fixed so it checks each mismatched
  transcript once, records the best match, times out cleanly, and supports
  `--capture-only` for hardware-capture diagnosis.
- `.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode vad --timeout 16 --capture-only`
  was rerun after the fix. It opened the Realtek microphone and exited cleanly
  with `Timed out waiting for any transcript`, confirming the stale-transcript
  loop is fixed but leaving the physical capture/phrase gate open.
- Added `tools\microphone_capture_diagnostic.py`, a fixed-duration physical
  microphone recorder that saves a WAV, reports RMS/peak/active/clipping
  stats, and can optionally transcribe that exact WAV through Whisper.
- Strict non-interactive diagnostic
  `.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 3 --output smoke_test_assets\microphone\diagnostic-noninteractive.wav`
  opened the Realtek microphone and saved a WAV, then failed as designed
  because the room/input was near-silent: RMS `0.00021`, peak `0.00119`,
  active `0%`.
- Evidence-only baseline
  `.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 3 --allow-low-level --output smoke_test_assets\microphone\diagnostic-quiet-baseline.wav`
  passed and saved a quiet baseline WAV: RMS `0.00022`, peak `0.00101`,
  active `0%`.
- PyInstaller isolated build passed with output under
  `smoke_test_assets\packaging\dist\OmniDictate`: 5,307 files,
  4,793,231,892 bytes, `OmniDictate.exe` size 68,936,248 bytes.
- Packaged `OmniDictate.exe` launch smoke passed by starting the packaged app
  hidden, confirming the process stayed alive during the launch window, and
  stopping it.
- Inno default high-compression build was stopped after a 30 minute timeout.
- Inno fast single-file build failed because the installer exceeded
  2,100,000,000 bytes without disk spanning.
- Inno split no-compression build passed using `DiskSpanning=yes`, producing
  `OmniDictate_Setup_v3.0.0.exe` plus three `.bin` slices totaling
  4,796,031,102 bytes. See `docs/evidence/packaging-2026-07-04.md`.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after the live microphone smoke-loop fix and packaging evidence updates.
- Added lazy imports and a PyInstaller `OMNIDICTATE_PACKAGE_PROFILE=whisper-only`
  profile so the baseline release package excludes Gemma/Torch/video/download
  stacks.
- Added `tools\import_boundary_test.py` to the quick gate and
  `tools\package_size_audit.py` for repeatable bundle measurements.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after the import-boundary and packaging-profile changes.
- Clean Whisper-only PyInstaller build passed:
  233,985,891 byte bundle at `smoke_test_assets\packaging\dist-whisper\OmniDictate`.
- Packaged Whisper-only launch smoke passed (`alive=True` after 12 seconds,
  process then stopped).
- Single-file no-compression Whisper-only Inno compile passed:
  `smoke_test_assets\packaging\installer-whisper-fast\OmniDictate_Setup_v3.0.0-whisper-smoke.exe`,
  236,259,929 bytes.
- `OmniDictate_Setup.iss` now supports explicit smoke overrides for per-user
  install: `PrivilegesRequiredMode`, `DefaultDir`, and
  `ArchitecturesInstallMode`.
- Per-user Whisper-only installer compile passed:
  `smoke_test_assets\packaging\installer-whisper-user-smoke\OmniDictate_Setup_v3.0.0-whisper-user-smoke.exe`.
- Added `tools\installer_smoke.ps1`.
- `powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1` passed:
  silent install to `%LOCALAPPDATA%\OmniDictateSmoke`, installed app launch
  alive after 12 seconds, silent uninstall exit 0, and installed payload
  removed.
- `OmniDictate_Setup.iss` now defaults to the verified per-user release path:
  `PrivilegesRequired=lowest`, `{localappdata}\OmniDictate`, and
  `x64compatible`. Admin/Program Files remains available by explicit
  preprocessor override.
- Release-default Whisper-only installer compile passed without
  privilege/directory overrides:
  `smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe`,
  236,259,922 bytes.
- `powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1 -InstallerPath smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe -InstallDir "$env:LOCALAPPDATA\OmniDictate" -UseInstallerDefaults`
  passed: installer defaults installed to `%LOCALAPPDATA%\OmniDictate`,
  launched, uninstalled, and removed the install directory.
- Added `tools\visual_context_smoke.py` and wired it into
  `tools\verify_local.ps1`.
- `.\venv\Scripts\python.exe tools\visual_context_smoke.py` passed: generated
  image attachment, generated video-frame sampling, active-window capture,
  full-screen capture, and webcam fail-soft/capture behavior.
- `tools\ui_smoke_test.py` now supports `--platform native` for real Windows
  visual screenshots while preserving offscreen mode for the quick gate.
- `.\venv\Scripts\python.exe tools\ui_smoke_test.py --platform native --screenshot smoke_test_assets\ui\qt-window-smoke-native.png`
  passed and produced a readable Windows screenshot. Offscreen screenshots can
  show square glyph boxes and are not the visual-font authority.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding the visual context smoke and native UI screenshot mode.
- Native settings-page screenshots passed for Whisper-only/Pure,
  Gemma hybrid/context, and GGUF context variants:
  `smoke_test_assets\ui\settings-whisper-pure.png`,
  `smoke_test_assets\ui\settings-gemma-hybrid-context.png`, and
  `smoke_test_assets\ui\settings-gguf-context.png`.
- Clean Whisper-only PyInstaller rebuild passed again:
  233,985,911 byte bundle at
  `smoke_test_assets\packaging\dist-whisper\OmniDictate`.
- Per-user Whisper-only installer compile passed again against the rebuilt
  bundle:
  `smoke_test_assets\packaging\installer-whisper-user-smoke\OmniDictate_Setup_v3.0.0-whisper-user-smoke.exe`.
- `.\venv\Scripts\python.exe tools\packaged_app_smoke.py --screenshot smoke_test_assets\ui\packaged-whisper-first-run.png`
  passed: installed the per-user Whisper-only installer, launched the installed
  app with isolated first-run `QSettings`, captured
  `smoke_test_assets\ui\packaged-whisper-first-run.png`, cleaned the temporary
  settings key, silently uninstalled, and verified the install directory was
  removed.
- The first-run packaged screenshot shows the expected Whisper baseline:
  Faster-Whisper backend, Pure transcription mode, Whisper-only path, context
  off, and `large-v3-turbo`.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding `tools\microphone_capture_diagnostic.py` to the quick gate as a
  compile-only diagnostic check.
- Added optional `TransformersASRBackend` for experimental non-Whisper ASR.
  The default `faster-whisper` path still does not eagerly import
  Transformers/Torch; `tools\import_boundary_test.py` remains green.
- Added `tools\alternative_stt_adapter_test.py` to the quick gate. It uses a
  fake ASR pipeline so normal verification does not download models or pull
  the experimental runtime into the baseline.
- Live Moonshine-tiny spike passed:
  `.\venv\Scripts\python.exe tools\alternative_stt_smoke.py --model UsefulSensors/moonshine-tiny --min-word-ratio 0.6 --keep-audio`
  loaded `UsefulSensors/moonshine-tiny`, route `Alternative STT`, latency
  1.83s, 8/8 expected words.
- Whisper comparison on the same fixture style: `large-v3-turbo` reported
  0.69s and 8/8, while Whisper `tiny` reported 0.63s and 8/8.
- Moonshine-tiny local Hugging Face cache footprint:
  `C:\Users\kapil\.cache\huggingface\hub\models--UsefulSensors--moonshine-tiny`,
  12 files, 110,376,063 bytes. Windows emitted the expected Hugging Face
  symlink-cache warning without Developer Mode/admin.
- R4 decision: keep the optional alternative STT adapter/smoke/benchmark for
  future experiments. Moonshine-tiny now has a synthetic latency win after
  warmup, but do not promote it to default UI or the Whisper-only release until
  real microphone snippets, command/punctuation behavior, and
  package/import/cache boundary evidence pass.
- Post-adapter Whisper-only PyInstaller rebuild passed:
  `smoke_test_assets\packaging\dist-whisper\OmniDictate`, 233,989,044 bytes.
  Audit confirmed `transformers`, `torch`, `bitsandbytes`, `cv2`, `av`, and
  `huggingface_hub` are absent from `_internal`.
- Post-adapter release-default Inno compile and installer smoke passed:
  `smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe`,
  236,263,090 bytes. The installer defaults installed to
  `%LOCALAPPDATA%\OmniDictate`, launched, uninstalled, and removed the install
  directory.
- Gemma package policy is now explicit: the public baseline installer remains
  Whisper-only. Gemma dependencies, model weights, Transformers/Torch stacks,
  and GGUF assets must not be bundled into the default installer. Gemma can
  ship only as source/dev functionality or a separately named experimental
  package after its own live gates pass.
- Added release-candidate docs:
  `docs/release/RELEASE_CHECKLIST_3.0.0-whisper.md` and
  `docs/release/RELEASE_NOTES_DRAFT_3.0.0-whisper.md`. These documents define
  the next shippable artifact as a Whisper-only baseline and keep Gemma, GGUF,
  and alternative STT out of the default installer.
- Added `docs/ai/COMPLETION_AUDIT.md`, which maps the original objective to
  current evidence and keeps the goal open until physical mic phrase-match,
  E4B, real GGUF, and final release alignment are proven or explicitly moved
  out of scope.
- `git diff --check` passed after the release-candidate doc updates. Git
  reported existing CRLF normalization warnings for `.gitignore`,
  `core_logic.py`, `hotkey_listener.py`, and `main_gui.py`.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after the release-candidate doc updates. The first 120-second run
  timed out before producing a result, so the gate was rerun with a longer
  timeout and completed successfully in about 79 seconds.
- README installation/package wording was aligned with the verified
  Whisper-only baseline: the default installer includes the app runtime but
  does not bundle Gemma weights, GGUF files, alternative STT models, or smoke
  caches; Whisper loads on demand and Gemma download remains explicit.
- `git diff --check` passed after the README/audit/research updates, again
  with only existing CRLF normalization warnings for `.gitignore`,
  `core_logic.py`, `hotkey_listener.py`, and `main_gui.py`.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  again on 2026-07-05 after the README/audit/research updates. Visual context
  smoke emitted local virtual camera vendor logs but completed successfully.
- Added `tools\release_readiness_audit.py` and wired it into
  `tools\verify_local.ps1`. It checks required recovery docs, keeps known live
  gates marked open, validates README package policy wording, validates
  per-user installer defaults, validates the whisper-only PyInstaller policy,
  and inspects local Whisper-only artifacts when they exist.
- `.\venv\Scripts\python.exe tools\release_readiness_audit.py` passed.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  again on 2026-07-05 with the release-readiness audit included as a normal
  quick-gate step.
- Added `tools\gguf_server_probe.py` and
  `docs/evidence/gguf-real-server-runbook-2026-07-05.md` so the open GGUF
  real-server gate has a direct `/models` and `/chat/completions` diagnostic
  before the full `tools\gemma_smoke_test.py --runtime gguf-server` backend
  smoke.
- `.\venv\Scripts\python.exe tools\gguf_server_probe.py --url http://127.0.0.1:8080/v1 --timeout 3`
  failed cleanly because no local server was listening. This confirms the
  diagnostic path but does not close the real-server gate.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding the GGUF real-server probe compile step. The quick gate now
  compiles `tools\gguf_server_probe.py` but does not require a live GGUF
  server for normal non-interactive verification.
- `.\venv\Scripts\python.exe tools\release_readiness_audit.py` passed after
  the GGUF runbook/probe additions.
- `tools\microphone_capture_diagnostic.py` now supports `--input` to
  revalidate a saved WAV without reopening the physical microphone, plus
  `--report-json` for repeatable evidence.
- `.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --input smoke_test_assets\microphone\diagnostic-quiet-baseline.wav --allow-low-level --report-json smoke_test_assets\microphone\diagnostic-quiet-baseline-report.json`
  passed on the existing quiet baseline. This proves the saved-WAV evidence
  path, not the remaining spoken phrase gate.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after the saved-WAV microphone diagnostic update.
- `.\venv\Scripts\python.exe tools\release_readiness_audit.py` passed after
  the saved-WAV microphone diagnostic update.
- `powershell -ExecutionPolicy Bypass -File tools\verify_whisper.ps1 -Model large-v3-turbo`
  passed again on 2026-07-05: route `Whisper only`, latency `0.60s`, 8/8
  expected words.
- `powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1 -InstallerPath smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe -InstallDir "$env:LOCALAPPDATA\OmniDictate" -UseInstallerDefaults`
  passed again on 2026-07-05: installed to `%LOCALAPPDATA%\OmniDictate`,
  launched, uninstalled, and removed the installed payload.
- Added `docs/release/ARTIFACT_MANIFEST_3.0.0-whisper.md` with current local
  smoke artifact paths, sizes, SHA256 hashes, bundle size audit, screenshot
  dimensions, and latest release gate evidence.
- `.\venv\Scripts\python.exe tools\release_readiness_audit.py` passed after
  adding the artifact manifest and manifest-aware audit checks.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding the artifact manifest; the quick gate now verifies that release
  notes point to the manifest.
- Added `docs/release/PUBLISHING_RUNBOOK_3.0.0.md` and D011. Recommended
  public tag is `v3.0.0`; recommended public installer is
  `OmniDictate_Setup_v3.0.0.exe`; `3.0.0-whisper-release-smoke` remains a
  local evidence suffix only.
- `.\venv\Scripts\python.exe tools\release_readiness_audit.py` passed after
  adding the publishing runbook/versioning audit checks.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding the publishing runbook/versioning audit checks.
- Fixed `.gitignore` so only the root `/release/` artifact directory is
  ignored. The previous broad `release/` pattern hid `docs/release/`.
- `tools\release_readiness_audit.py` now fails if `docs/release` files are
  ignored or if forbidden local artifacts/model paths are staged.
- `git check-ignore -v docs\release\RELEASE_CHECKLIST_3.0.0-whisper.md`
  confirmed `docs/release` is visible to git.
- `tools\release_readiness_audit.py` now verifies that release notes state the
  package is Whisper-only and keep Gemma E4B, GGUF real server, alternative
  STT, and physical microphone phrase-match gates honest.
- `.\venv\Scripts\python.exe tools\release_readiness_audit.py` passed after
  adding the release-note honesty checks.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding the release-note honesty checks.
- Added `tools\gemma_model_preflight.py` and
  `docs/evidence/gemma-e4b-preflight-2026-07-05.md` to diagnose local E4B
  model/runtime readiness without loading or downloading weights by default.
- `.\venv\Scripts\python.exe tools\gemma_model_preflight.py --model google/gemma-4-E4B-it --report-json smoke_test_assets\gemma-e4b-preflight.json`
  passed as a preflight: Transformers `5.5.0`, `AutoModelForMultimodalLM`,
  Torch `2.6.0+cu126`, CUDA on RTX 3060 Laptop GPU. Local E4B weights were
  missing, so the live E4B gate remains open.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding the Gemma E4B preflight compile step.
- `.\venv\Scripts\python.exe tools\release_readiness_audit.py` passed after
  adding the Gemma E4B preflight docs/tooling.
- `tools\release_readiness_audit.py` now requires
  `docs/evidence/gemma-e4b-preflight-2026-07-05.md` and checks that it keeps
  E4B local weights missing/live gate open until real generation passes.
- `.\venv\Scripts\python.exe tools\release_readiness_audit.py` and
  `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  after adding the E4B preflight evidence assertions.
- Added `tools\open_gate_summary.py` and wired
  `tools\open_gate_summary.py --strict` into `tools\verify_local.ps1`. It
  prints the current external gates, evidence files, dependencies, and next
  commands while failing only if the docs stop admitting those gates.
- `tools\open_gate_summary.py` now reads
  `docs\release\RELEASE_SCOPE_DECISIONS_3.0.0.md` and prints each open gate's
  `Scope: pending` status. `tools\open_gate_summary_test.py` is wired into
  `tools\verify_local.ps1`, and the release status/GitHub preflight snapshots
  were refreshed with `release_scope_status` on each open gate payload.
- `tools\external_gate_orchestrator.py` also prints `Scope: pending` and writes
  `release_scope_status` into each `smoke_test_assets\external-gates-dry-run.json`
  gate payload. `tools\release_snapshot_freshness_audit.py` compares that
  field so stale scope decisions are caught in saved dry-run reports.
- Added `tools\release_decision_matrix_report.py`, a compact local report that
  combines final artifact readiness, saved GitHub preflight state, remaining
  release-scope gates, evidence paths, and next commands into
  `smoke_test_assets\packaging\release-decision-matrix.json`.
- Added `tools\external_gate_prerequisite_audit.py`, a non-interactive report
  that checks fixture files, expected gate reports, and local E4B safetensors
  without opening the microphone, loading Gemma, or contacting a GGUF server.
  It writes `smoke_test_assets\external-gate-prerequisites.json`, and the
  decision matrix now includes its missing-file/report fields plus each gate's
  closure report and closure-audit command.
- `tools\goal_completion_audit.py` now validates that saved decision matrix
  stays `blocked`, `publish_ready: false`, and aligned to the same three
  pending release-scope gates before it allows the goal-open audit to pass.
- `tools\release_readiness_audit.py` now treats the seven saved release reports
  as a canonical set and fails if they disappear or are no longer referenced
  from the coordination docs.
- Added `tools\external_gate_closure_audit.py`; it reads saved gate evidence
  through the same per-gate audit functions and reports `missing-evidence`,
  `evidence-failed`, or `eligible-for-proven` so scope decisions can be updated
  only after real passing reports exist.
- `.\venv\Scripts\python.exe tools\open_gate_summary.py --json --strict` and
  `.\venv\Scripts\python.exe tools\release_readiness_audit.py` passed after
  adding the open-gate summary tool.
- Refreshed `docs\research\STT_MODEL_RESEARCH_2026.md` against current primary
  model-card/docs sources for NVIDIA Nemotron 3.5 ASR, GLM-ASR-Nano,
  MOSS-Transcribe, and Microsoft VibeVoice-ASR. The release conclusion did not
  change: keep `faster-whisper`/`large-v3-turbo` as the default baseline,
  treat Parakeet/Nemotron/Moonshine as the next latency adapter lane, and keep
  heavier multilingual/long-form/multimodal ASR models out of the default
  installer until measured adapter spikes justify them.
- `tools\release_readiness_audit.py` now verifies that the STT research doc
  keeps this current model/release-policy boundary intact.
- `.\venv\Scripts\python.exe -m py_compile tools\release_readiness_audit.py`,
  `.\venv\Scripts\python.exe tools\release_readiness_audit.py`, and
  `.\venv\Scripts\python.exe tools\open_gate_summary.py --strict` passed after
  the research refresh.
- Added explicit alternative-STT promotion criteria to
  `docs\research\STT_MODEL_RESEARCH_2026.md`,
  `docs\specs\PRODUCT_SPEC.md`, and the R4 checklist: a candidate must match
  accuracy, either beat short-utterance latency by at least 20% or prove a
  named product win, preserve lazy import/package boundaries, record cache and
  Windows warning evidence, and end with a keep/defer/reject decision before
  visible UI or release promotion.
- `tools\release_readiness_audit.py` now protects those alternative-STT
  acceptance markers.
- Added `tools\stt_adapter_benchmark.py` for repeatable STT promotion
  evidence. It runs Whisper and an optional Transformers ASR candidate on the
  same fixture, records median latency and word-match ratio, and emits a
  decision such as `baseline-only`,
  `candidate-meets-latency-promotion-bar`, or
  `defer-candidate-no-measured-win`.
- `.\venv\Scripts\python.exe tools\stt_adapter_benchmark.py --whisper-model tiny --runs 1 --report-json smoke_test_assets\stt-benchmarks\baseline-tiny-smoke.json`
  passed: Whisper `tiny` loaded, matched 100% of expected words, reported
  `0.34s` latency, and wrote ignored JSON evidence.
- Repeated Moonshine benchmark passed:
  `.\venv\Scripts\python.exe tools\stt_adapter_benchmark.py --whisper-model large-v3-turbo --candidate-model UsefulSensors/moonshine-tiny --runs 3 --whisper-package-dir smoke_test_assets\packaging\dist-whisper\OmniDictate --check-import-boundary --check-command-routing --command-check "comma=," --command-check "period=." --report-json smoke_test_assets\stt-benchmarks\moonshine-tiny-vs-large-v3-turbo.json --keep-audio`.
  Whisper `large-v3-turbo` median latency was `0.47s`, Moonshine-tiny median
  latency was `0.31s`, both had 100% word match, candidate cache footprint was
  12 files / 110,376,063 bytes, Whisper-only package-boundary and baseline
  import-boundary checks passed, command routing passed for spoken `comma` and
  `period`, and the decision was
  `candidate-meets-latency-promotion-bar`. The JSON report says
  `promotion_ready: false` and lists blockers for physical microphone
  snippets and release UI approval. Hugging Face warned about unauthenticated
  Hub requests.
- Moonshine-tiny remains experimental despite the synthetic latency win. It
  still needs physical microphone snippets, command/punctuation behavior, and
  package/import/cache boundary evidence before visible UI or release
  promotion.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1`,
  `git diff --check`, `git diff --cached --name-only`, and
  `.\venv\Scripts\python.exe tools\open_gate_summary.py --strict` were rerun
  on 2026-07-05 after the `--audio-source` benchmark/reporting updates. The
  quick gate passed; `git diff --check` reported only the known CRLF
  normalization warnings for `.gitignore`, `core_logic.py`,
  `hotkey_listener.py`, and `main_gui.py`; no files were staged. The open-gate
  list remained the same four external gates at that point.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  again on 2026-07-05 after the microphone evidence doc was updated with the
  user's repeated-mismatch/Ctrl+C run details.
- `tools\microphone_capture_diagnostic.py` now supports `--prompt` and
  `--countdown` for guided human speech capture, and its JSON report records
  `prompted` plus the expected phrase. A short low-level prompt-path smoke
  opened the Realtek microphone, printed the expected phrase, recorded, and
  wrote `prompted: true` evidence. `powershell -ExecutionPolicy Bypass -File
  tools\verify_local.ps1` passed afterward with the guided mic command in the
  open-gate summary.
- `tools\live_microphone_smoke.py` now supports `--countdown`,
  `--max-transcripts`, `--device`, and `--report-json` for guided manual
  VAD/PTT evidence. Failed and interrupted runs can write reports too,
  including all worker transcripts, selected device, and `failed_mode`.
  `tools\open_gate_summary.py` now prints every command in each open-gate
  sequence, not just the first one. `powershell
  -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on 2026-07-05
  with the expanded open-gate output and guided live-loop command.
- Added `tools\microphone_evidence_tooling_test.py` and wired it into
  `tools\verify_local.ps1`. It validates live-loop JSON report shape,
  failed-report mode/transcript evidence, manual prompt wording, the three-step
  physical microphone command sequence, and `Next`/`Then` open-gate output
  without opening the microphone.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after adding `tools\microphone_evidence_tooling_test.py` to the
  quick gate.
- Added `tools\artifact_manifest_audit.py` and wired it into
  `tools\verify_local.ps1`. It recomputes the artifact manifest's listed local
  file sizes, SHA256 hashes, and packaged screenshot dimensions. The current
  smoke artifact manifest passed this byte/hash/dimension audit on 2026-07-05.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 with `tools\artifact_manifest_audit.py` included after the
  release-readiness audit.
- Added `tools\final_release_preflight.py`. It checks local static
  prerequisites for the final `v3.0.0` public build and prints the final
  PyInstaller, Inno Setup, installer smoke, package-size audit, and hash
  commands without building or publishing. It passed on 2026-07-05 and is now
  the first step in `docs\release\PUBLISHING_RUNBOOK_3.0.0.md`.
- `.\venv\Scripts\python.exe tools\final_release_preflight.py --json`,
  `.\venv\Scripts\python.exe tools\release_readiness_audit.py`,
  `.\venv\Scripts\python.exe tools\open_gate_summary.py --strict`, and
  `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after adding the final release preflight. The open-gate summary
  now uses the final `dist-whisper-final` and `installer-whisper-final` paths.
- Added `tools\final_release_tooling_test.py` and wired it into
  `tools\verify_local.ps1`. It protects final public release command shape:
  public installer name, final artifact directories, no smoke suffix, JSON
  preflight payload, and open-gate/preflight path alignment.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after adding `tools\final_release_tooling_test.py` to the quick
  gate.
- Added `tools\final_release_gate_audit.py` and
  `tools\final_release_gate_audit_test.py`, then wired them into
  `tools\verify_local.ps1`. Future final-public-release closure now requires
  `final-release-preflight.json`, a matching final
  `dist-whisper-final\OmniDictate` bundle, the exact
  `OmniDictate_Setup_v3.0.0.exe` installer name, a non-smoke artifact path,
  size checks, installer SHA256 recording, and
  `final-release-gate-report.json`.
- Added `tools\final_public_release_gate.py` and
  `tools\final_public_release_gate_test.py`, then wired them into
  `tools\verify_local.ps1`. The final public release artifact gate now has one
  command that internally runs preflight, Whisper-only PyInstaller, Inno Setup,
  installer smoke, size/hash checks, and final artifact audit while writing
  `smoke_test_assets\packaging\final-public-release-gate-report.json`.
- `.\venv\Scripts\python.exe tools\final_public_release_gate_test.py`,
  `.\venv\Scripts\python.exe tools\final_public_release_gate.py --dry-run --report-json smoke_test_assets\packaging\final-public-release-gate-dry-run.json`,
  `.\venv\Scripts\python.exe -m py_compile tools\final_public_release_gate.py`,
  `.\venv\Scripts\python.exe tools\final_release_tooling_test.py`,
  `.\venv\Scripts\python.exe tools\release_readiness_audit.py`,
  `.\venv\Scripts\python.exe tools\open_gate_summary.py --strict`,
  `.\venv\Scripts\python.exe tools\goal_completion_audit.py`, and
  `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after adding the one-command final public release gate runner.
- `.\venv\Scripts\python.exe tools\final_release_gate_audit_test.py`,
  `.\venv\Scripts\python.exe tools\final_release_tooling_test.py`,
  `.\venv\Scripts\python.exe -m py_compile tools\final_release_preflight.py tools\final_release_gate_audit.py`,
  `.\venv\Scripts\python.exe tools\release_readiness_audit.py`,
  `.\venv\Scripts\python.exe tools\open_gate_summary.py --strict`,
  `.\venv\Scripts\python.exe tools\goal_completion_audit.py`, and
  `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after adding the final release artifact audit gate.
- Added `tools\external_gate_orchestrator.py` and
  `tools\external_gate_orchestrator_test.py`, then wired them into
  `tools\verify_local.ps1`. The orchestrator dry-runs the remaining
  external gate runners by default and writes an aggregate report; `--execute`
  is required before it opens devices, loads E4B, contacts a GGUF server, or
  builds final artifacts.
- `tools\gguf_server_probe.py` now supports `--report-json` for durable real
  server probe evidence. Added `tools\gguf_server_probe_test.py`, which starts
  a mock OpenAI-compatible server, verifies image+text and text-only probe
  paths, validates JSON report shape, and checks that raw audio keys are not
  sent. This test passed on 2026-07-05 and is wired into `tools\verify_local.ps1`.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after adding `tools\gguf_server_probe_test.py` to the quick gate.
- `tools\gemma_smoke_test.py` now supports `--report-json`.
  `tools\gguf_gate_report_audit.py` and `tools\gguf_gate_report_audit_test.py`
  were added for the real-server gate. A future GGUF claim now needs a named
  real server implementation plus both structured reports: direct probe and
  full `--runtime gguf-server` backend smoke. Mock labels, URL mismatches,
  non-GGUF routes, missing visual context, and transcript mismatches are
  rejected by the audit.
- Added `tools\gguf_real_server_gate.py` and
  `tools\gguf_real_server_gate_test.py`, then wired them into
  `tools\verify_local.ps1`. The real GGUF server gate now has one command that
  internally runs the direct probe, full `--runtime gguf-server` backend smoke,
  and report audit while writing
  `smoke_test_assets\gguf\real-server-gate-report.json`.
- `.\venv\Scripts\python.exe tools\gguf_real_server_gate_test.py`,
  `.\venv\Scripts\python.exe tools\gguf_real_server_gate.py --server-implementation "LM Studio" --dry-run --report-json smoke_test_assets\gguf\real-server-gate-dry-run.json`,
  `.\venv\Scripts\python.exe -m py_compile tools\gguf_real_server_gate.py`,
  `.\venv\Scripts\python.exe tools\release_readiness_audit.py`, and
  `.\venv\Scripts\python.exe tools\open_gate_summary.py --strict` passed on
  2026-07-05 after adding the one-command GGUF real-server gate runner.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` also
  passed on 2026-07-05 with the GGUF real-server gate runner tests and compile
  step included.
- Added `tools\gemma_model_preflight_test.py` and wired it into
  `tools\verify_local.ps1`. It uses a temporary empty model store and mocked
  runtime summaries to prove `--require-local` fails and writes a report when
  E4B weights are missing, without downloading or loading E4B.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after adding `tools\gemma_model_preflight_test.py` to the quick
  gate.
- `tools\gemma_smoke_test.py` now supports `--report-json`, and
  `tools\gemma_e4b_gate_report_audit.py` / `_test.py` were added for the E4B
  live gate. Future E4B closure now requires a preflight report proving local
  safetensors plus a passing hybrid `Whisper -> Gemma` E4B smoke report with
  visual context and matching text.
- Added `tools\gemma_e4b_gate.py` and `tools\gemma_e4b_gate_test.py`, then
  wired them into `tools\verify_local.ps1`. The E4B live gate now has one
  command that internally runs local-weight preflight, hybrid live smoke, and
  report audit while writing `smoke_test_assets\gemma-e4b-gate-report.json`.
- `.\venv\Scripts\python.exe tools\gemma_e4b_gate_test.py`,
  `.\venv\Scripts\python.exe tools\gemma_e4b_gate.py --dry-run --report-json smoke_test_assets\gemma-e4b-gate-dry-run.json`,
  `.\venv\Scripts\python.exe -m py_compile tools\gemma_e4b_gate.py`,
  `.\venv\Scripts\python.exe tools\release_readiness_audit.py`,
  `.\venv\Scripts\python.exe tools\open_gate_summary.py --strict`, and
  `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after adding the one-command E4B gate runner.
- Added `tools\goal_completion_audit.py` and wired it into
  `tools\verify_local.ps1`. It verifies that `docs\ai\COMPLETION_AUDIT.md`
  still maps the original objective and agrees with
  `tools\open_gate_summary.py` while the external gates remain open.
- Added `tools\microphone_gate_report_audit.py` and wired its test/compile
  checks into `tools\verify_local.ps1`. It validates future physical mic
  evidence JSON: prompted capture, healthy levels, matching saved-WAV
  transcript, passing VAD and PTT loop reports, no worker errors. The physical
  mic gate should not be closed unless this validator passes.
- Added `tools\physical_microphone_gate.py` and
  `tools\physical_microphone_gate_test.py`, plus
  `tools\physical_microphone_run_card.py`, then wired them into
  `tools\verify_local.ps1`. The physical microphone gate now has one guided
  command that internally runs prompted capture, saved-WAV revalidation,
  manual VAD/PTT live-loop evidence, and the report audit while writing
  `smoke_test_assets\microphone\physical-gate-report.json`. Its dry-run report
  also writes structured `manual_prompt` metadata so the saved JSON carries the
  phrase, selected device, timing, required modes, and pass rule; the run-card
  tool prints that metadata as terminal-ready human instructions. If `--device`
  is supplied, the same sounddevice input is used for prompted capture and the
  live VAD/PTT loop.
- `tools\physical_microphone_gate.py --reuse-capture` now supports retrying
  only the live VAD/PTT loop and final audit after a prompted saved-WAV capture
  and capture report already exist. It fails before opening the microphone if
  either reuse prerequisite is missing.
- `tools\microphone_capture_diagnostic.py --list-devices` now lists
  input-capable PortAudio devices and writes
  `smoke_test_assets\microphone\audio-device-inventory.json` without recording
  audio. Use it before the physical mic gate when the default input is
  ambiguous.
- `tools\gemma_e4b_gate.py` and `tools\gguf_real_server_gate.py` now validate
  local audio/image fixtures before attempting E4B load/generation or GGUF
  server contact. Missing fixtures write failed reports and keep
  `results: []`.
- `tools\release_scope_decision_audit.py` now requires future `scoped-out`
  rows to include dated `User authorized ... on YYYY-MM-DD` text and a dated
  `Updated ... on YYYY-MM-DD` release-note/checklist marker; vague approval
  wording remains a blocker.
- `tools\open_gate_summary.py` and `tools\release_status_report.py` now use
  `smoke_test_assets\microphone\audio-device-inventory.json` to include the
  recommended numeric `--device` argument in the physical mic command when an
  inventory recommendation exists.
- `.\venv\Scripts\python.exe tools\physical_microphone_gate_test.py`,
  `.\venv\Scripts\python.exe tools\microphone_evidence_tooling_test.py`,
  `.\venv\Scripts\python.exe tools\physical_microphone_gate.py --dry-run --report-json smoke_test_assets\microphone\physical-gate-dry-run.json`,
  `.\venv\Scripts\python.exe tools\release_readiness_audit.py`,
  `.\venv\Scripts\python.exe tools\open_gate_summary.py --strict`,
  `.\venv\Scripts\python.exe tools\goal_completion_audit.py`, and
  `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after adding the one-command physical microphone gate runner.
- Added `tools\external_gate_orchestrator.py` and
  `tools\external_gate_orchestrator_test.py`, then wired them into
  `tools\verify_local.ps1`. The orchestrator dry-runs the three remaining
  external gate runners by default and requires `--execute` before touching
  physical microphone capture, E4B generation, or a real GGUF server. It now
  uses the saved audio-device inventory's recommended numeric microphone by
  default and accepts `--microphone-device <numeric sounddevice input index>`
  as an explicit override for `tools\physical_microphone_gate.py`; use a
  device display name only when the inventory shows it is unique.
- `.\venv\Scripts\python.exe tools\external_gate_orchestrator_test.py`,
  `.\venv\Scripts\python.exe tools\external_gate_orchestrator.py --report-json smoke_test_assets\external-gates-dry-run.json`,
  `.\venv\Scripts\python.exe -m py_compile tools\external_gate_orchestrator.py`,
  `.\venv\Scripts\python.exe tools\release_readiness_audit.py`,
  `.\venv\Scripts\python.exe tools\open_gate_summary.py --strict`,
  `.\venv\Scripts\python.exe tools\goal_completion_audit.py`, and
  `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after adding the aggregate external-gate dry-run.
- The real final public artifact gate passed on 2026-07-05 after fixing
  repeatability in `tools\final_public_release_gate.py`: the runner now passes
  a concrete `%LOCALAPPDATA%\OmniDictate` path to `installer_smoke.ps1`, opts
  into `-AllowRemoveExisting`, and uses `tools\file_sha256.py` instead of a
  shell-dependent `Get-FileHash` step. It wrote
  `smoke_test_assets\packaging\final-public-release-gate-report.json` with
  `status: passed` and `smoke_test_assets\packaging\final-release-gate-report.json`
  with `status: ready`.
- Final artifact evidence after the 2026-07-06 rebuild: bundle
  `smoke_test_assets\packaging\dist-whisper-final\OmniDictate` is 322,225,944
  bytes; installer
  `smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe`
  is 324,505,897 bytes with SHA256
  `3DD9CF5CD1E172D41208DDD3BDC3380A5A18BA1DDBA4BD5F3CE7FDEA2CEA10A5`.
- Rebuilt final public artifact after the packaged `av` failure. The
  Whisper-only package now includes PyAV and Hugging Face Hub, runs
  `tools\packaged_app_smoke.py` before installer smoke, and the packaged
  runtime self-test passed `av_import`, `faster_whisper_import`,
  runtime-settings sanitization, and `large-v3-turbo` load.
- Rebuilt the final public artifact again after the installed app exposed
  Gemma/GGUF controls and the Whisper path appeared CPU-bound. The
  Whisper-only PyInstaller build now includes `pyi_runtime_whisper_only.py`,
  `tools\packaged_app_smoke.py` no longer injects `--package-profile`, and the
  installed runtime self-test now proves `package_profile: whisper-only` plus
  `Whisper model 'large-v3-turbo' loaded on cuda (float16)`.
- Added `tools\publication_blocker_audit.py` and
  `tools\publication_blocker_audit_test.py`, then wired them into
  `tools\verify_local.ps1`. The audit requires the final public artifact
  reports to be passed/ready and reports publication as `blocked` while the
  current open-gate set remains physical microphone phrase-match VAD/PTT,
  Gemma E4B live generation, and real GGUF server.
- Refreshed `docs\research\STT_MODEL_RESEARCH_2026.md` against live primary
  ASR sources and added D013. Future ASR candidates are now sorted into
  low-latency dictation, multilingual/dialect, realtime/heavy runtime, and
  rich-transcript lanes; rich-transcript models such as IBM Granite Speech are
  not default dictation replacements unless product scope changes.
- Strengthened `docs\ai\COMPLETION_AUDIT.md` with an Objective Evidence
  Matrix. Each original objective requirement now has a proof standard,
  authoritative evidence, current decision, and closure condition; adjacent
  green tests are explicitly not enough to mark the full goal complete.
- Added `docs\implementation-plans-and-checklists\phase-4-release-execution.md`
  as the next-phase release execution checklist. It sequences physical
  microphone, Gemma E4B, real GGUF, and final publication decisions without
  treating the existing final artifact as publish-ready by itself.
- Added `tools\release_status_report.py` and
  `tools\release_status_report_test.py`. The reporter aggregates final
  artifact status, publication blocker state, open gates, aggregate external
  gate dry-run commands, inventory-backed microphone selection,
  selected-microphone dry-run guidance, run-card preparation commands, and
  next commands in one JSON/text status snapshot.
- `tools\publication_blocker_audit.py` and
  `tools\release_status_report.py` now write schema-versioned,
  `generated_at_utc` stamped JSON snapshots. The blocker report also includes
  `open_gate_details` with each remaining gate's evidence path and next
  commands, including the inventory-backed physical microphone `--device`
  argument, so future agents can inspect a single report without reconstructing
  the gate list from docs.
- Added `tools\release_snapshot_freshness_audit.py` and
  `tools\release_snapshot_freshness_audit_test.py`, then wired them into
  `tools\verify_local.ps1`. The audit recomputes the publication blocker and
  release status reports, plus the GitHub release preflight report, ignores
  only `generated_at_utc`, and fails if saved JSON snapshots drift from
  current gate lists, artifact state, installer hashes, remote tag state,
  GitHub preflight scope blockers, external-gate dry-run command shapes, or
  command shapes.
- Added `docs\release\RELEASE_SCOPE_DECISIONS_3.0.0.md`,
  `tools\release_scope_decision_audit.py`, and
  `tools\release_scope_decision_audit_test.py`, then wired them into
  `tools\verify_local.ps1`. All three remaining release-scope gates are
  currently `pending`; a future `scoped-out` decision requires explicit user
  authorization plus a release note/checklist update marker.
- `tools\publication_blocker_audit.py` now consumes
  `RELEASE_SCOPE_DECISIONS_3.0.0.md`. Current `pending` rows keep the same
  three publication blockers; future `proven` or authorized `scoped-out`
  rows are the machine-readable path for removing a gate from the blocker
  report.
- Added `tools\github_release_preflight.py` and
  `tools\github_release_preflight_test.py`, then wired them into
  `tools\verify_local.ps1`. The preflight checks the GitHub remote, confirms
  `v3.0.0` is not already present, confirms `v2.0.2` is visible, verifies the
  final installer path, and refuses to mark the release publish-ready while the
  local release status is `blocked`.
- `tools\github_release_preflight.py` now writes schema-versioned,
  `generated_at_utc` stamped JSON and exposes `scope_gate_statuses` plus
  `pending_release_scope_gates` at the top level. The saved preflight report
  was refreshed and currently shows all three release-scope gates as pending.
- Added `tools\handoff_next_action_audit.py` and
  `tools\handoff_next_action_audit_test.py`, then wired them into
  `tools\verify_local.ps1`. The audit keeps the `Exact Next Action` section
  aligned with the Phase 4 checklist, GitHub release preflight, release status
  report, publication blocker report, and three remaining gate commands.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-05 after updating the final artifact evidence and reducing the open
  external gate list to three.
- `tools\release_readiness_audit.py` now rejects current-sounding stale docs
  that claim four current open gates or an unrebuilt final public artifact.
  `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  again on 2026-07-05 after that stale-doc guard.
- `docs\release\RELEASE_CHECKLIST_3.0.0-whisper.md` now leads current artifact
  evidence with the final public installer size/SHA256 instead of the earlier
  smoke artifact. `tools\release_readiness_audit.py`,
  `tools\artifact_manifest_audit.py`, `tools\open_gate_summary.py --strict`,
  and `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed
  on 2026-07-05 after that checklist alignment.
- `preload_model_on_launch` now starts a fail-soft background warm-up for the
  selected built-in Gemma backend on app launch without opening the microphone.
  `tools\preload_model_worker_test.py` covers success/failure signal behavior
  and backend unload cleanup, and `tools\ui_smoke_test.py` disables preload so
  saved local settings cannot make normal UI smoke load real model files.
- The typing loop now discards pending keystrokes when OmniDictate itself has
  focus instead of holding old transcripts and replaying them into the next
  foreground app. The transcript still appears in OmniDictate's display.
  `tools\worker_behavior_test.py` covers both discard-on-own-window and normal
  typing into another target.
- The public Whisper-only Settings page has more row padding and stronger base
  font weight so row borders do not cut through text. Visible Whisper-only
  Settings copy no longer mentions Gemma/GGUF-only paths. Native screenshot
  evidence was refreshed at
  `smoke_test_assets\ui\settings-whisper-public-font-padding-2026-07-06.png`.
- README now explains why the public installer is about 300 MB instead of the
  earlier multi-GB development bundle: it bundles the app runtime, Python, Qt,
  PyAV/FFmpeg, and CTranslate2, but not Whisper model weights, CUDA/cuDNN DLLs,
  Torch/Transformers, Gemma/GGUF stacks, alternative STT models, or test caches.
  A fresh machine needs first-run model download or a pre-populated Hugging
  Face cache, microphone permission, and NVIDIA driver/CUDA/cuDNN runtime
  availability for GPU acceleration.
- README was rewritten again on 2026-07-06 to remove stale v2.0.2-style
  feature framing and internal release-policy/model-experiment wording from
  the public path. It now gives end users a simple install, update, settings,
  and troubleshooting flow.
- Added `docs\final-review-2026-07-06.md` with the package sufficiency
  verdict, README review, threading/lifecycle review, and update strategy.
- Added D014: do not add a full auto-updater to `v3.0.0`; use manual GitHub
  Releases updates plus an explicit Settings `Check for Updates` action that
  makes no startup network call, compares the latest GitHub tag, and opens the
  release page when a newer version exists.
- Added `docs\github-issues-review-2026-07-06.md`. Implemented #27
  Transcribe Only/no keyboard simulation, #26 Czech language selection, and
  #18 minimum PTT hold. Deferred #22 global start/stop hotkey, #23 GPU/cuDNN
  fallback, #21 model research, and full #20 memory-leak closure pending
  longer soak evidence.
- `app_updates.py` plus `tools\app_updates_test.py` cover non-network update
  version comparison; the UI runs the real GitHub latest-release check only
  when the user clicks Settings -> Check for Updates.
- Start/Stop buttons now use explicit `state` properties: Start is primary
  only while idle, Stop is primary only while dictation is running, and Stop
  uses a neutral busy state while shutdown is pending. `tools\ui_contrast_static_test.py`
  guards those selectors and blocks the old always-red Stop styling, while
  `tools\ui_transport_state_test.py` verifies the runtime state transitions.
- Stop handling is now asynchronous for normal UI use: `stop_dictation()` queues
  `DictationWorker.stop_processing()` instead of using `BlockingQueuedConnection`;
  the worker emits `stop_completed`, the thread quits from that signal, and
  queued transcription requests are dropped on stop. `tools\threading_lifecycle_test.py`
  guards this path.
- `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1` passed on
  2026-07-06 after the typing-history discard, Settings readability, visible
  Whisper-only UI copy, UI smoke assertion, and README package-dependency
  updates.

## Not Yet Verified

- Live Gemma E4B model load and generation with weights remains unverified and
  is scoped out of the public Whisper-only `v3.0.0` release by user
  authorization on 2026-07-05.
- GGUF server route against a real llama.cpp, LM Studio, or other local
  endpoint remains unverified and is scoped out of the public Whisper-only
  `v3.0.0` release by user authorization on 2026-07-05. The contract is
  covered by a mock server test only.
- GitHub publication itself is not performed. Local preflight is ready:
  the final public artifact is rebuilt and audited, physical microphone is
  proven for release scope, Gemma/GGUF are scoped out, and `v3.0.0` does not
  exist on the remote.

## Exact Next Action

Do final human review of the release notes/runbook, then publish `v3.0.0`
using `docs\release\PUBLISHING_RUNBOOK_3.0.0.md` if the user explicitly asks
to tag/release. Keep
`docs\implementation-plans-and-checklists\phase-4-release-execution.md` as the
release execution checklist. Before publication, rerun the stop/go reports:

```powershell
.\venv\Scripts\python.exe tools\publication_blocker_audit.py --report-json smoke_test_assets\packaging\publication-blockers.json
```

```powershell
.\venv\Scripts\python.exe tools\release_status_report.py --report-json smoke_test_assets\packaging\release-status-report.json
```

```powershell
.\venv\Scripts\python.exe tools\external_gate_prerequisite_audit.py --report-json smoke_test_assets\external-gate-prerequisites.json
```

```powershell
.\venv\Scripts\python.exe tools\external_gate_closure_audit.py --report-json smoke_test_assets\external-gate-closure-audit.json
```

```powershell
.\venv\Scripts\python.exe tools\release_decision_matrix_report.py --report-json smoke_test_assets\packaging\release-decision-matrix.json
```

```powershell
.\venv\Scripts\python.exe tools\release_snapshot_freshness_audit.py
```

```powershell
.\venv\Scripts\python.exe tools\release_scope_decision_audit.py
```

```powershell
.\venv\Scripts\python.exe tools\github_release_preflight.py --report-json smoke_test_assets\packaging\github-release-preflight.json
```

```powershell
.\venv\Scripts\python.exe tools\external_gate_orchestrator.py --report-json smoke_test_assets\external-gates-dry-run.json
```

For future technical gate visibility, rerun:

```powershell
.\venv\Scripts\python.exe tools\open_gate_summary.py --strict
```

The physical microphone release-scope gate is already proven, but this is the
repeat command if it ever needs revalidation:

```powershell
.\venv\Scripts\python.exe tools\physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --report-json smoke_test_assets\microphone\physical-gate-report.json
```

After any code or docs change, rerun:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

The quick gate now includes `tools\release_readiness_audit.py`, so it will
fail if release docs or README wording silently promote open Gemma/GGUF/mic
gates.

For future experimental R2 work, run
`.\venv\Scripts\python.exe tools\gemma_e4b_gate.py --model google/gemma-4-E4B-it --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gemma-e4b-gate-report.json`;
E4B is scoped out of this release until local E4B weights are available and
that gate passes. For future experimental R3 work, run
`.\venv\Scripts\python.exe tools\gguf_real_server_gate.py --url http://127.0.0.1:8080/v1 --server-implementation "LM Studio" --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gguf\real-server-gate-report.json`
against a named real local server before claiming GGUF readiness; GGUF is
scoped out of this release until that gate passes. For R5, use
`docs/release/RELEASE_CHECKLIST_3.0.0-whisper.md` as the tagging checklist and
`docs/release\PUBLISHING_RUNBOOK_3.0.0.md` for the final publishing commands
after the physical microphone release-scope gate passes or is explicitly scoped
out.
