# OmniDictate Agent Guide

This repo is in recovery mode. The last known-good public release is
`v2.0.2` at commit `7d32a12`. The local working tree contains an
uncommitted Gemma-era experiment. Do not assume the local branch is release
ready just because the UI exposes Gemma controls.

## Start Here

1. Read `docs/ai/HANDOFF.md`.
2. Read only the docs/files named by the handoff plus direct dependencies.
3. Run the cheapest relevant gate from `docs/ai/VERIFY.md` before claiming
   progress.
4. Update the durable docs when implementation or verification truth changes.

## Product Spine

The reliable product is still local Windows dictation:

- `faster-whisper` transcribes short utterances.
- VAD or push-to-talk controls recording.
- Text is typed into the active target window.
- Settings persist through `QSettings`.

Gemma, GGUF, visual context, and reasoning are experimental lanes until their
live gates pass. Preserve the Whisper-only path as the default and regression
baseline.

## Loop Principle

Every task follows this loop:

`orient -> plan -> act -> verify -> fix -> check -> record`

Do not hand off red work. If a gate fails, fix the cause and rerun from the
failed step. If the same failure repeats three times, record the blocker in
`docs/ai/HANDOFF.md` with exact command output and stop.

## Boundaries

- Do not commit or push unless the user explicitly asks.
- Do not delete the local Gemma work unless the user explicitly approves a
  reset or cleanup.
- Do not add downloaded model weights to git. Model caches are ignored.
- Do not update README or installer version as if a release is ready unless the
  release gate in `docs/ai/VERIFY.md` has passed.
- Prefer small, separately verifiable slices over broad rewrites.
