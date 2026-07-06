# OmniDictate v3.0.0 Post-Release Issue Closeout

Run this only after the `v3.0.0` GitHub release is published and the final
installer asset is visible on the release page.

## Close After Release

### Issue #27: Option for disabling keyboard simulation

Reason: v3.0.0 adds **Type into active app**. Turning it off keeps transcripts
inside OmniDictate without sending keystrokes to other apps.

Comment:

```text
Released in v3.0.0. There is now a "Type into active app" setting, so OmniDictate can be used in Transcribe Only mode without keyboard simulation.

Thanks for the suggestion. This was a good fit for the recovery release because it also gives users a safer way to test dictation before sending text into another app.
```

Command:

```powershell
gh issue comment 27 --repo gurjar1/OmniDictate --body "Released in v3.0.0. There is now a \"Type into active app\" setting, so OmniDictate can be used in Transcribe Only mode without keyboard simulation.`n`nThanks for the suggestion. This was a good fit for the recovery release because it also gives users a safer way to test dictation before sending text into another app."
gh issue close 27 --repo gurjar1/OmniDictate --reason completed
```

### Issue #26: Czech language

Reason: v3.0.0 adds Czech to the preferred language selector.

Comment:

```text
Released in v3.0.0. Czech is now available in the preferred language selector, alongside Auto Detect.

Thanks for reporting this. Auto Detect can be inconvenient for regular Czech dictation, so a fixed language option makes sense here.
```

Command:

```powershell
gh issue comment 26 --repo gurjar1/OmniDictate --body "Released in v3.0.0. Czech is now available in the preferred language selector, alongside Auto Detect.`n`nThanks for reporting this. Auto Detect can be inconvenient for regular Czech dictation, so a fixed language option makes sense here."
gh issue close 26 --repo gurjar1/OmniDictate --reason completed
```

### Issue #18: Accidental short PTT tap can produce repeated apology text

Reason: v3.0.0 adds **Minimum PTT hold**, which ignores very short PTT taps
before they can queue transcription.

Comment:

```text
Released in v3.0.0. OmniDictate now has a "Minimum PTT hold" setting, and very short PTT taps are ignored instead of being sent for transcription.

This should reduce the accidental quick-tap path that could produce unwanted repeated text. If you still see this with normal-length PTT recordings, please open a new issue with the model, microphone, and phrase details.
```

Command:

```powershell
gh issue comment 18 --repo gurjar1/OmniDictate --body "Released in v3.0.0. OmniDictate now has a \"Minimum PTT hold\" setting, and very short PTT taps are ignored instead of being sent for transcription.`n`nThis should reduce the accidental quick-tap path that could produce unwanted repeated text. If you still see this with normal-length PTT recordings, please open a new issue with the model, microphone, and phrase details."
gh issue close 18 --repo gurjar1/OmniDictate --reason completed
```

## Do Not Close Yet

- #19 close/shutdown behavior: v3.0.0 improves async stop and cleanup, but this
  still deserves real post-release confirmation before closing.
- #20 memory leak: related stability work improved cleanup, but no long soak
  evidence is recorded yet.
- #22 global start/stop hotkey: not implemented in this release.
- #23 cuDNN environment failure: not fully solved; still depends on local GPU
  runtime setup.
- #21 model request: research only, not a v3.0.0 user feature.
- #8 taskbar icon: do not close unless packaged visual QA confirms the public
  installed app/taskbar behavior on a clean machine.
