# OmniDictate 3.0.0 Whisper-Only Artifact Manifest

Date: 2026-07-06
Status: current local final public artifact, ready for GitHub publication.
The recommended public release tag is `v3.0.0`; see
`docs/release/PUBLISHING_RUNBOOK_3.0.0.md`.

## Package Policy

The current baseline artifact is Whisper-only. It does not intentionally bundle
Gemma 4 weights, GGUF model files, alternative STT model files, local
Hugging Face caches, or `smoke_test_assets`. The final PyInstaller build bakes
in the `whisper-only` runtime profile so normal installed launches hide
Gemma/GGUF controls and sanitize stale experimental settings without an
external environment variable.

## Current Artifacts

| Artifact | Path | Size | SHA256 |
| --- | --- | ---: | --- |
| Final public installer | `smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe` | 324,505,897 bytes | `3DD9CF5CD1E172D41208DDD3BDC3380A5A18BA1DDBA4BD5F3CE7FDEA2CEA10A5` |
| Release-default installer smoke | `smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe` | 236,263,090 bytes | `B03A4BFA51CF363329FC47010A11F336E4F4D055DAB5E1C4EDF2B032DE0C8FEE` |
| Final packaged app executable | `smoke_test_assets\packaging\dist-whisper-final\OmniDictate\OmniDictate.exe` | 12,014,414 bytes | `0394CF935B661A3261C82284F02B41C34D53985C35D5897F2F84D89D0AEC3B02` |
| Packaged app executable | `smoke_test_assets\packaging\dist-whisper\OmniDictate\OmniDictate.exe` | 6,962,895 bytes | `0EFE8D0106041C5B48AB9D717D82B9F2DA4FBAE99BBD5EE1B27EED76C893E7BE` |
| Final packaged screenshot | `smoke_test_assets\ui\packaged-whisper-final.png` | 54,308 bytes | `4BB49B2368EDDEBC25966D2D12A61721848CBDBE2A23FD55833A46AF9F5B7B8E` |
| Packaged first-run screenshot | `smoke_test_assets\ui\packaged-whisper-first-run.png` | 69,863 bytes | `2515C427ED4A6EAD025C697DABC2BB18AA92ED3B2B47A0F34A6039FA96FC8D4E` |

## Bundle Size Audit

Command:

```powershell
.\venv\Scripts\python.exe tools\package_size_audit.py smoke_test_assets\packaging\dist-whisper-final\OmniDictate --top 8 --fail-over-mb 330
```

Result: passed.

```text
Total: 307.3 MB (322225944 bytes)
Top 2 entries:
  295.8 MB  _internal
   11.5 MB  OmniDictate.exe
```

Final public artifact gate: passed

```powershell
.\venv\Scripts\python.exe tools\final_public_release_gate.py --report-json smoke_test_assets\packaging\final-public-release-gate-report.json
```

Result: passed on 2026-07-06. The gate wrote
`smoke_test_assets\packaging\final-public-release-gate-report.json`, rebuilt
`smoke_test_assets\packaging\dist-whisper-final\OmniDictate`, compiled
`smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.0.exe`,
ran the packaged Whisper runtime smoke with `large-v3-turbo`, ran the
per-user installer smoke, ran the size/hash steps, and wrote
`smoke_test_assets\packaging\final-release-gate-report.json`.

Final release audit:

```text
bundle_bytes: 322225944
installer_bytes: 324505897
installer_sha256: 3DD9CF5CD1E172D41208DDD3BDC3380A5A18BA1DDBA4BD5F3CE7FDEA2CEA10A5
status: ready
```

Packaged runtime smoke:

```text
package_profile: passed (whisper-only)
av_import: passed
faster_whisper_import: passed
runtime_settings: passed
whisper_load: Whisper model 'large-v3-turbo' loaded on cuda (float16).
```

## Manifest Integrity Audit

Command:

```powershell
.\venv\Scripts\python.exe tools\artifact_manifest_audit.py
```

Result: passed on 2026-07-06. The audit recomputed the listed artifact sizes,
SHA256 hashes, and packaged screenshot dimensions from the local files.

## Screenshot Evidence

Current first-run packaged screenshot:

```text
smoke_test_assets\ui\packaged-whisper-first-run.png
916x719 RGB, 69,863 bytes
```

The screenshot evidence shows the expected Whisper baseline:

- Faster-Whisper backend.
- Pure transcription mode.
- Whisper-only path.
- Context off.
- `large-v3-turbo`.

## Fresh Release Gate Evidence

Latest focused Whisper gate:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_whisper.ps1 -Model large-v3-turbo
```

Result: passed on 2026-07-05. Route `Whisper only`, latency `0.60s`, 8/8
expected words.

Latest release-default installer smoke:

```powershell
powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1 -InstallerPath smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe -InstallDir "$env:LOCALAPPDATA\OmniDictate" -UseInstallerDefaults
```

Result: passed on 2026-07-05. The installer used its defaults to install to
`%LOCALAPPDATA%\OmniDictate`, launched, uninstalled, and removed the installed
payload.

## Remaining Before Publication

- Publish only after final human review of the release notes/runbook and an
  explicit user request to tag and publish.
- Keep Gemma E4B and real GGUF server claims experimental unless their live
  gates pass before publication.
