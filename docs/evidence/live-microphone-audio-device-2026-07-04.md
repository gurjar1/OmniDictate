# Live Microphone Evidence - 2026-07-04

## Command

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode both --timeout 28
```

## Result

Result: partially verified after microphone permission was granted.

The script found a default input device:

```text
Default audio devices: [1, 3]
Default input: Microphone (Realtek(R) Audio)
```

OmniDictate loaded the Whisper model, opened the Realtek microphone, started
VAD recording, queued an utterance, and transcribed it:

```text
Status: Whisper model 'tiny' loaded.
Status: Using device: Microphone (Realtek(R) Audio)
Status: Listening...
Starting VAD microphone smoke.
Status: Recording (VAD)...
Status: Queued utterance for transcription...
Status: Transcribing...
Transcript: We're open to the world.
Status: Listening...
```

The phrase assertion did not pass:

```text
Expected: hello world this is a simple speech test
Actual:   We're open to the world.
Matched 1/8 expected words (12%).
```

Because the command used `--mode both`, PTT was not reached after the VAD
phrase-match failure.

The original run then repeatedly printed the same mismatch lines until it was
manually stopped with Ctrl+C:

```text
Expected: hello world this is a simple speech test
Actual:   We're open to the world.
Matched 1/8 expected words (12%).
```

The old interrupt path ended with a `KeyboardInterrupt` traceback from
`_wait_for_transcript`. The smoke tool had a bug where it repeatedly rechecked
the same mismatched transcript instead of producing a bounded failure. That
has been fixed: the tool now treats one non-empty transcript per mode as the
default evidence attempt, tracks the best match, and fails promptly with a
single summary when the phrase does not match. `--max-transcripts 0` restores
the wait-until-timeout behavior, and higher values allow a bounded retry
count. The tool also handles Ctrl+C as a clean user interrupt instead of
printing a traceback. It also has a diagnostic mode:

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode vad --timeout 28 --capture-only
```

## Interpretation

The old device-open blocker is resolved on this machine after granting
microphone permission. The remaining R1 gate is quality and loop behavior:
physical VAD captures and transcribes, but the expected phrase did not match
with the `tiny` model, and physical PTT still needs a passing run.

## User Rerun - 2026-07-05

Command:

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode both --timeout 28
```

Result: reproduced the same post-permission state. The Realtek microphone was
selected, Whisper `tiny` loaded, VAD captured one utterance, and the transcript
was again:

```text
We're open to the world.
```

The expected phrase was still:

```text
hello world this is a simple speech test
```

The match remained `1/8` words, or `12%`. The script then repeated the same
mismatch lines until the user stopped it with Ctrl+C, confirming why the
bounded retry/reporting fix is required for unattended gate runs. This rerun is
valid evidence that the microphone permission/device-open issue is no longer
the blocker, but it does not close the release gate because VAD phrase-match
failed and PTT was not reached.

Recommended next runs:

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode vad --timeout 28 --capture-only
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model large-v3-turbo --mode both --timeout 40 --manual --countdown 3 --max-transcripts 1 --report-json smoke_test_assets\microphone\live-loop-large-v3-turbo-report.json
```

## Follow-up Diagnostic

Command:

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model tiny --mode vad --timeout 16 --capture-only
```

Result: failed to capture a new transcript during the short automated run, but
the smoke exited cleanly instead of repeating the previous transcript:

```text
Default input: Microphone (Realtek(R) Audio)
Status: Whisper model 'tiny' loaded.
Status: Using device: Microphone (Realtek(R) Audio)
Status: Listening...
Starting VAD microphone smoke.
Status: Stopping...
Status: Idle
AssertionError: Timed out waiting for any transcript from physical microphone audio.
```

This keeps the physical microphone phrase/capture gate open. It also confirms
the smoke-loop fix: no stale transcript was rechecked indefinitely.

## Capture-Level Diagnostic

Added `tools\microphone_capture_diagnostic.py` to separate device audio
quality from VAD/PTT loop behavior. The tool records a fixed-duration physical
microphone sample, saves a PCM WAV, reports duration/RMS/peak/active/clipping
stats, and can optionally transcribe that exact saved sample with Whisper.

Strict quiet-room command:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 3 --output smoke_test_assets\microphone\diagnostic-noninteractive.wav
```

Result: failed as designed because the Realtek input was essentially silent
during the non-interactive run:

```text
Default audio devices: [1, 3]
Default input: Microphone (Realtek(R) Audio)
Recording 3.0s at 16000 Hz...
Saved WAV: D:\OmniDictate - GUI\smoke_test_assets\microphone\diagnostic-noninteractive.wav
Audio stats: duration=3.00s rms=0.00021 peak=0.00119 active=0% clipping=0.00%
AssertionError: Captured audio peak is extremely low; microphone input may be muted or silent.
```

Evidence-only quiet baseline command:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 3 --allow-low-level --output smoke_test_assets\microphone\diagnostic-quiet-baseline.wav
```

Result: passed in collection mode and saved a quiet baseline WAV:

```text
Default audio devices: [1, 3]
Default input: Microphone (Realtek(R) Audio)
Recording 3.0s at 16000 Hz...
Saved WAV: D:\OmniDictate - GUI\smoke_test_assets\microphone\diagnostic-quiet-baseline.wav
Audio stats: duration=3.00s rms=0.00022 peak=0.00101 active=0% clipping=0.00%
Microphone capture diagnostic passed.
```

Saved-WAV revalidation command:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --input smoke_test_assets\microphone\diagnostic-quiet-baseline.wav --allow-low-level --report-json smoke_test_assets\microphone\diagnostic-quiet-baseline-report.json
```

Result: passed in collection mode. The saved quiet WAV was reloaded without
opening the microphone, stats were recomputed, and a JSON report was written:

```text
Audio stats: duration=3.00s rms=0.00020 peak=0.00098 active=0% clipping=0.00%
Wrote report: D:\OmniDictate - GUI\smoke_test_assets\microphone\diagnostic-quiet-baseline-report.json
```

This gives agents a repeatable post-capture verification path. Once a human
records the spoken phrase, the same `--input ... --model large-v3-turbo`
path can re-check the saved WAV transcript without requiring another live
microphone capture.

The recorder now supports a guided human-capture path:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 7 --prompt --countdown 3 --model large-v3-turbo --output smoke_test_assets\microphone\spoken-phrase-large-v3-turbo.wav
```

With `--prompt`, it prints the exact phrase to speak, waits for the countdown,
then starts recording. JSON reports also include `prompted` and `expected`
fields so saved evidence can distinguish guided human captures from quiet
baseline/device-only captures.

The VAD/PTT loop smoke also supports guided manual prompts and a JSON report
for pass, failure, or user interruption:

```powershell
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model large-v3-turbo --mode both --timeout 40 --manual --countdown 3 --max-transcripts 1 --report-json smoke_test_assets\microphone\live-loop-large-v3-turbo-report.json
```

If Windows has multiple input devices or the default input changes, append
`--device <numeric sounddevice input index>`. Use a device display name only
when the inventory shows it is unique. The smoke sets that input as the process
default before `DictationWorker` opens the stream and records the selected
device in the JSON report.

## Physical Gate Attempt - 2026-07-05

Command:

```powershell
.\venv\Scripts\python.exe tools\physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --report-json smoke_test_assets\microphone\physical-gate-report.json
```

Result: the saved-WAV capture, saved-WAV transcription, and VAD live-loop
portion passed on device `1`.

```text
Transcript: hello world this is a sample speech test
Expected: hello world this is a simple speech test
Matched 7/8 expected words (88%).
VAD microphone smoke passed: hello world this is a sample speech test
```

The PTT portion timed out before producing any transcript. The failure was in
the smoke tooling, not in the saved microphone capture: `live_microphone_smoke`
held synthetic PTT while sleeping, which prevented the Qt audio-check timer
from processing microphone chunks during the PTT window. The tool now pumps Qt
events during the synthetic PTT hold.

Remaining human rerun:

```powershell
.\venv\Scripts\python.exe tools\physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --reuse-capture --report-json smoke_test_assets\microphone\physical-gate-report.json
```

This preserves the already-passing saved WAV evidence and repeats only the live
VAD/PTT loop plus final report audit.

The loop report records model, mode, expected phrase, per-mode passing results,
all worker transcripts, statuses, worker errors, `device`, `max_transcripts`,
`outcome`, `failed_mode`, and failure text. A failed VAD attempt like the user's
permission-granted run therefore becomes durable evidence without requiring a
Ctrl+C transcript scrape, but it still does not close the physical mic gate
unless both VAD and PTT pass the phrase threshold.

Interpretation: the input device opens, but this non-interactive capture did
not receive usable speech-level audio. The next physical gate should first run
the diagnostic while a human speaks the expected phrase, ideally with
`--model large-v3-turbo`, then rerun the VAD/PTT loop smoke after the saved
WAV has healthy peak/RMS and a matching transcript.

Recommended next physical command:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --list-devices --report-json smoke_test_assets\microphone\audio-device-inventory.json
```

```powershell
.\venv\Scripts\python.exe tools\physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --report-json smoke_test_assets\microphone\physical-gate-report.json
```

Use the numeric `--device` index from the latest
`audio-device-inventory.json` if the default input is not the intended
microphone. The runner now passes that same device to both physical capture and
the live VAD/PTT loop; saved-WAV revalidation remains file-based and does not
reopen the microphone. The revalidation report stores the original capture
device as `device`, and the final report audit rejects a capture/live-loop
device mismatch when both reports declare one. The current inventory report
recommends numeric `--device 1` and warns about duplicate input names, so
numeric selection is safer than a repeated display name on this machine.

The runner executes these lower-level evidence commands internally:

```powershell
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --duration 7 --prompt --countdown 3 --model large-v3-turbo --output smoke_test_assets\microphone\spoken-phrase-large-v3-turbo.wav
.\venv\Scripts\python.exe tools\microphone_capture_diagnostic.py --input smoke_test_assets\microphone\spoken-phrase-large-v3-turbo.wav --model large-v3-turbo --report-json smoke_test_assets\microphone\spoken-phrase-large-v3-turbo-report.json
.\venv\Scripts\python.exe tools\live_microphone_smoke.py --model large-v3-turbo --mode both --timeout 40 --manual --countdown 3 --max-transcripts 1 --report-json smoke_test_assets\microphone\live-loop-large-v3-turbo-report.json
```

If the saved spoken WAV and its capture report already passed but the VAD/PTT
loop needs another attempt, append `--reuse-capture` to the physical gate
command. That skips the prompted capture/revalidation steps and reruns only
the live loop plus final report audit. It fails before opening the microphone
if `spoken-phrase-large-v3-turbo.wav` or
`spoken-phrase-large-v3-turbo-report.json` is missing.
