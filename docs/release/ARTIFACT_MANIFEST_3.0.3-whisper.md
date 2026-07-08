# OmniDictate 3.0.3 Whisper-Only Artifact Manifest

Date: 2026-07-08
Status: final public artifact passed local release gates.

## Current Artifact

| Artifact | Path | Size | SHA256 |
| --- | --- | ---: | --- |
| Final public installer | `smoke_test_assets\packaging\installer-whisper-final\OmniDictate_Setup_v3.0.3.exe` | 324,518,159 bytes | `057F1A9E2BF6866C07AE2120468CE3EB1349EEF86C6E45CC6E3C2B5F3F78EB06` |

## Gate Evidence

Final public release gate:

```powershell
.\venv\Scripts\python.exe tools\final_public_release_gate.py --report-json smoke_test_assets\packaging\final-public-release-gate-report.json
```

Result: passed on 2026-07-08.

Final release audit:

```text
bundle_bytes: 322238198
installer_bytes: 324518159
installer_sha256: 057F1A9E2BF6866C07AE2120468CE3EB1349EEF86C6E45CC6E3C2B5F3F78EB06
status: ready
```

The gate rebuilt the Whisper-only PyInstaller bundle, compiled
`OmniDictate_Setup_v3.0.3.exe`, loaded the packaged `large-v3-turbo` Whisper
path, ran the installer smoke, checked bundle size, and audited the final
artifact.
