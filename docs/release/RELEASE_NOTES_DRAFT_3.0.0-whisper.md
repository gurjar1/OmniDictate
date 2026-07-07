# OmniDictate v3.0.0

## Summary

OmniDictate v3.0.0 is a Windows desktop dictation release focused on reliable
local Whisper speech-to-text. It restores the core dictation workflow, improves
the packaged installer, and adds small usability fixes from GitHub issue
feedback.

## Download

Download:

```text
OmniDictate_Setup_v3.0.0.exe
```

SHA256:

```text
3DD9CF5CD1E172D41208DDD3BDC3380A5A18BA1DDBA4BD5F3CE7FDEA2CEA10A5
```

Install it normally, then allow microphone permission if Windows asks. The app
installs per user under `%LOCALAPPDATA%\OmniDictate` and should not require
administrator access.

## What's New

- Local Whisper dictation with `large-v3-turbo` support.
- Smaller installer that downloads selected Whisper models on first use.
- Cleaner first-run Settings page for the public Windows build.
- **Check for Updates** button in Settings.
- **Transcribe Only** option by turning off active-app typing.
- Multi-language option.
- Minimum PTT hold setting to ignore accidental quick taps.
- Safer stop handling and better cleanup during shutdown.
- Better handling when OmniDictate itself is the active window.

## Fresh Windows Requirements

- Windows 10 or Windows 11, 64-bit.
- A working microphone.
- Internet access on first use so the selected Whisper model can download.
- For GPU acceleration: an NVIDIA GPU plus a working NVIDIA driver and
  CUDA/cuDNN runtime that matches this OmniDictate build. CPU mode can work but
  is slower.
- Microsoft Visual C++ Redistributable 2015-2022 x64 if Windows reports missing
  runtime DLLs.

Python, Git, and PyTorch are not required for the normal installer.

### Recommended Runtime Setup

OmniDictate shows a **Runtime** badge in the main window after the speech model
starts. Click it to open **Performance Check**. The checker says whether the app
is using GPU or CPU mode, what was detected, and which setup step to try next.

Use these official downloads only when Performance Check says GPU setup needs
attention:

1. Install or update the NVIDIA display driver from
   [NVIDIA Driver Downloads](https://www.nvidia.com/en-us/drivers/).
2. Install the CUDA runtime/toolkit version recommended by Performance Check:
   [CUDA Toolkit Archive](https://developer.nvidia.com/cuda-toolkit-archive).
3. If OmniDictate reports missing cuDNN DLLs or GPU loading still fails, install
   the cuDNN version recommended by Performance Check from
   [NVIDIA cuDNN Archive](https://developer.nvidia.com/rdp/cudnn-archive).
4. If Windows reports missing Visual C++ runtime DLLs, install
   **Microsoft Visual C++ Redistributable for Visual Studio 2015-2022 x64** from
   [Microsoft's latest supported VC++ Redistributable page](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
   The direct x64 installer link on that page is
   [vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe).

## Updating

Run the new installer normally. You can also use Settings -> **Check for
Updates** inside OmniDictate to open the latest GitHub Releases page.

## Uninstalling

Use Windows **Settings > Apps > Installed apps**, or run:

```text
%LOCALAPPDATA%\OmniDictate\unins000.exe
```

## Notes

- The app is unsigned, so Windows SmartScreen may show a warning.
- The first model load can take longer while the selected Whisper model is
  downloaded and initialized.
- If transcription is slow, click the **Runtime** badge and follow Performance
  Check.

## Technical Details

- Public package: Windows per-user Inno installer.
- Default install location: `%LOCALAPPDATA%\OmniDictate`.
- Default dictation model: `large-v3-turbo`.
- Speech runtime: Faster-Whisper through CTranslate2.
- Packaged runtime includes PyAV/FFmpeg support for audio decoding.
- Whisper model files are downloaded on demand and are not bundled inside the
  installer.
- The public installer is intentionally smaller than the old development bundle
  because it excludes downloaded model caches, local smoke-test assets, and
  developer-only runtime stacks.
