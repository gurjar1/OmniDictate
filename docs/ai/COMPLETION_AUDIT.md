# OmniDictate Goal Completion Audit

Date: 2026-07-05
Status: release objective locally ready; future experimental gates remain scoped out

This audit maps the original recovery objective to current evidence. Treat
uncertain or indirect proof as incomplete.

## Requirement Status

| Requirement | Evidence | Status |
| --- | --- | --- |
| Understand the successful `v2.0.2` baseline | `docs/ai/STATE.md`, `docs/ai/HANDOFF.md`, current git state at `7d32a12` | Proven |
| Compare local Gemma-era work to the known-good baseline | `docs/ai/STATE.md`, `docs/ai/DECISIONS.md`, `docs/implementation-plans-and-checklists/phase-3-gemma-recovery.md` | Proven |
| Decide whether the Gemma direction is salvageable | D002, D003, R2 evidence: E2B hybrid/context and native-audio smokes passed; E4B runtime preflight passed but local weights are missing | Partially proven |
| Preserve Whisper as the stable product path | D001, D008, D008A, whisper-only package profile, import-boundary test, release checklist | Proven |
| Review current STT model landscape with web research | `docs/research/STT_MODEL_RESEARCH_2026.md` plus 2026-07-05 refresh notes below | Proven for planning, not exhaustive forever |
| Include better STT models if justified | `TransformersASRBackend`, `tools\alternative_stt_adapter_test.py`, `tools\alternative_stt_smoke.py`, `tools\stt_adapter_benchmark.py`; Moonshine-tiny met the synthetic latency bar but still lacks real mic and packaging promotion evidence | Proven decision: keep adapter experimental |
| Understand features and UI/UX | `docs/specs/PRODUCT_SPEC.md`, `docs/ai/STATE.md`, visual/UI evidence | Proven |
| Create agent/AI/spec/test/acceptance docs | `AGENTS.md`, `docs/ai/*`, `docs/specs/PRODUCT_SPEC.md`, `docs/ai/VERIFY.md`, phase checklist, release checklist | Proven |
| Implement loop principle | `AGENTS.md`, `docs/ai/LOOP.md`, `tools\verify_local.ps1`, handoff update pattern | Proven |
| Complete testing with minimum human intervention | Quick gate, synthetic/live typing, package/installer smokes, visual context smoke | Partially proven |
| Verify physical microphone behavior | Physical microphone gate passed on 2026-07-05: prompted saved WAV, VAD, PTT, and report audit passed | Proven |
| Verify live Gemma E4B | Runtime preflight passed, but local E4B weights are missing and no E4B generation smoke has passed | Incomplete |
| Verify real GGUF server route | Mock contract passed; real server not tested | Incomplete |
| Final release readiness | Final public `OmniDictate_Setup_v3.0.0.exe` artifact gate passed; README/package wording is aligned; `tools\release_readiness_audit.py` protects policy claims; artifact manifest records the final artifact; `docs\release\RELEASE_SCOPE_DECISIONS_3.0.0.md` records physical microphone as proven and Gemma E4B / real GGUF as scoped out for this Whisper-only release. GitHub preflight is ready; publication is now a user-owned GitHub action. | Proven |

## Objective Evidence Matrix

Use this matrix as the proof standard before changing the goal status. A row
is complete only when the listed authority proves the proof standard; green
adjacent tests or plausible implementation intent are not enough.

| Objective requirement | Proof standard | Authoritative evidence | Current decision | Closure condition |
| --- | --- | --- | --- | --- |
| Verify the known-good `v2.0.2` baseline | Git state and docs identify `v2.0.2`/`7d32a12` as the public baseline and explain which behavior must be preserved | `git status --short --branch`, `docs/ai/STATE.md`, `docs/ai/HANDOFF.md` | Complete | Reopen only if the remote baseline/tag changes or local history is rewritten |
| Analyze whether local Gemma-era direction was right | Architecture, decisions, and live evidence distinguish salvageable paths from experimental paths | `docs/ai/DECISIONS.md`, `docs/ai/STATE.md`, `docs/evidence/gemma-transformers-live-2026-07-04.md`, `docs/evidence/gemma-e4b-preflight-2026-07-05.md` | Partially complete | Close only after E4B is either live-tested or explicitly scoped out |
| Preserve and test Whisper features | Whisper backend, worker behavior, hotkeys, typing guard, package/import boundaries, installer path, and physical microphone path pass repeatable checks | `tools/verify_local.ps1`, `tools/verify_whisper.ps1 -Model large-v3-turbo`, worker/hotkey/import tests, final artifact reports, physical microphone gate report | Complete for v3.0.0 Whisper-only scope | Reopen if a release-scope gate or final artifact report is invalidated |
| Understand UI/UX and product behavior | Product spec and screenshots capture actual user workflows and do not market unverified paths | `docs/specs/PRODUCT_SPEC.md`, native screenshots in `smoke_test_assets/ui`, release notes/checklist | Complete for documented UI | Reopen if UI defaults or visible model labels change |
| Review current STT model landscape | Research doc cites live primary sources, separates candidate lanes, and records promotion criteria | `docs/research/STT_MODEL_RESEARCH_2026.md`, D010, D013, release-readiness audit | Complete for 2026-07-05 planning | Refresh before promoting any new ASR model or after meaningful leaderboard/model changes |
| Include better STT models only if justified | Adapter exists, benchmark evidence exists, and promotion remains blocked until real microphone and package/runtime proof pass | `TransformersASRBackend`, `tools/stt_adapter_benchmark.py`, Moonshine benchmark report, product spec acceptance criteria | Complete decision: keep experimental | Close promotion only after physical snippets and release UI approval pass |
| Create docs for agents, AI, specs, tests, and acceptance | Canonical docs exist and audits require key markers | `AGENTS.md`, `docs/ai/*`, `docs/specs/PRODUCT_SPEC.md`, phase/release checklists, `tools/release_readiness_audit.py` | Complete | Reopen when implementation truth changes without matching docs |
| Implement looping principle | Loop docs and verification cadence exist, and handoff names exact next actions | `docs/ai/LOOP.md`, `docs/ai/HANDOFF.md`, `docs/ai/VERIFY.md`, `tools/verify_local.ps1` | Complete | Reopen if handoff/verify docs become stale |
| Complete testing with minimum human intervention | Non-interactive quick gate covers compile, core behavior, import/package boundaries, mock/server contracts, audits, and UI smoke; remaining model/server lanes are scoped out for this release | `powershell -ExecutionPolicy Bypass -File tools\verify_local.ps1`, release scope decisions, physical microphone gate report | Complete for v3.0.0 Whisper-only scope | Reopen when Gemma/GGUF are moved back into public release scope |
| Close physical microphone behavior | Real microphone opens, prompted speech has healthy levels, saved-WAV transcript matches expected phrase, VAD and PTT both pass, and report audit passes | `tools/physical_microphone_gate.py`, `tools/microphone_gate_report_audit.py`, `smoke_test_assets/microphone/physical-gate-report.json` | Complete | Reopen only if microphone evidence is invalidated |
| Close live Gemma E4B | Local E4B safetensors exist, hybrid E4B smoke passes with visual context, and report audit passes | `tools/gemma_e4b_gate.py`, `tools/gemma_e4b_gate_report_audit.py`, `smoke_test_assets/gemma-e4b-gate-report.json` | Incomplete | Provide local E4B weights and pass the one-command gate |
| Close real GGUF route | Named non-mock server passes direct probe, full backend smoke, and report audit without raw audio | `tools/gguf_real_server_gate.py`, `tools/gguf_gate_report_audit.py`, `smoke_test_assets/gguf/real-server-gate-report.json` | Incomplete | Start a real OpenAI-compatible multimodal server and pass the one-command gate |
| Publish or prepare final release | Final artifact is built/audited, publication blocker report is current, release-scope decisions are structured, and release notes match the artifact and scope | `tools/final_public_release_gate.py`, `tools/publication_blocker_audit.py`, `tools/release_scope_decision_audit.py`, artifact manifest, release checklist/runbook | Ready for user-owned GitHub publication | Create the tag/release only after final human review of release notes and installer path |

## Current Blocking External Gates

The public Whisper-only release is no longer blocked by the physical microphone gate.
Gemma E4B and real GGUF remain documented future technical gates but are scoped
out of this release by user authorization on 2026-07-05.

These future gates require user action, hardware, model weights, or a running
local service if they are brought back into release scope:

To rehearse the remaining gate commands without opening devices, loading E4B,
contacting a GGUF server, or building artifacts:

```powershell
.\venv\Scripts\python.exe tools\external_gate_orchestrator.py --report-json smoke_test_assets\external-gates-dry-run.json
```

Add `--microphone-device <numeric sounddevice input index>` to the orchestrator
when the physical microphone gate should use a non-default input. Use a device
display name only when the inventory shows it is unique.

1. Physical microphone phrase-match VAD/PTT:

   Preparation run-card:

   ```powershell
   .\venv\Scripts\python.exe tools\physical_microphone_run_card.py --report-json smoke_test_assets\microphone\physical-gate-dry-run.json
   ```

   Gate command using the saved audio-device inventory recommendation:

   ```powershell
   .\venv\Scripts\python.exe tools\physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --report-json smoke_test_assets\microphone\physical-gate-report.json
   ```

   The run-card prints the phrase, device, timing, pass rule, and evidence
   paths before the gate runs the prompted capture diagnostic, saved-WAV
   revalidation, guided VAD/PTT live loop, and report audit internally.

2. Gemma E4B live weights (scoped out for `v3.0.0` Whisper-only):

   ```powershell
   .\venv\Scripts\python.exe tools\gemma_e4b_gate.py --model google/gemma-4-E4B-it --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gemma-e4b-gate-report.json
   ```

   This one command runs local-weight preflight, hybrid E4B live smoke, and
   report audit after weights are available locally.

3. Real GGUF server (scoped out for `v3.0.0` Whisper-only):

   Start a named OpenAI-compatible local server such as llama.cpp or LM Studio
   with a multimodal model and run:

   ```powershell
   .\venv\Scripts\python.exe tools\gguf_real_server_gate.py --url http://127.0.0.1:8080/v1 --server-implementation "LM Studio" --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --report-json smoke_test_assets\gguf\real-server-gate-report.json
   ```

   Replace `"LM Studio"` with the named real server in use.

## Completion Decision

The release-preparation goal is locally ready for publication: the final public
artifact is built/audited, the physical microphone phrase-match gate is proven,
and E4B plus real GGUF are scoped out of the public Whisper-only release. E4B
and real GGUF remain future experimental work unless they are reintroduced into
release scope.

Do not mark the goal complete until every incomplete row above is either
closed with current evidence or explicitly moved out of release scope by the
user.
