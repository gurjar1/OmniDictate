# OmniDictate 3.0.0 Whisper-Only Release Checklist

Date: 2026-07-06
Status: release candidate documentation, ready for GitHub publication

## Release Scope

Ship the verified Whisper-only Windows baseline as the next public package.
Gemma 4, GGUF server refinement, visual context, reasoning, and alternative
STT remain experimental source/dev features until their own live gates pass.

## Must Pass Before Tagging

- [x] Repo baseline understood: `v2.0.2` is the last successful public release.
- [x] Default dictation route remains `faster-whisper`.
- [x] Quick non-interactive gate passes:
  `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1`.
- [x] Whisper fixture gate passes for `tiny`.
- [x] Whisper fixture gate passes for release default `large-v3-turbo`.
- [x] Worker behavior tests cover punctuation, filter phrases, PTT queueing,
  VAD queueing, and own-window typing guard.
- [x] Live Notepad typing smoke passes.
- [x] Synthetic VAD -> Whisper -> routing -> Notepad smoke passes.
- [x] Global PTT and Ctrl+1/2/3 hotkey smoke passes.
- [x] Physical microphone opens after Windows permission is granted.
- [x] Saved microphone WAVs can be revalidated without reopening the physical
  microphone.
- [x] Physical microphone phrase-match VAD and PTT both pass on real speech.
- [x] Whisper-only PyInstaller profile excludes Gemma/Torch/video/download
  stacks from the baseline package.
- [x] Whisper-only PyInstaller runtime hook is baked into the public bundle so
  installed launches hide Gemma/GGUF without requiring a terminal environment
  variable.
- [x] Packaged runtime smoke loads `large-v3-turbo` on CUDA float16 on the
  release test machine.
- [x] Whisper-only release-default Inno installer compiles.
- [x] Release-default installer installs to `%LOCALAPPDATA%\OmniDictate`,
  launches, uninstalls, and removes the install directory.
- [x] Packaged first-run screenshot shows the Whisper baseline:
  Faster-Whisper, Pure transcription, Whisper-only path, context off, and
  `large-v3-turbo`.
- [x] README package/model-download wording matches the verified Whisper-only
  baseline policy.
- [x] Current screenshot selection and final artifact metadata are recorded in
  the artifact manifest.
- [x] Recommended public version/tag is documented as `v3.0.0`; smoke suffixes
  remain local artifact names.
- [ ] Final GitHub release notes match the exact published artifact.

## Experimental Gates Not Required For Whisper-Only Tag

- [x] Gemma 4 E2B hybrid/context smoke passed locally.
- [x] Gemma 4 E2B native-audio smoke passed locally but is too slow on CPU for
  the normal product path.
- [x] Gemma 4 E4B is scoped out of the public Whisper-only `v3.0.0` release by
  user authorization on 2026-07-05. Impact: the release does not include or
  claim E4B speech refinement/native E4B audio. Benefit: the public installer
  can remain Whisper-only while E4B waits for local weights and live proof.
  Closure command:
  `.\venv\Scripts\python.exe tools\gemma_e4b_gate.py --model google/gemma-4-E4B-it --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gemma-e4b-gate-report.json`.
- [x] GGUF OpenAI-compatible server contract test passed against a mock server.
- [x] Real GGUF server support is scoped out of the public Whisper-only
  `v3.0.0` release by user authorization on 2026-07-05. Impact: the release
  does not include or claim llama.cpp/LM Studio refinement. Benefit: no local
  server setup, GGUF/mmproj files, or unverified server behavior is required
  for the baseline installer.
  Closure command:
  `.\venv\Scripts\python.exe tools\gguf_real_server_gate.py --url http://127.0.0.1:8080/v1 --server-implementation "LM Studio" --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gguf\real-server-gate-report.json`.
- [x] Alternative STT adapter spike passed with Moonshine-tiny.
- [x] Alternative STT is not promoted to the release UI or installer.

## Current Release Artifact Evidence

- Final public installer:
  `smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe`
  at 324,505,897 bytes, SHA256
  `3DD9CF5CD1E172D41208DDD3BDC3380A5A18BA1DDBA4BD5F3CE7FDEA2CEA10A5`.
- Final Whisper-only bundle:
  `smoke_test_assets\packaging\dist-whisper-final\OmniDictate`
  at 322,225,944 bytes.
- Earlier Whisper-only smoke bundle:
  `smoke_test_assets\packaging\dist-whisper\OmniDictate`
  at 233,989,044 bytes.
- Earlier release-default installer smoke:
  `smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe`
  at 236,263,090 bytes.
- Packaged first-run screenshot:
  `smoke_test_assets\ui\packaged-whisper-first-run.png`.
- Current artifact manifest:
  `docs\release\ARTIFACT_MANIFEST_3.0.0-whisper.md`.
- Publishing runbook:
  `docs\release\PUBLISHING_RUNBOOK_3.0.0.md`.
- Release execution checklist:
  `docs\implementation-plans-and-checklists\phase-4-release-execution.md`.

## Physical Microphone Gate

The physical microphone gate passed on 2026-07-05 with a spoken phrase, not
with a silent automated capture. The guided command was:

```powershell
.\venv\Scripts\python.exe tools\physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --report-json smoke_test_assets\microphone\physical-gate-report.json
```

Use the numeric `--device` index from
`smoke_test_assets\microphone\audio-device-inventory.json`. Device names are
safe only when the inventory shows the name is unique; duplicated Windows
device display names should use numeric indexes. The runner passes the same
selected device to prompted capture and the live VAD/PTT loop, records it in
the JSON evidence, and rejects mismatched capture/live-loop device metadata.

It runs this evidence chain internally:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 7 --prompt --countdown 3 --model large-v3-turbo --output smoke_test_assets\microphone\spoken-phrase-large-v3-turbo.wav
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --input smoke_test_assets\microphone\spoken-phrase-large-v3-turbo.wav --model large-v3-turbo --report-json smoke_test_assets\microphone\spoken-phrase-large-v3-turbo-report.json
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model large-v3-turbo --mode both --timeout 40 --manual --countdown 3 --max-transcripts 1 --report-json smoke_test_assets\microphone\live-loop-large-v3-turbo-report.json
.\venv\Scripts\python.exe tools\microphone_gate_report_audit.py --capture-report smoke_test_assets\microphone\spoken-phrase-large-v3-turbo-report.json --loop-report smoke_test_assets\microphone\live-loop-large-v3-turbo-report.json
```

Acceptance for this gate:

- [x] The saved WAV has speech-level peak/RMS and no meaningful clipping.
- [x] The saved-WAV transcription matches the expected phrase at the configured
  word ratio.
- [x] The saved WAV can be revalidated with `--input` and a JSON report.
- [x] VAD records, queues, transcribes, and types or reports the expected phrase.
- [x] PTT records, queues, transcribes, and types or reports the expected phrase.
- [x] No stale transcript is rechecked repeatedly after a mismatch.
- [x] `tools\microphone_gate_report_audit.py` passes on the saved capture and
  live-loop JSON reports.
- [x] `tools\physical_microphone_gate.py` writes
  `smoke_test_assets\microphone\physical-gate-report.json` with `status:
  passed`.

## Tagging Checklist

- [x] Rerun `git diff --check`.
- [x] Rerun `tools\verify_local.ps1`.
- [ ] Dry-run all external gates with
  `.\venv\Scripts\python.exe tools\external_gate_orchestrator.py --report-json smoke_test_assets\external-gates-dry-run.json`.
  Add `--microphone-device <numeric sounddevice input index>` when the
  physical microphone gate should use a non-default input. Use a device display
  name only when the inventory shows it is unique.
- [x] Rerun doc-slice `git diff --check` and `tools\verify_local.ps1` after
  README/audit/research updates on 2026-07-05.
- [x] Add repeatable release-readiness audit to protect release policy claims.
- [x] Add GGUF real-server probe/runbook while keeping the live GGUF gate open.
- [x] Rerun `tools\verify_whisper.ps1 -Model large-v3-turbo` on 2026-07-05.
- [x] Rerun release-default installer smoke against the current installer
  artifact on 2026-07-05.
- [x] Record current final artifact names, sizes, checksums, and screenshot
  dimensions.
- [x] Confirm release docs are visible to git and no forbidden
  `smoke_test_assets`, model cache, or downloaded weight paths are staged.
- [x] Confirm release notes state that the package is Whisper-only.
- [x] Confirm experimental Gemma/GGUF/alternative-STT wording remains honest.
- [x] Add final publishing runbook for the
  `OmniDictate_Setup_v3.0.0.exe` artifact and publication path.
- [x] Final public `OmniDictate_Setup_v3.0.0.exe` artifact gate passed on
  2026-07-05.
  Closure command:
  `.\venv\Scripts\python.exe tools\final_public_release_gate.py --report-json smoke_test_assets\packaging\final-public-release-gate-report.json`.
- [x] Run `tools\final_release_gate_audit.py --preflight-report smoke_test_assets\packaging\final-release-preflight.json`
  against the final bundle and installer, and keep
  `smoke_test_assets\packaging\final-release-gate-report.json` as the final
  publication audit.
- [x] Add publication blocker audit for the current stop/go answer:
  `.\venv\Scripts\python.exe tools\publication_blocker_audit.py --report-json smoke_test_assets\packaging\publication-blockers.json`.
  Current expected result is `ready`: the physical microphone release-scope
  gate is proven, and Gemma E4B / real GGUF server support are scoped out for
  this Whisper-only release.
- [x] Add one-command release status report:
  `.\venv\Scripts\python.exe tools\release_status_report.py --report-json smoke_test_assets\packaging\release-status-report.json`.
  Current expected result is `ready`, with final artifact status `ready` and no
  pending release-scope blocker.
- [x] Add GitHub release preflight:
  `.\venv\Scripts\python.exe tools\github_release_preflight.py --report-json smoke_test_assets\packaging\github-release-preflight.json`.
  Current expected result is `ready`: the remote has `v2.0.2`, `v3.0.0` does
  not exist yet, and local publication blockers are closed for the
  Whisper-only release scope.
