# OmniDictate v3.0.0 Publishing Runbook

Date: 2026-07-06
Status: final artifact path executed locally; publication gates passed

## Version Decision

Recommended public tag: `v3.0.0`

Recommended public installer name:

```text
OmniDictate_Setup_v3.0.0.exe
```

Rationale:

- `v2.0.2` is the last successful public release.
- The current baseline release candidate is a Whisper-only product recovery,
  not a Gemma-enabled public release.
- `OmniDictate_Setup.iss` already defaults to `AppVersion "3.0.0"`.
- `main_gui.py` uses app user model id `omnicorp.omnidictate.gui.3.0.0`.
- The `3.0.0-whisper-release-smoke` suffix should remain local evidence
  naming, not the public GitHub tag.

## Final Build Command

Before executing any final build, dry-run the aggregate external gate
orchestrator so the remaining technical gates and their release-scope statuses
are visible from one report:

```powershell
.\venv\Scripts\python.exe tools\external_gate_orchestrator.py --report-json smoke_test_assets\external-gates-dry-run.json
```

The orchestrator defaults to dry-run mode. Use `--execute` only when you are
ready to run the real physical microphone gate or future experimental Gemma
E4B/GGUF gates.
Add `--microphone-device 8` with the intended numeric sounddevice input index
when the physical microphone gate should use a non-default input. Use a device
display name only when `tools\microphone_capture_diagnostic.py --list-devices`
shows that input name is unique.
`tools\open_gate_summary.py --strict` prints the remaining technical gate list
with `Scope: proven` for the physical microphone evidence and
`Scope: scoped-out` for Gemma E4B / real GGUF in this Whisper-only release.
Use `docs\implementation-plans-and-checklists\phase-4-release-execution.md`
as the checklist for release execution.

Record any pass/pending/scoped-out release-scope decision in:

```text
docs\release\RELEASE_SCOPE_DECISIONS_3.0.0.md
```

Then run:

```powershell
.\venv\Scripts\python.exe tools\release_scope_decision_audit.py
```

The current expected result keeps `physical-microphone` as `proven` and keeps
Gemma E4B / real GGUF as authorized `scoped-out` rows. A `scoped-out` row
requires explicit user authorization and a release note/checklist update
marker.

Run the publication blocker audit after any final artifact rebuild or gate
status change. It should report `ready` when the physical microphone gate is
proven and the experimental gates remain explicitly scoped out:

```powershell
.\venv\Scripts\python.exe tools\publication_blocker_audit.py --report-json smoke_test_assets\packaging\publication-blockers.json
```

The JSON report includes `schema_version`, `generated_at_utc`,
`scope_decisions_doc`, `scope_gate_statuses`, `open_gate_details`, and the
current final artifact statuses so stale blocker evidence is easier to
identify. `pending` rows in `RELEASE_SCOPE_DECISIONS_3.0.0.md` remain
publication blockers; `proven` or authorized `scoped-out` rows are the only
machine-readable path to remove a gate from this blocker report.

For a single human-readable and machine-readable release status snapshot, run:

```powershell
.\venv\Scripts\python.exe tools\release_status_report.py --report-json smoke_test_assets\packaging\release-status-report.json
```

That report also includes the aggregate external-gate dry-run command and a
copy/pasteable selected-microphone numeric-index variant using
`--microphone-device` and the current inventory recommendation. Its JSON
payload is also schema-versioned and stamped with `generated_at_utc`.

For a compact decision matrix that release agents can scan without expanding
nested reports, run:

```powershell
.\venv\Scripts\python.exe tools\external_gate_prerequisite_audit.py --report-json smoke_test_assets\external-gate-prerequisites.json
```

```powershell
.\venv\Scripts\python.exe tools\external_gate_closure_audit.py --report-json smoke_test_assets\external-gate-closure-audit.json
```

```powershell
.\venv\Scripts\python.exe tools\release_decision_matrix_report.py --report-json smoke_test_assets\packaging\release-decision-matrix.json
```

The prerequisite audit has no live side effects; it checks fixture files,
expected gate reports, and local Gemma E4B safetensors. The matrix combines
final artifact readiness, saved GitHub preflight state, each pending
release-scope gate, evidence paths, prerequisite gaps, dry-run commands, and
real closure commands. Each prerequisite row also records the closure report
and closure-audit command that prove the gate after a live run. The closure
audit reads saved evidence and marks gates `eligible-for-proven` only when the
same per-gate report audits pass.

After refreshing the saved JSON reports, verify they still match current tool
output. The audit also checks the saved GitHub preflight snapshot:

```powershell
.\venv\Scripts\python.exe tools\release_snapshot_freshness_audit.py
```

The freshness audit ignores only `generated_at_utc`; stale gate lists,
artifact statuses, installer hashes, remote tag state, GitHub preflight
scope blockers, external-gate dry-run command shapes, or command shapes fail
the audit.

Before creating a GitHub release or tag, run the remote publication preflight:

```powershell
.\venv\Scripts\python.exe tools\github_release_preflight.py --report-json smoke_test_assets\packaging\github-release-preflight.json
```

It checks that the configured remote is reachable, that `v3.0.0` is not
already present, that the last public `v2.0.2` tag is visible, that the final
installer exists, and that the local release status is publishable. The current
expected result is `ready` if the remote tag is still absent.
The JSON report includes `schema_version`, `generated_at_utc`,
`scope_gate_statuses`, and `pending_release_scope_gates` so the remote
preflight shows the same scope-decision blockers as the local publication
audit.

The final public artifact has already been produced locally with this gate
runner. Rerun it before publication if any release input changes:

```powershell
.\venv\Scripts\python.exe tools\final_public_release_gate.py --report-json smoke_test_assets\packaging\final-public-release-gate-report.json
```

It runs the final preflight, PyInstaller build, Inno Setup compile, installer
smoke, package-size audit, hash command, and final artifact audit internally.
Use `--dry-run` to record the intended sequence without building.

The first internal step checks local static prerequisites and writes the final
build intent:

```powershell
.\venv\Scripts\python.exe tools\final_release_preflight.py --report-json smoke_test_assets\packaging\final-release-preflight.json
```

Then rebuild the final public installer without the smoke suffix:

```powershell
$env:OMNIDICTATE_PACKAGE_PROFILE='whisper-only'
.\venv\Scripts\pyinstaller.exe --clean --noconfirm --distpath smoke_test_assets\packaging\dist-whisper-final --workpath smoke_test_assets\packaging\build-whisper-final OmniDictate.spec
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0' /DSourceDir='smoke_test_assets\packaging\dist-whisper-final\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-final' /DCompressionMode=none /DSolidCompressionMode=no OmniDictate_Setup.iss
```

Then run:

```powershell
powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1 -InstallerPath smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe -InstallDir "$env:LOCALAPPDATA\OmniDictate" -UseInstallerDefaults
.\venv\Scripts\python.exe tools\package_size_audit.py smoke_test_assets\packaging\dist-whisper-final\OmniDictate --top 8 --fail-over-mb 330
.\venv\Scripts\python.exe tools\file_sha256.py smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe
.\venv\Scripts\python.exe tools\final_release_gate_audit.py --preflight-report smoke_test_assets\packaging\final-release-preflight.json --bundle smoke_test_assets\packaging\dist-whisper-final\OmniDictate --installer smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe --report-json smoke_test_assets\packaging\final-release-gate-report.json
```

Update `docs/release/ARTIFACT_MANIFEST_3.0.0-whisper.md` after any future
final artifact rebuild. The final gate audit must pass before publishing; it
verifies that the preflight intent matches the final bundle and installer
paths, rejects smoke artifact names, enforces the
`OmniDictate_Setup_v3.0.0.exe` public filename, records the installer SHA256,
and writes `final-release-gate-report.json`.

Latest final local artifact result: passed on 2026-07-06. The final installer
is `smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe`,
324,505,897 bytes, SHA256
`3DD9CF5CD1E172D41208DDD3BDC3380A5A18BA1DDBA4BD5F3CE7FDEA2CEA10A5`.

## Required Gates Before Publishing

- Physical microphone phrase-match VAD/PTT passes, or the user explicitly
  moves that gate out of release scope.
- `tools\verify_local.ps1` passes.
- `tools\verify_whisper.ps1 -Model large-v3-turbo` passes.
- Final installer smoke passes against `OmniDictate_Setup_v3.0.0.exe`.
- `tools\final_public_release_gate.py` writes
  `smoke_test_assets\packaging\final-public-release-gate-report.json` with
  `status: passed`.
- `tools\publication_blocker_audit.py` writes
  `smoke_test_assets\packaging\publication-blockers.json`; its current
  `blocked` result is a publication stop until the listed gates pass or the
  remaining blockers are explicitly moved out of release scope.
- `tools\release_scope_decision_audit.py` passes against
  `docs\release\RELEASE_SCOPE_DECISIONS_3.0.0.md`.
- `tools\github_release_preflight.py` writes
  `smoke_test_assets\packaging\github-release-preflight.json`; it must report
  `ready` with `publish_ready: true` before a GitHub release or `v3.0.0` tag is
  created.
- `tools\final_release_gate_audit.py` passes against
  `smoke_test_assets\packaging\final-release-preflight.json`, the final
  bundle, and `OmniDictate_Setup_v3.0.0.exe`.
- Artifact manifest is recomputed for the final installer.
- Release notes state that the public package is Whisper-only.
- Gemma E4B and real GGUF remain labeled experimental/unverified unless their
  own live gates pass before publishing.

## GitHub Release Notes Shape

Title:

```text
OmniDictate v3.0.0
```

Opening note:

```text
OmniDictate v3.0.0 is a Windows desktop dictation release focused on reliable
local Whisper speech-to-text. It improves the packaged installer, Settings,
update checks, and day-to-day dictation stability.
```

Recommended release body:

```text
Download OmniDictate_Setup_v3.0.0.exe below, run it normally, and allow
microphone permission if Windows asks.

What's new:
- Local Whisper dictation with large-v3-turbo support.
- Smaller installer that downloads selected Whisper models on first use.
- Check for Updates button in Settings.
- Transcribe Only option by turning off active-app typing.
- Czech language option.
- Minimum PTT hold setting to ignore accidental quick taps.
- Safer stop handling and better cleanup during shutdown.

Fresh Windows requirements:
- Windows 10 or Windows 11, 64-bit.
- Working microphone.
- Internet access on first use for model download.
- NVIDIA driver and CUDA runtime files for GPU acceleration. CPU mode can work
  but is slower.
- Microsoft Visual C++ Redistributable 2015-2022 x64 if Windows reports missing
  runtime DLLs.

Uninstall:
Use Windows Settings > Apps > Installed apps, or run
%LOCALAPPDATA%\OmniDictate\unins000.exe.

The app is unsigned, so Windows SmartScreen may show a warning. Only continue
if the installer came from this official GitHub release.
```
