# Visual Context And UI Evidence - 2026-07-04

## Visual Context Smoke

Command:

```powershell
.\venv\Scripts\python.exe tools\visual_context_smoke.py
```

Result: passed.

The smoke generated local fixtures under `smoke_test_assets\visual_context`
and verified:

- Image attachment works and produces `VisualSource.ATTACHED_IMAGE`.
- Video attachment works with PyAV and samples two frames.
- Active-window screen capture returns a snapshot without raising.
- Full-screen capture returns a snapshot without raising.
- Webcam capture fails softly when unavailable; on this machine it returned
  one frame from the available virtual camera.

Observed output:

```text
Image attachment smoke passed: Images: visual-context-image.png
Video attachment smoke passed: frames=2 Videos: visual-context-video.mp4
Screen context smoke passed: target=active-window source=screen-active-window images=1
Screen context smoke passed: target=full-screen source=screen-full images=1
Webcam fail-soft smoke passed: source=webcam images=1
Visual context smoke passed.
```

The local camera provider emitted verbose virtual-camera diagnostic lines. They
did not fail the smoke.

## Native UI Screenshot

Command:

```powershell
.\venv\Scripts\python.exe tools\ui_smoke_test.py --platform native --screenshot smoke_test_assets\ui\qt-window-smoke-native.png
```

Result: passed.

The saved screenshot rendered readable text and the main dictation layout:

```text
smoke_test_assets\ui\qt-window-smoke-native.png
```

An earlier screenshot taken through the forced `offscreen` Qt platform showed
square glyph boxes. A standalone Qt font probe and a native-platform app
screenshot confirmed that the glyph issue was an offscreen capture artifact,
not the actual Windows render path.

`tools\ui_smoke_test.py` now supports:

- `--platform offscreen` for headless quick-gate construction smoke.
- `--platform native` for real Windows visual QA screenshots.
- `--page settings` plus backend/prompt/mode overrides for settings-page
  variant screenshots.

## Settings Page Screenshots

Commands:

```powershell
.\venv\Scripts\python.exe tools\ui_smoke_test.py --platform native --page settings --backend faster-whisper --prompt-mode pure --screenshot smoke_test_assets\ui\settings-whisper-pure.png
.\venv\Scripts\python.exe tools\ui_smoke_test.py --platform native --page settings --backend gemma-4 --prompt-mode context --gemma-audio-mode hybrid-whisper --screenshot smoke_test_assets\ui\settings-gemma-hybrid-context.png
.\venv\Scripts\python.exe tools\ui_smoke_test.py --platform native --page settings --backend gemma-gguf-server --prompt-mode context --screenshot smoke_test_assets\ui\settings-gguf-context.png
```

Result: passed.

The native Windows screenshots rendered readable settings text for the
Whisper-only, Gemma hybrid/context, and GGUF context variants:

```text
smoke_test_assets\ui\settings-whisper-pure.png
smoke_test_assets\ui\settings-gemma-hybrid-context.png
smoke_test_assets\ui\settings-gguf-context.png
```

The smoke helper temporarily applies these UI choices without saving them back
to persistent settings.

## Packaged App Screenshot

Commands:

```powershell
$env:OMNIDICTATE_PACKAGE_PROFILE='whisper-only'
.\venv\Scripts\pyinstaller.exe --clean --noconfirm --distpath smoke_test_assets\packaging\dist-whisper --workpath smoke_test_assets\packaging\build-whisper OmniDictate.spec
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' /DAppVersion='3.0.0-whisper-user-smoke' /DSourceDir='smoke_test_assets\packaging\dist-whisper\OmniDictate' /DInstallerOutputDir='smoke_test_assets\packaging\installer-whisper-user-smoke' /DCompressionMode=none /DSolidCompressionMode=no /DPrivilegesRequiredMode=lowest /DDefaultDir='{localappdata}\OmniDictateSmoke' /DArchitecturesInstallMode=x64compatible OmniDictate_Setup.iss
.\venv\Scripts\python.exe tools\packaged_app_smoke.py --screenshot smoke_test_assets\ui\packaged-whisper-first-run.png
```

Result: passed.

The packaged smoke installed the per-user Whisper-only installer, launched the
installed app with an isolated temporary `QSettings` app id, captured a native
first-run screenshot, cleaned the temporary settings key, silently uninstalled,
and verified the installed payload was removed.

Saved screenshot:

```text
smoke_test_assets\ui\packaged-whisper-first-run.png
```

The verified first-run screenshot shows the expected baseline release state:
`Backend: Faster-Whisper`, `Mode: Pure transcription`, `Path: Whisper only`,
`Context: off`, and `Model: large-v3-turbo`.

## Quick Gate

Command:

```powershell
powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1
```

Result: passed after adding visual context smoke to the quick gate.
