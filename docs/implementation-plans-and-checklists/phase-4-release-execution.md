# Phase 4 Release Execution Plan

Goal: turn the recovered Whisper-only baseline into a publishable release
without accidentally promoting unverified Gemma, GGUF, microphone, or
alternative-STT behavior.

Status: ready for publication after physical microphone gate pass

## P4.0 - Current Stop/Go Snapshot

- [x] Final public Whisper-only artifact exists and passed the final public
  release gate.
- [x] `tools\publication_blocker_audit.py` reports publication as `ready`
  after the physical microphone release-scope gate passed and writes a schema-versioned,
  `generated_at_utc` stamped JSON snapshot with detailed open-gate commands.
- [x] `tools\release_status_report.py` aggregates the final artifact status,
  publication blocker result, open gates, aggregate external-gate dry-run
commands, selected-microphone dry-run guidance, the copy/pasteable
selected-microphone numeric-index variant, inventory-backed microphone
  defaults, run-card preparation commands, and next gate commands in a
  schema-versioned, `generated_at_utc` stamped JSON snapshot.
- [x] `tools\release_snapshot_freshness_audit.py` verifies the saved
  publication blocker, release status, GitHub preflight, and external-gate
  dry-run JSON snapshots still match current tool output. It compares
  GitHub preflight JSON snapshots and external-gate dry-run JSON snapshots while
  ignoring only `generated_at_utc`.
- [x] `docs\release\RELEASE_SCOPE_DECISIONS_3.0.0.md` and
  `tools\release_scope_decision_audit.py` make pass/pending/scoped-out
  release decisions explicit. Current status: physical microphone is
  `proven`, while Gemma E4B and real GGUF are authorized `scoped-out` rows for
  this Whisper-only release.
- [x] `tools\publication_blocker_audit.py` consumes those release-scope decisions:
  `pending` rows remain blockers, while future `proven` or
  authorized `scoped-out` rows are the machine-readable path for removing a
  gate from publication blockers.
- [x] `tools\github_release_preflight.py` checks the GitHub remote, `v3.0.0`
  tag absence, last public `v2.0.2` tag visibility, final installer presence,
  local publishable status, and top-level release-scope blocker summary via
  `scope_gate_statuses` plus `pending_release_scope_gates`.
- [x] `tools\handoff_next_action_audit.py` verifies that `docs\ai\HANDOFF.md`
  still points at this release execution checklist and the current gate
  commands.
- [x] `tools\open_gate_summary.py --strict` prints the same three gates, each
  gate's release-scope decision status, including `Scope: proven` for the
  physical microphone gate, and the
  inventory-backed numeric microphone `--device` value when the saved
  audio-device inventory recommends one.
- [x] `tools\goal_completion_audit.py` keeps the full objective open.

Acceptance: the stop/go answer is machine-readable and agrees with the
handoff, release checklist, and completion audit.

## P4.1 - Physical Microphone Release Gate

Status: passed on 2026-07-05

- [x] List input-capable audio devices without recording:

  ```powershell
  .\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --list-devices --report-json smoke_test_assets\microphone\audio-device-inventory.json
  ```

  Use the listed numeric index with `--device` if the Windows default input is
  not the intended microphone. A device name is acceptable only when the
  inventory shows that input name is unique; if duplicate names appear, prefer
  the numeric recommended `--device` value from the inventory output.

- [x] Run the guided one-command physical microphone gate:

  ```powershell
  .\venv\Scripts\python.exe tools\physical_microphone_run_card.py --report-json smoke_test_assets\microphone\physical-gate-dry-run.json
  ```

  ```powershell
  .\venv\Scripts\python.exe tools\physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --report-json smoke_test_assets\microphone\physical-gate-report.json
  ```

  The run-card command prints the exact phrase, selected device, countdown,
  recording duration, required VAD/PTT modes, and pass rule from the latest
  dry-run report.

  The current saved audio-device inventory recommends numeric `--device 1`.
  Add `--device 8` with the intended numeric sounddevice input index if the
  intended physical microphone changes from the saved inventory recommendation.
  Use a quoted device name only when the inventory shows that name is unique.
  Capture and live-loop reports must agree on device metadata when a device is
  supplied.

  If the prompted saved-WAV capture and capture report already passed, but the
  VAD/PTT loop needs another attempt, reuse that capture evidence instead of
  asking the human to record the same phrase again:

  ```powershell
  .\venv\Scripts\python.exe tools\physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --reuse-capture --report-json smoke_test_assets\microphone\physical-gate-report.json
  ```

  On 2026-07-05, the saved-WAV capture, VAD live-loop, PTT live-loop, and
  `tools\microphone_gate_report_audit.py` all passed on device `1`.

- [x] Confirm `smoke_test_assets\microphone\physical-gate-report.json` has
  `status: passed`.
- [x] Confirm saved-WAV capture, saved-WAV transcription, VAD, PTT, and
  `tools\microphone_gate_report_audit.py` all pass.
- [ ] If the transcript mismatches, keep the failed report as evidence and do
  not close the gate.

Acceptance: prompted physical speech matches the expected phrase, both VAD and
PTT pass, and the report audit passes.

## P4.2 - Gemma E4B Release-Scope Decision

Status: scoped out for v3.0.0 Whisper-only on 2026-07-05

- [x] User authorization recorded in
  `docs\release\RELEASE_SCOPE_DECISIONS_3.0.0.md`.
- [x] Release notes and checklist state the impact: the public Whisper-only
  installer does not include or claim E4B speech refinement/native E4B audio;
  E4B remains experimental until local weights and live evidence pass.
- [ ] Future release work only: if E4B returns to release scope, place local
  `google/gemma-4-E4B-it` safetensors under the configured model store and
  run:

  ```powershell
  .\venv\Scripts\python.exe tools\gemma_e4b_gate.py --model google/gemma-4-E4B-it --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gemma-e4b-gate-report.json
  ```

  The runner validates the local audio/image fixtures before attempting local
  model preflight or live generation, and writes a failed report if those
  fixtures are missing.

- [ ] Future release work only: confirm the report proves local weights, hybrid `Whisper -> Gemma`
  route, visual context, expected transcript match, and report-audit success.

Acceptance: E4B is explicitly scoped out of the public Whisper-only release;
future E4B claims still require the live gate.

## P4.3 - Real GGUF Server Release-Scope Decision

Status: scoped out for v3.0.0 Whisper-only on 2026-07-05

- [x] User authorization recorded in
  `docs\release\RELEASE_SCOPE_DECISIONS_3.0.0.md`.
- [x] Release notes and checklist state the impact: the public Whisper-only
  installer does not include or claim llama.cpp/LM Studio/GGUF refinement; real
  GGUF remains experimental until a named server passes the live gate.
- [ ] Future release work only: start a named non-mock OpenAI-compatible multimodal server, such as LM
  Studio or llama.cpp.
- [ ] Run:

  ```powershell
  .\venv\Scripts\python.exe tools\gguf_real_server_gate.py --url http://127.0.0.1:8080/v1 --server-implementation "LM Studio" --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gguf\real-server-gate-report.json
  ```

  The runner validates the local audio/image fixtures before contacting the
  server, and writes a failed report if those fixtures are missing.

- [ ] Future release work only: confirm direct probe, backend smoke, no-raw-audio behavior, expected
  transcript match, visual context, and report-audit success.

Acceptance: GGUF is explicitly scoped out of the public Whisper-only release;
future GGUF claims still require the real-server gate.

## P4.4 - Publication Decision

Status: ready after P4.1 pass

- [ ] Rerun:

  ```powershell
  .\venv\Scripts\python.exe tools\publication_blocker_audit.py --report-json smoke_test_assets\packaging\publication-blockers.json
  ```

- [ ] Rerun:

  ```powershell
  .\venv\Scripts\python.exe tools\release_status_report.py --report-json smoke_test_assets\packaging\release-status-report.json
  ```

- [ ] Rerun:

  ```powershell
  .\venv\Scripts\python.exe tools\release_snapshot_freshness_audit.py
  ```

- [ ] Rerun:

  ```powershell
  .\venv\Scripts\python.exe tools\release_scope_decision_audit.py
  ```

- [ ] Rerun:

  ```powershell
  .\venv\Scripts\python.exe tools\github_release_preflight.py --report-json smoke_test_assets\packaging\github-release-preflight.json
  ```

- [ ] Rerun:

  ```powershell
  .\venv\Scripts\python.exe tools\handoff_next_action_audit.py
  ```

- [ ] Rerun:

  ```powershell
  powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
  git diff --check
  ```

- [ ] If any final release input changed, rerun:

  ```powershell
  .\venv\Scripts\python.exe tools\final_public_release_gate.py --report-json smoke_test_assets\packaging\final-public-release-gate-report.json
  ```

- [ ] Update the artifact manifest and release notes with the exact artifact
  being published.
- [ ] Publish only if the remaining blockers are passed or explicitly scoped
  out and the release notes still say the installer is Whisper-only.

Acceptance: the release decision is backed by current blocker, final-artifact,
manifest, release-note, and quick-gate evidence.
