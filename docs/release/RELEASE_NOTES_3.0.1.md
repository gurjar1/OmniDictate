# OmniDictate v3.0.1

## Summary

OmniDictate v3.0.1 is a focused stability and usability patch for the
Whisper-only Windows release.

## What's Changed

- Added a **Runtime** status badge in the main window.
- Added a **Performance Check** dialog that explains whether OmniDictate is
  using GPU or CPU mode and gives step-by-step setup guidance.
- Added official setup links for NVIDIA driver, CUDA, cuDNN, and Microsoft
  Visual C++ Redistributable when GPU/runtime setup needs attention.
- Improved Whisper runtime diagnostics for GPU ready, GPU compatibility, CPU
  fallback, and model-load errors.
- Bumped the default-settings migration so existing installs are repaired to:
  `large-v3-turbo`, English, and active-app typing enabled.
- Updated README troubleshooting so users start from the in-app Performance
  Check instead of guessing CUDA/cuDNN versions.

## Install

Download and run:

```text
OmniDictate_Setup_v3.0.1.exe
```

SHA256:

```text
A8A3074396E7C03CBF2F724EF152799C7AB358FE4268C14CF2A125BB8A7ED9FD
```

The installer is per-user and installs under:

```text
%LOCALAPPDATA%\OmniDictate
```

## Notes

- The app is unsigned, so Windows SmartScreen may show a warning.
- Whisper model files are downloaded on first use and are not bundled inside
  the installer.
- Python, Git, and PyTorch are not required for normal use.
