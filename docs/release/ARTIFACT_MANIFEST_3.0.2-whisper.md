# OmniDictate 3.0.2 Whisper-Only Artifact Manifest

Date: 2026-07-08
Status: final public artifact passed local release gates.

## Current Artifact

| Artifact | Path | Size | SHA256 |
| --- | --- | ---: | --- |
| Final public installer | `smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.2.exe` | 324,516,430 bytes | `AC1D403DFA35E97AAFAB68C2A0E0AD00208456A6EE71611BB6FBCD28BD29627F` |

## Gate Evidence

Final public release gate:

```powershell
.\venv\Scripts\python.exe tools\final_public_release_gate.py --report-json smoke_test_assets\packaging\final-public-release-gate-report.json
```

Result: passed on 2026-07-08.

Final release audit:

```text
bundle_bytes: 322236521
installer_bytes: 324516430
installer_sha256: AC1D403DFA35E97AAFAB68C2A0E0AD00208456A6EE71611BB6FBCD28BD29627F
status: ready
```

The gate rebuilt the Whisper-only PyInstaller bundle, compiled
`OmniDictate_Setup_v3.0.2.exe`, loaded the packaged `large-v3-turbo` Whisper
path, ran the installer smoke, checked bundle size, and audited the final
artifact.
