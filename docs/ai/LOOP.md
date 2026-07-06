# OmniDictate Loop

The loop is the engineering heartbeat for this repo:

`orient -> plan -> act -> verify -> fix -> check -> record`

## Orient

Read `docs/ai/HANDOFF.md`, then only the named files and direct dependencies.
Do not reread the entire repo unless the handoff is stale or contradictory.

## Plan

Pick the smallest checkpoint that proves something useful. For this project,
proof usually means a smoke test, processor compatibility check, live sample
transcription, packaging launch, or visual/manual checklist with exact steps.

## Act

Keep changes scoped. Preserve Whisper parity. Do not mix a UI redesign,
backend rewrite, dependency bump, and packaging change in one checkpoint.

## Verify

Run `tools\verify_local.ps1` for quick checks. Run the focused live gate from
`docs/ai/VERIFY.md` when touching model/audio/runtime behavior.

## Fix

Fix the first failing gate before continuing. After three failed attempts on
the same blocker, record the exact blocker in `HANDOFF.md`.

## Check

Review your own diff as if it came from another agent. Confirm docs do not
overstate what passed.

## Record

Update `HANDOFF.md`, `STATE.md`, `DECISIONS.md`, or the phase checklist only
when durable truth changes.
