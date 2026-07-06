# Phase 3 Gemma Recovery Plan

Goal: recover the local Gemma-era work without regressing the `v2.0.2`
Whisper product.

## R0 - Recovery Documentation And Gates

Status: complete

- [x] Confirm repo baseline is `v2.0.2`.
- [x] Compare local changes to baseline.
- [x] Verify compile and route smoke tests.
- [x] Verify Gemma processor compatibility without loading weights.
- [x] Add project-specific agent docs.
- [x] Add quick verification runner.
- [x] Ignore local model caches.
- [x] Run quick verification runner successfully.

Acceptance: `tools\verify_local.ps1` passes and docs name the next action.

## R1 - Whisper Parity Gate

Status: in progress

- [x] Run quick gate on a clean local environment.
- [x] Add or collect a small known WAV fixture with expected text.
- [x] Prove `WhisperBackend` transcribes the fixture.
- [x] Prove VAD and PTT still queue audio correctly in headless worker tests.
- [x] Prove punctuation commands and filter words match `v2.0.2` in headless
  worker tests.
- [x] Prove the app does not type into its own window in headless worker tests.
- [x] Prove live Whisper transcription with the release/default
  `large-v3-turbo` model.
- [x] Prove live Notepad typing on Windows through the worker typing thread.
- [x] Prove synthetic VAD -> Whisper -> routing -> Notepad typing with
  `large-v3-turbo`.
- [x] Prove global PTT and Ctrl+1/2/3 hotkey events reach the listener.
- [x] Prove the physical microphone can open after permission is granted and
  that VAD can capture, queue, and transcribe at least one utterance.
- [x] Add a saved-WAV microphone diagnostic for separating device audio levels
  from VAD/PTT loop behavior.
- [x] Add saved-WAV revalidation and JSON report output so a spoken physical
  capture can be checked repeatedly without reopening the microphone.
- [ ] Prove physical microphone phrase-match VAD/PTT capture. The latest VAD
  run transcribed `We're open to the world.` with `tiny` instead of the
  expected phrase, and PTT was not reached; see
  `docs/evidence/live-microphone-audio-device-2026-07-04.md`.
- [x] Update README to mark Gemma as experimental until gates pass.

Acceptance: Whisper-only behavior is at least as reliable as `v2.0.2`, and no
Gemma dependency is required for default dictation.

## R2 - Transformers Gemma Gate

Status: in progress

- [x] Confirm official Gemma 4 E2B model load API against installed
  `transformers`.
- [x] Run E2B hybrid mode on a short audio fixture.
- [x] Run E2B context mode with one image fixture.
- [x] Run E2B native audio mode on a short audio fixture.
- [x] Record latency, device map, warnings, and failure modes for E2B.
- [x] Mark E4B as unverified in the UI until live weights are tested.
- [x] Add E4B model/runtime preflight tooling and runbook.
- [ ] Test or explicitly defer E4B live weights.
- [ ] Disable or hide any mode that fails repeatably.

Acceptance: each enabled Transformers Gemma route has a live, repeatable smoke
test and honest UI wording.

## R3 - GGUF Server Gate

Status: in progress

- [x] Define supported local server contract: `/models` and
  `/chat/completions`.
- [x] Verify contract against a mock OpenAI-compatible server.
- [x] Confirm image payload format works in the contract test.
- [x] Confirm raw audio is not sent to the server in the contract test.
- [x] Add a real-server probe/runbook so server setup can be diagnosed before
  the full backend smoke.
- [ ] Test against one real server implementation.
- [x] Document startup/probe instructions for candidate OpenAI-compatible
  local servers. A named selected server still needs a passing live smoke
  before GGUF readiness can be claimed.

Acceptance: GGUF server mode works with a named server and reports useful
errors when the server is unavailable.

## R4 - Alternative STT Adapter Spike

Status: complete

- [x] Build a minimal adapter interface for one non-Whisper ASR candidate.
- [x] Spike Parakeet unified or Moonshine first. Decision: Moonshine-tiny
  first because the local environment has Transformers/Torch but not NeMo.
- [x] Measure latency, quality, package size, and install friction.
- [x] Compare against `large-v3-turbo` on the same fixture style.
- [x] Decide whether to keep, defer, or reject the adapter. Decision: keep the
  optional adapter and live smoke for experiments, but do not promote it to the
  default UI or release package.
- [x] Define promotion criteria for future STT candidates: accuracy parity,
  at least 20% better short-utterance latency or a named product win,
  import/package isolation, cache footprint evidence, and a recorded
  keep/defer/reject decision.
- [x] Refresh the 2026 open-source ASR shortlist against live primary sources
  and sort candidates into named next-phase lanes: low-latency dictation,
  multilingual/dialect dictation, realtime/heavy runtime, and rich transcript.

Acceptance: a model is added only if it beats Whisper on a named product
metric without breaking packaging.

## R5 - Packaging And Release Candidate

Status: in progress

- [x] PyInstaller build passes in an isolated local output directory.
- [x] Packaged `OmniDictate.exe` launch smoke passes.
- [x] Inno split no-compression installer compile passes with disk spanning.
- [x] Produce a practical release-size Whisper-only packaging profile while
  keeping Gemma-heavy dependencies optional/experimental.
- [x] Compile a single-file Whisper-only smoke installer. The current output is
  236,259,929 bytes.
- [x] Per-user Whisper-only installer install/launch/uninstall smoke passes.
- [x] Add reusable installer smoke script.
- [x] Decide whether the public release installer should be per-user or
  admin/Program Files, then run that final release-path smoke. Decision:
  per-user is the default release path; admin/Program Files remains an
  explicit override.
- [x] Define the release policy for Gemma dependencies: optional post-install
  download, separate experimental package, or full bundle with a size warning.
  Decision: do not bundle Gemma in the baseline installer; ship only
  Whisper-only by default, with Gemma limited to source/dev or a separately
  named experimental package after its own gates pass.
- [x] Add a repeatable release-readiness audit so baseline package, README,
  installer, and open-gate claims stay aligned.
- [ ] README, screenshots, installer version, and release notes match verified
  features.
- [x] Record current smoke artifact names, sizes, checksums, screenshot
  dimensions, and current release gate evidence in
  `docs/release/ARTIFACT_MANIFEST_3.0.0-whisper.md`.
- [x] Document final public version/tag recommendation and rebuild commands in
  `docs/release/PUBLISHING_RUNBOOK_3.0.0.md`.
- [x] Create release checklist evidence before tagging:
  `docs/release/RELEASE_CHECKLIST_3.0.0-whisper.md`.

Acceptance: release artifacts are built from a clean, documented, gate-green
state and can be installed, launched, and removed without bundling local model
caches.

## R6 - Visual Context And UI QA

Status: complete

- [x] Verify generated image attachment.
- [x] Verify generated video-frame sampling.
- [x] Verify active-window screen capture returns or fails softly.
- [x] Verify full-screen capture returns or fails softly.
- [x] Verify webcam capture returns or fails softly.
- [x] Add visual context smoke to the quick gate.
- [x] Capture a native Windows screenshot of the main dictation view with
  readable text.
- [x] Capture settings page variants with native Windows screenshots.
- [x] Capture packaged app screenshots from the installed Whisper-only build.

Acceptance: visual-context inputs fail softly when unavailable, work when local
fixtures/devices are available, and primary UI screens render readable text on
the native Windows platform.
