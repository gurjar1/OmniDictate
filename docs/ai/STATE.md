# OmniDictate State

## Baseline Product

`v2.0.2` is the last successful release. It shipped a Windows PySide6 GUI for
local dictation with `faster-whisper`, VAD/PTT, spoken punctuation, filter
phrases, persistent settings, and direct typing into the active application.

## Local Architecture

The local branch changes the app from a single Whisper worker into a routed
transcription system:

- `app_settings.py`: typed settings facade over `QSettings`.
- `core_logic.py`: audio capture, VAD/PTT, request queue, inference queue,
  typing queue, backend dispatch. It now has small test seams for the
  foreground-window guard and pending-text typing path.
- `engines/base.py`: common request/result dataclasses and prompt modes.
- `engines/whisper_backend.py`: extracted faster-whisper path.
- `engines/gemma4_backend.py`: Transformers Gemma 4 path with native or
  hybrid audio.
- `engines/gemma_gguf_backend.py`: Whisper draft plus OpenAI-compatible local
  server refinement.
- `engines/context_capture.py`: screen, webcam, image, and sampled video
  context.
- `engines/prompt_modes.py`: pure, context, and reasoning prompts.
- `main_gui.py`: expanded settings UI, prompt modes, context attachment, and
  download controls.
- `hotkey_listener.py`: serialized hotkey storage plus Ctrl+1/2/3 mode switch.

## Runtime Routes

1. `faster-whisper`: default and release baseline. Audio -> text.
2. `gemma-4` hybrid: Whisper draft -> Gemma refinement when context/reasoning
   needs it. Pure mode short-circuits back to Whisper-only.
3. `gemma-4` native audio: audio/image/video -> Gemma. Experimental.
4. `gemma-gguf-server`: Whisper draft -> local OpenAI-compatible server with
  optional image payload. It does not send raw audio to the server.
5. `transformers-asr`: optional experimental non-Whisper ASR adapter. The
   first live spike uses `UsefulSensors/moonshine-tiny`; it is not exposed in
   the main UI or included in the Whisper-only package.

## UI/UX State

The local UI moves from the v2 dark slate UI to a lighter "liquid glass" style
with more settings density. The settings page is more capable but also more
complex. The release path should keep Whisper prominent, label Gemma clearly as
experimental, and avoid claiming download/build readiness before the gates
pass.

Offscreen screenshot capture produced missing glyph boxes, likely due to Qt
offscreen font behavior. Treat real Windows visual QA as required before any
release.

## Risk Register

- Public version policy is now explicit: use `v3.0.0` for the Whisper-only
  baseline after gates pass; keep `3.0.0-whisper-release-smoke` only for local
  smoke artifacts.
- `tools\final_public_release_gate.py` is now the one-command final public
  artifact closure path. It keeps final preflight, Whisper-only PyInstaller,
  Inno Setup, installer smoke, size/hash checks, and final artifact audit
  together. The final public `OmniDictate_Setup_v3.0.0.exe` artifact gate
  passed locally on 2026-07-05.
- `tools\external_gate_orchestrator.py` dry-runs the remaining technical gate
  runners by default and writes an aggregate report with `release_scope_status`
  for each gate. Use `--execute` only when the human/device/model/server
  prerequisites are intentionally ready.
- `tools\publication_blocker_audit.py` is the current publication stop/go
  audit. It requires the final public artifact reports to be passed/ready and
  then reports publication as ready after the physical microphone phrase-match
  VAD/PTT gate passed. Gemma E4B live generation and real GGUF server support are
  scoped out of the public Whisper-only `v3.0.0` release by user authorization
  on 2026-07-05.
- `tools\release_decision_matrix_report.py` is the compact local release view:
  it writes `smoke_test_assets\packaging\release-decision-matrix.json` with the
  final artifact state, saved GitHub preflight state, each release-scope gate,
  evidence path, dry-run command, and real closure command.
- `tools\external_gate_prerequisite_audit.py` writes
  `smoke_test_assets\external-gate-prerequisites.json` without live side
  effects. It reports missing gate evidence files/reports and whether local
  Gemma E4B safetensors are present before a live attempt, and records the
  closure report plus closure-audit command for each remaining gate.
- `tools\external_gate_closure_audit.py` writes
  `smoke_test_assets\external-gate-closure-audit.json` and classifies each
  gate as `missing-evidence`, `evidence-failed`, or `eligible-for-proven`
  using the same per-gate report-audit functions used for live closure.
- Large local model caches existed as untracked files. `.gitignore` now blocks
  common model artifacts and cache directories.
- `preload_model_on_launch` now starts a fail-soft background warm-up for the
  selected built-in Gemma backend on app launch. It loads and unloads the
  backend without opening the microphone, reports status in the status bar, and
  is covered by `tools\preload_model_worker_test.py` in the quick gate.
- Live Gemma E2B generation has been verified in this pass; E4B has not.
- Gemma E2B live generation is verified for hybrid/context and native-audio
  routes. Native audio worked on CPU but took 246.39s for a 3.19s fixture, so
  hybrid remains the only practical experimental path on this hardware.
- Gemma E4B live generation is still unverified because local E4B weights were
  not present. The UI labels E4B as unverified instead of presenting it as a
  peer-verified path.
- `tools\gemma_e4b_gate.py` is now the one-command E4B closure path. It keeps
  local-weight preflight, hybrid live smoke, and report audit together while
  normal quick verification covers only dry-run/test behavior.
- GGUF server mode has a mock contract test covering `/v1/models`,
  `/v1/chat/completions`, image data URLs, Pure-mode server bypass, and no raw
  audio in outbound requests. A real llama.cpp or LM Studio server remains
  unverified.
- `tools\gguf_real_server_gate.py` is now the one-command real-server closure
  path. It keeps the direct server probe, full GGUF backend smoke, and report
  audit together while normal quick verification covers only dry-run/test
  behavior.
- GGUF support is server-based only; there is no embedded llama.cpp runtime.
- Packaging hidden imports may still be incomplete for PyInstaller.
- PyInstaller now builds an isolated local bundle and the packaged app launches,
  but the bundle is 4,793,231,892 bytes across 5,307 files.
- Inno high-compression installer compile timed out after 30 minutes, while a
  no-compression single-file installer exceeded the 2,100,000,000 byte setup
  limit. A disk-spanned no-compression compile passed, producing one setup
  launcher plus three `.bin` slices totaling 4,796,031,102 bytes.
- A `whisper-only` PyInstaller profile now trims the practical baseline bundle
  to a practical public bundle. The current final public build is 322,225,944
  bytes and the installer is 324,505,897 bytes. This profile excludes Torch,
  Transformers, bitsandbytes, OpenCV, SciPy, Gemma download tooling, Gemma
  weights, GGUF files, and alternative STT model files. It intentionally
  retains PyAV and Hugging Face Hub because Faster-Whisper needs them for
  packaged audio decode and model resolution. The final public build bakes in
  the `whisper-only` runtime profile and its packaged runtime smoke loaded
  `large-v3-turbo` on CUDA float16 on the release test machine.
- Baseline UI/import paths no longer eagerly import Gemma/Torch/video/download
  stacks; `tools\import_boundary_test.py` covers this in the quick gate.
- Alternative STT now has a lazy Transformers ASR adapter, fake-pipeline
  quick-gate test, and benchmark harness. Live Moonshine-tiny smoke passed.
  A repeated synthetic benchmark later beat the `large-v3-turbo` median
  latency bar with equal word match, but it still adds about 110 MB of Hugging
  Face cache model files plus Transformers/Torch packaging friction. It
  remains experimental until real microphone snippets, command behavior, and
  package/import boundaries are proven.
- The 2026-07-05 live ASR source refresh sorts future candidates into
  low-latency dictation, multilingual/dialect, realtime/heavy runtime, and
  rich-transcript lanes. IBM Granite Speech, VibeVoice-ASR, Cohere Transcribe,
  and MOSS-Transcribe are rich-transcript/meeting-note candidates, not
  automatic replacements for the global hotkey Whisper path.
- `OmniDictate_Setup.iss` now defaults to the verified per-user release path:
  `PrivilegesRequired=lowest`, `{localappdata}\OmniDictate`, and
  `x64compatible`. Admin/Program Files remains available by explicit
  preprocessor override.
- `tools\installer_smoke.ps1` passed for the per-user Whisper-only installer:
  silent install, installed app launch, silent uninstall, and payload removal.
- Final public release installer path is verified for the Whisper-only
  baseline: the release-default installer installs without UAC, launches,
  uninstalls, and removes `%LOCALAPPDATA%\OmniDictate`.
- Gemma package policy is decided: the baseline release installer is
  Whisper-only. Gemma dependencies, model weights, Transformers/Torch stacks,
  and GGUF assets are source/dev or separately named experimental package
  material only after their own gates pass; they must not be silently bundled
  into the public baseline installer.
- Visual context has local smoke coverage for generated image attachment,
  generated video-frame sampling, active-window capture, full-screen capture,
  and webcam fail-soft/capture behavior.
- Native Windows screenshot evidence shows the main dictation view renders
  readable text. Offscreen Qt screenshots can show square glyph boxes and
  should not be used as the visual-font authority.
- Native Windows settings-page screenshots now cover Whisper-only/Pure, Gemma
  hybrid/context, and GGUF context variants with readable text.
- Packaged app screenshot smoke passed from the installed per-user
  Whisper-only build and removed the payload afterward. The latest smoke uses
  an isolated temporary `QSettings` app id and verifies the clean first-run
  baseline screen: Faster-Whisper, Pure transcription, Whisper-only path,
  context off, and `large-v3-turbo`.
- The Start/Stop transport buttons now use explicit runtime states instead of
  always coloring Stop as a destructive action. Start is the primary action
  only while idle, Stop is the primary action only while dictation is running,
  and Stop uses a neutral busy state while shutdown is still in progress.
- Settings now include `Check for Updates`, `Type into active app`, `Minimum
  PTT hold`, and Czech language selection. Update checks are explicit user
  actions only; there is no startup network request and no in-place updater.
- The public Whisper-only Settings page was visually rechecked on 2026-07-06
  after increasing row padding and text weight. The native screenshot at
  `smoke_test_assets\ui\settings-whisper-public-font-padding-2026-07-06.png`
  shows the row borders no longer cutting through visible text, and
  `tools\ui_smoke_test.py --assert-whisper-only-ui --page settings` now scans
  visible labels so Gemma/GGUF-only copy cannot leak into the public Settings
  page.
- Live Notepad typing is covered by `tools\live_typing_smoke.py`.
- Synthetic VAD-to-Notepad flow is covered by
  `tools\full_loop_synthetic_smoke.py`; physical microphone VAD/PTT capture
  passed on 2026-07-05.
- The worker now discards pending keystrokes when OmniDictate is the foreground
  window, preventing old transcripts from being replayed into whichever app is
  clicked next. The transcript remains visible inside OmniDictate.
- Stop handling is asynchronous for normal UI use. `main_gui.py` queues
  `DictationWorker.stop_processing()` to the worker thread, `core_logic.py`
  emits `stop_completed`, and the worker thread quits from that signal. The
  worker drops queued transcription requests on stop; an in-flight model call
  still cannot be interrupted mid-call, so the UI remains in a stopping state
  until cleanup completes.
- The #27 keyboard-simulation request is handled by `type_into_active_app`; if
  it is off, transcripts are displayed but no keystrokes are queued. The #18
  short-PTT issue is mitigated by `min_ptt_duration_ms`, default `250 ms`.
- Global PTT and Ctrl+1/2/3 hotkeys are covered by
  `tools\global_hotkey_smoke.py`.
- Local physical microphone capture is no longer blocked at device open after
  permission was granted. The physical microphone release gate passed on
  2026-07-05 using device `1`: prompted saved-WAV capture, VAD, PTT, and
  `tools\microphone_gate_report_audit.py` all passed. The live microphone
  smoke uses a bounded transcript attempt by default (`--max-transcripts 1`)
  so mismatches fail cleanly instead of requiring Ctrl+C.
- `tools\microphone_capture_diagnostic.py` now records a fixed-duration
  physical mic WAV, reports level/clipping stats, and can transcribe that exact
  sample with Whisper. The non-interactive Realtek run opened the device but
  captured near-silence, so the next physical gate needs a spoken phrase or a
  deliberate loopback source before judging VAD/PTT quality.
- `tools\physical_microphone_gate.py` is now the one-command guided path for
  physical microphone evidence. It still uses the lower-level capture,
  saved-WAV revalidation, live VAD/PTT, and report-audit tools internally, but
  reduces the human run to one prompted command.
- `tools\external_gate_orchestrator.py` is the aggregate command wrapper for
  the remaining technical gates. It defaults to dry-run mode and writes
  `smoke_test_assets\external-gates-dry-run.json` with each gate's
  release-scope status; use `--execute` only when intentionally running the
  real physical microphone gate or future experimental Gemma E4B/GGUF gates.
