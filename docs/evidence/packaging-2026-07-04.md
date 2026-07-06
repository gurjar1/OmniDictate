# Packaging Evidence - 2026-07-04

## PyInstaller Build

Command:

```powershell
.\venv\Scripts\pyinstaller.exe --noconfirm --distpath smoke_test_assets\packaging\dist --workpath smoke_test_assets\packaging\build OmniDictate.spec
```

Result: passed.

- Output directory: `smoke_test_assets\packaging\dist\OmniDictate`
- File count: 5,307 files
- Total size: 4,793,231,892 bytes
- App executable: `smoke_test_assets\packaging\dist\OmniDictate\OmniDictate.exe`
- App executable size: 68,936,248 bytes

Packaged executable launch smoke:

```powershell
Start-Process smoke_test_assets\packaging\dist\OmniDictate\OmniDictate.exe -WindowStyle Hidden
```

Result: passed. The process stayed alive for the launch window and was then
stopped by the smoke.

Notable PyInstaller warnings:

- Optional `triton` modules are missing.
- Optional `bitsandbytes`/CUDA-related paths report missing modules or DLL
  dependencies.
- Optional `sycl8.dll` and `tbb12.dll` style dependencies still need release
  triage before promising packaged Gemma acceleration.

## Inno Setup Builds

Default high-compression installer command:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DSourceDir='smoke_test_assets\packaging\dist\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer' OmniDictate_Setup.iss
```

Result: stopped after a 30 minute timeout. This is not a release-ready
installer result.

Fast single-file installer command:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DSourceDir='smoke_test_assets\packaging\dist\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-fast' /DCompressionMode=none /DSolidCompressionMode=no OmniDictate_Setup.iss
```

Result: failed because the output exceeded Inno Setup's single setup-file
limit without disk spanning:

```text
Disk spanning must be enabled in order to create an installation larger than 2100000000 bytes in size.
```

Split no-compression installer command:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DSourceDir='smoke_test_assets\packaging\dist\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-split-fast' /DCompressionMode=none /DSolidCompressionMode=no /DDiskSpanningMode=yes /DDiskSliceSizeMode=2000000000 /DSlicesPerDiskMode=10 OmniDictate_Setup.iss
```

Result: passed.

Output files:

| File | Bytes |
| --- | ---: |
| `OmniDictate_Setup_v3.0.0.exe` | 2,777,946 |
| `OmniDictate_Setup_v3.0.0-1a.bin` | 1,997,221,888 |
| `OmniDictate_Setup_v3.0.0-1b.bin` | 2,000,000,000 |
| `OmniDictate_Setup_v3.0.0-1c.bin` | 796,031,268 |

Total split installer size: 4,796,031,102 bytes.

Official Inno Setup docs confirm that disk spanning is the right mechanism for
large installer media and that slice size is controlled by `DiskSliceSize`:

- https://jrsoftware.org/ishelp/topic_setup_diskspanning.htm
- https://jrsoftware.org/ishelp/topic_setup_diskslicesize.htm

## Open Gates

- Installer install, launch, and uninstall smoke were not run because the
  current script requires admin privileges.
- The full Gemma-capable bundle is too large for a practical release in its
  current form.
- Before a Gemma-enabled release, keep Gemma-heavy dependencies optional or
  downloaded after install.

## Whisper-Only Packaging Profile

Implemented a `whisper-only` PyInstaller profile using:

```powershell
$env:OMNIDICTATE_PACKAGE_PROFILE='whisper-only'
.\venv\Scripts\pyinstaller.exe --clean --noconfirm --distpath smoke_test_assets\packaging\dist-whisper --workpath smoke_test_assets\packaging\build-whisper OmniDictate.spec
```

Supporting code changes:

- Gemma backends are imported lazily only when a Gemma backend is selected.
- `faster_whisper`, Torch CUDA checks, video frame decoding, webcam capture,
  and Hugging Face downloads are no longer imported during baseline UI import.
- Selecting an excluded Gemma backend returns a clear unavailable-backend error
  instead of crashing the worker.
- `tools\import_boundary_test.py` protects the baseline import boundary.
- `tools\package_size_audit.py` reports bundle size and largest package
  families.

Result: passed.

Whisper-only bundle:

```text
Bundle: smoke_test_assets\packaging\dist-whisper\OmniDictate
Total: 223.1 MB (233985911 bytes)
Top entries:
216.5 MB  _internal
  6.6 MB  OmniDictate.exe
```

Largest `_internal` entries:

```text
91.9 MB  PySide6
59.3 MB  ctranslate2
20.0 MB  numpy.libs
10.5 MB  PIL
 7.1 MB  tokenizers
 5.9 MB  numpy
```

Heavy experimental stacks were absent from the Whisper-only bundle. PyAV and
Hugging Face Hub are intentionally retained because Faster-Whisper needs them
for packaged audio decode and model resolution:

```text
torch, transformers, bitsandbytes, cv2, llvmlite, scipy, onnxruntime,
torchvision, model_downloader
```

Packaged Whisper-only launch smoke:

```powershell
$p = Start-Process -FilePath (Resolve-Path 'smoke_test_assets\packaging\dist-whisper\OmniDictate\OmniDictate.exe') -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 12
$alive = -not $p.HasExited
if ($alive) { Stop-Process -Id $p.Id -Force }
```

Result: passed, `alive=True`.

Single-file no-compression Whisper-only installer command:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0-whisper-smoke' /DSourceDir='smoke_test_assets\packaging\dist-whisper\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-fast' /DCompressionMode=none /DSolidCompressionMode=no OmniDictate_Setup.iss
```

Result: passed.

- Output:
  `smoke_test_assets\packaging\installer-whisper-fast\OmniDictate_Setup_v3.0.0-whisper-smoke.exe`
- Size: 236,259,929 bytes

This proves a practical baseline release packaging path exists.

## Per-User Installer Smoke

`OmniDictate_Setup.iss` originally supported smoke-build overrides while
preserving an admin/Program Files release default:

```text
/DPrivilegesRequiredMode=lowest
/DDefaultDir='{localappdata}\OmniDictateSmoke'
/DArchitecturesInstallMode=x64compatible
```

Per-user smoke installer compile command:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0-whisper-user-smoke' /DSourceDir='smoke_test_assets\packaging\dist-whisper\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-user-smoke' /DCompressionMode=none /DSolidCompressionMode=no /DPrivilegesRequiredMode=lowest /DDefaultDir='{localappdata}\OmniDictateSmoke' /DArchitecturesInstallMode=x64compatible OmniDictate_Setup.iss
```

Result: passed.

Output:

```text
smoke_test_assets\packaging\installer-whisper-user-smoke\OmniDictate_Setup_v3.0.0-whisper-user-smoke.exe
```

Reusable smoke command:

```powershell
powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1
```

Result: passed.

The scripted smoke verified:

- Silent install into `C:\Users\kapil\AppData\Local\OmniDictateSmoke`.
- Installed `OmniDictate.exe` exists after install.
- Installed app launches and remains alive for 12 seconds.
- Silent uninstall exits successfully.
- `OmniDictate.exe`, `_internal`, and the install directory payload are removed
  after uninstall.

Logs:

```text
smoke_test_assets\packaging\installer-whisper-user-smoke\install-smoke.log
smoke_test_assets\packaging\installer-whisper-user-smoke\uninstall-smoke.log
```

Open installer work:

- Keep README, screenshots, installer version, and release notes aligned with
  the verified Whisper-only baseline before tagging.

## Packaged App Screenshot Smoke

The Whisper-only PyInstaller profile and per-user installer were rebuilt again
from clean PyInstaller work output, then exercised through the installed-app
smoke.

Commands:

```powershell
$env:OMNIDICTATE_PACKAGE_PROFILE='whisper-only'
.\venv\Scripts\pyinstaller.exe --clean --noconfirm --distpath smoke_test_assets\packaging\dist-whisper --workpath smoke_test_assets\packaging\build-whisper OmniDictate.spec
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0-whisper-user-smoke' /DSourceDir='smoke_test_assets\packaging\dist-whisper\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-user-smoke' /DCompressionMode=none /DSolidCompressionMode=no /DPrivilegesRequiredMode=lowest /DDefaultDir='{localappdata}\OmniDictateSmoke' /DArchitecturesInstallMode=x64compatible OmniDictate_Setup.iss
.\venv\Scripts\python.exe tools\packaged_app_smoke.py --screenshot smoke_test_assets\ui\packaged-whisper-first-run.png
```

Result: passed.

The smoke verified:

- Silent install of the per-user Whisper-only installer.
- Installed app launch.
- Native first-run screenshot capture using an isolated temporary `QSettings`
  app id:
  `smoke_test_assets\ui\packaged-whisper-first-run.png`.
- Temporary smoke settings registry key cleanup.
- Silent uninstall.
- Install directory removed after uninstall.

The first-run screenshot shows the expected Whisper-only baseline: Faster-
Whisper backend, Pure transcription mode, Whisper-only path, context off, and
`large-v3-turbo`.

## Release-Default Installer Path

Decision: the public Whisper-only baseline installer should default to a
per-user install. This avoids UAC friction for a desktop dictation utility,
matches the successfully smoked path, and keeps admin/Program Files available
as an explicit build override:

```text
/DPrivilegesRequiredMode=admin
/DDefaultDir='{autopf64}\OmniDictate'
/DArchitecturesInstallMode=x64
```

Current default Inno values:

```text
PrivilegesRequired=lowest
DefaultDirName={localappdata}\OmniDictate
ArchitecturesInstallIn64BitMode=x64compatible
```

Release-default compile command:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0-whisper-release-smoke' /DSourceDir='smoke_test_assets\packaging\dist-whisper\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-release-smoke' /DCompressionMode=none /DSolidCompressionMode=no OmniDictate_Setup.iss
```

Result: passed.

Output:

```text
smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe
```

Size: 236,263,090 bytes.

Release-default installer smoke command:

```powershell
powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1 -InstallerPath smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe -InstallDir "$env:LOCALAPPDATA\OmniDictate" -UseInstallerDefaults
```

Result: passed.

The smoke intentionally did not pass `/CURRENTUSER` or `/DIR`, so the installer
defaults controlled install behavior. It verified:

- Silent install to `C:\Users\kapil\AppData\Local\OmniDictate`.
- Installed app launch.
- Silent uninstall.
- `%LOCALAPPDATA%\OmniDictate` removed after uninstall.

Logs:

```text
smoke_test_assets\packaging\installer-whisper-release-smoke\install-smoke.log
smoke_test_assets\packaging\installer-whisper-release-smoke\uninstall-smoke.log
```

## Post-Alternative-STT Packaging Guard

After adding the optional Transformers ASR adapter, the Whisper-only package
profile was rebuilt to make sure experimental ASR code did not enter the
baseline release artifact.

Command:

```powershell
$env:OMNIDICTATE_PACKAGE_PROFILE='whisper-only'
.\venv\Scripts\pyinstaller.exe --clean --noconfirm --distpath smoke_test_assets\packaging\dist-whisper --workpath smoke_test_assets\packaging\build-whisper OmniDictate.spec
```

Result: passed.

Audit:

```text
Bundle: smoke_test_assets\packaging\dist-whisper\OmniDictate
Total: 223.1 MB (233989044 bytes)
```

The following experimental runtime families were absent from `_internal`.
PyAV and Hugging Face Hub are no longer part of this absence list; they are
required by the Whisper-only packaged runtime:

```text
transformers, torch, bitsandbytes, cv2, model_downloader
```

This is now release policy, not just a size optimization: the public baseline
installer must remain Whisper-only. Gemma dependencies, model weights, and
GGUF assets are source/dev or separately named experimental package material
only after their own gates pass.

The release-default installer was recompiled from this rebuilt bundle and
smoked again:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0-whisper-release-smoke' /DSourceDir='smoke_test_assets\packaging\dist-whisper\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-release-smoke' /DCompressionMode=none /DSolidCompressionMode=no OmniDictate_Setup.iss
powershell -ExecutionPolicy Bypass -File tools\installer_smoke.ps1 -InstallerPath smoke_test_assets\packaging\installer-whisper-release-smoke\OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe -InstallDir "$env:LOCALAPPDATA\OmniDictate" -UseInstallerDefaults
```

Result: passed. Rebuilt installer size: 236,263,090 bytes.
