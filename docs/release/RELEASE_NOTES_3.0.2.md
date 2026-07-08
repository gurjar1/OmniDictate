# OmniDictate v3.0.2

## Summary

OmniDictate v3.0.2 improves long push-to-talk dictation reliability.

## What's Changed

- Push-to-talk now uses short pauses as phrase breaks while the key is still
  held.
- Completed PTT phrases can be queued for transcription before final key
  release, while OmniDictate keeps listening for the next phrase.
- The old 25-second VAD utterance cap no longer cuts normal PTT recordings.
- Leading silence in PTT mode is discarded instead of being sent as junk audio.
- If transcription falls behind, OmniDictate preserves already queued phrases
  and reports that the queue is full instead of silently dropping older text.
- Minimum PTT hold still protects against accidental short key taps.

## Install

Download and run:

```text
OmniDictate_Setup_v3.0.2.exe
```

SHA256:

```text
AC1D403DFA35E97AAFAB68C2A0E0AD00208456A6EE71611BB6FBCD28BD29627F
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
