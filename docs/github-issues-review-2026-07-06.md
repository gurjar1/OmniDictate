# GitHub Issues Review - 2026-07-06

Source reviewed: https://github.com/gurjar1/OmniDictate/issues

Open issue count at review time: 9.

## Implemented In This Slice

| Issue | User need | Change |
| --- | --- | --- |
| #27 - Option for disabling keyboard simulation | Use OmniDictate as a transcript pad without typing into other apps | Added `Type into active app` setting. When off, transcripts still appear in OmniDictate, but no keystrokes are queued. |
| #26 - Czech language support | Avoid Auto Detect switching away from Czech | Added Czech (`cs`) to the language selector. |
| #18 - Repeated "I'm sorry" after accidental quick PTT tap | Ignore very short PTT key brushes | Added `Minimum PTT hold` setting, default `250 ms`, and worker behavior that discards shorter PTT recordings before transcription. |

## Already Improved Or Partly Covered

| Issue | Current state |
| --- | --- |
| #8 - Blank Windows taskbar icon | The current app sets the application icon early and uses the packaged icon metadata. Keep this covered in packaged smoke/manual visual QA. |
| #19 - Closing does not shut down / microphone remains in use | The worker now has explicit stop completion signaling, and normal Stop no longer blocks the UI thread. Close still waits briefly so the microphone stream is released before process exit. |
| #20 - Memory leak after close | The same stop lifecycle work reduces the most likely cause: a worker/audio stream continuing after the UI closes. A real long-run memory soak is still needed before claiming the issue fully closed. |

## Deferred

| Issue | Why deferred |
| --- | --- |
| #22 - Global hotkey to start/stop dictation | Useful, but it changes global hotkey behavior and needs collision handling, UI configuration, and live Windows testing. |
| #23 - cuDNN failure on first sounds | Likely environment/runtime specific. README now explains GPU runtime requirements, but a robust fallback from GPU failure to CPU needs careful packaged testing. |
| #21 - Voxtral | Model research lane, not release-blocker polish. Needs benchmarks and packaging evidence before product exposure. |

## Verification Added

- `tools\worker_behavior_test.py` covers Transcribe Only and short PTT tap discard.
- `tools\ui_transport_state_test.py` covers Czech, Type into active app, Minimum PTT hold, and Check for Updates UI presence.
- `tools\app_updates_test.py` covers release tag parsing and update comparison without network calls.
- `tools\threading_lifecycle_test.py` guards the non-blocking stop path.
