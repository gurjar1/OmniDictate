# OmniDictate v3.0.0 Release Scope Decisions

Date: 2026-07-05
Status: ready for publication

This file is the structured authority for deciding whether remaining
release-scope gates are proven, still pending, or explicitly scoped out before
publishing the Whisper-only baseline. Do not use prose elsewhere to move a
gate out of scope without updating this table and rerunning
`tools\release_scope_decision_audit.py`.

Allowed statuses:

- `pending`: the gate remains a publication blocker.
- `proven`: the gate has a passing report from its one-command gate runner.
- `scoped-out`: the user explicitly moved the gate out of the public
  Whisper-only release scope and the release notes/checklist were updated.

For a `scoped-out` row, `User authorization` must include
`User authorized ... on YYYY-MM-DD`, and `Release note/checklist update` must
include `Updated ... on YYYY-MM-DD`. Vague approval text is not enough.

| Gate key | Release scope status | Required evidence | Current evidence | User authorization | Release note/checklist update |
| --- | --- | --- | --- | --- | --- |
| `physical-microphone` | `proven` | `smoke_test_assets\microphone\physical-gate-report.json` with `status: passed` | Passed on 2026-07-05: saved prompted WAV passed, VAD matched 6/8 words, PTT matched 8/8 words, and `tools\microphone_gate_report_audit.py` passed | Not applicable for proven evidence | Updated release notes and checklist on 2026-07-05 to state that the physical microphone gate passed |
| `gemma-e4b-live` | `scoped-out` | `smoke_test_assets\gemma-e4b-gate-report.json` with `status: passed` | Runtime preflight passed, local E4B weights are missing, no E4B live generation report exists; excluded from the public Whisper-only installer and release claims | User authorized scoping out Gemma E4B for v3.0.0 Whisper-only on 2026-07-05 | Updated release notes and checklist on 2026-07-05 to state that Gemma E4B is excluded from the baseline release and remains experimental/unverified |
| `gguf-real-server` | `scoped-out` | `smoke_test_assets\gguf\real-server-gate-report.json` with `status: passed` | Mock contract/probe tests pass, no named real local server report exists; excluded from the public Whisper-only installer and release claims | User authorized scoping out real GGUF server support for v3.0.0 Whisper-only on 2026-07-05 | Updated release notes and checklist on 2026-07-05 to state that real GGUF server support is excluded from the baseline release and remains experimental/unverified |

Current decision: publication is ready from the local gate perspective. The
physical microphone gate is `proven`; Gemma E4B and real GGUF server support
are explicitly scoped out of the public Whisper-only `v3.0.0` release.
