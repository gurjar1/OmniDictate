# OmniDictate v3.0.3

## Summary

OmniDictate v3.0.3 adds automatic update notifications.

## What's Changed

- OmniDictate can now check GitHub Releases once per day when the app opens.
- The daily check is enabled by default and can be turned off in Settings.
- If a newer version is available, OmniDictate asks whether to open the GitHub
  release page.
- The app does not download or run installers automatically.
- Manual **Check for Updates** remains available in Settings.
- Release smoke tests disable the background update check so packaging
  verification stays independent of network timing.

## Install

Download and run:

```text
OmniDictate_Setup_v3.0.3.exe
```

SHA256:

```text
057F1A9E2BF6866C07AE2120468CE3EB1349EEF86C6E45CC6E3C2B5F3F78EB06
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
