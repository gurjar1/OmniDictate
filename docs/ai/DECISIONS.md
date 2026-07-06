# Decisions

## D001 - Preserve Whisper as the Default Spine

Keep `faster-whisper` as the default user path and regression baseline. Gemma
features must not make the existing dictation workflow slower, harder to start,
or less reliable.

## D002 - Salvage the Gemma Branch, Do Not Reset Yet

The local branch is directionally salvageable. It compiles, the route smoke
tests pass, the UI instantiates, and the Gemma 4 processor accepts the current
audio/image prompt assembly. Do not discard it unless a later live gate proves
the architecture is not recoverable.

## D003 - Keep Gemma Native Audio Experimental

Official Gemma 4 docs support ASR and speech translation on E2B/E4B, but the
local app has not yet passed a live model-generation gate. Keep native Gemma
audio behind experimental wording and use hybrid Whisper-first mode as the
recommended Gemma path.

## D004 - Treat GGUF as External Server Refinement

The current local code does not embed llama.cpp. The GGUF route means:
Whisper drafts audio locally, then an OpenAI-compatible local server refines
text plus optional images. Do not promise built-in GGUF model download or raw
audio GGUF inference until implemented and verified.

## D005 - Ignore Model Caches

Downloaded model caches and heavyweight model artifacts must stay out of git.
This repo should contain source, docs, and small smoke fixtures only.

## D006 - Use OmniDictate-Specific Loop Docs

The copied loop-principle docs referenced another project. The canonical agent
workflow is now `AGENTS.md`, `docs/ai/HANDOFF.md`, and
`docs/ai/VERIFY.md`.

## D007 - Do Not Treat The Current Split Installer As Release-Ready

PyInstaller and disk-spanned Inno compilation now pass locally, but the bundled
artifact is about 4.8 GB and installer install/uninstall has not been smoked.
Before release, reduce the packaged dependency set or make Gemma-heavy runtime
pieces optional/downloaded after install.

## D008 - Ship Whisper-Only As The Practical Baseline Package

The practical release path is a Whisper-only PyInstaller profile that keeps
Gemma dependencies optional. The current final public build is a 322,225,944
byte app bundle and a 324,505,897 byte single-file Inno installer. PyAV and
Hugging Face Hub are part of the Whisper-only runtime because Faster-Whisper
needs them. The public PyInstaller build now bakes in the `whisper-only`
runtime profile, and the packaged runtime smoke loaded `large-v3-turbo` on
CUDA float16 on the release test machine. Gemma and alternative STT runtimes
remain available in source/full experimental environments, but a Gemma-enabled
binary should be a separate explicit package or an explicit opt-in post-install
download flow, never part of the baseline installer.

## D008A - Do Not Bundle Gemma In The Baseline Installer

The public baseline installer must remain Whisper-only. Gemma dependencies,
local model weights, Transformers/Torch stacks, and GGUF server assets must not
be silently bundled into the default installer. Gemma can ship only as source
code/dev functionality or as a separately named experimental package after its
own live gates pass. A future post-install download flow is allowed only if it
requires an explicit user action, labels disk/GPU requirements, and keeps
model caches outside git and outside the baseline installer.

## D009 - Use Per-User Install As The Whisper Baseline Release Default

Use `PrivilegesRequired=lowest`, `{localappdata}\OmniDictate`, and
`x64compatible` as the default Inno behavior for the Whisper-only baseline
installer. This release-default path has passed compile, install, launch,
uninstall, and cleanup smoke without UAC. Keep admin/Program Files available as
an explicit override for special builds.

## D010 - Keep Alternative STT Behind An Experimental Adapter

Moonshine-tiny works through a lazy Transformers ASR adapter. The first live
smoke was slower than Whisper, but a repeated synthetic benchmark later met
the latency promotion bar: Whisper `large-v3-turbo` median `0.47s`,
Moonshine-tiny median `0.31s`, both with 100% word match, decision
`candidate-meets-latency-promotion-bar`; package/import boundary checks and
synthetic command-routing checks passed, but `promotion_ready: false`. Keep
the adapter and benchmark tooling for experiments, but do not add it to the
default UI or Whisper-only release package until the remaining promotion
criteria pass: real microphone snippets, release UI approval, Windows
warnings, and a recorded keep/defer/reject decision.

## D011 - Use v3.0.0 For The Public Whisper-Only Baseline

Use `v3.0.0` as the recommended public GitHub tag and
`OmniDictate_Setup_v3.0.0.exe` as the recommended public installer name after
the remaining release gates pass. Keep suffixes such as
`3.0.0-whisper-release-smoke` for local smoke artifacts only. This avoids
publishing an awkward pre-release-style package name while keeping the public
release clearly scoped as a Whisper-only baseline, not a Gemma-enabled release.

## D012 - Keep Release Docs Trackable While Ignoring Artifacts

Ignore only the root `/release/` artifact directory, not every directory named
`release`. Release coordination docs under `docs/release/` must stay visible
to git and must be protected by `tools\release_readiness_audit.py`.

## D013 - Sort New ASR Models Into Evaluation Lanes

The 2026-07-05 live ASR refresh found useful candidates, but no model should
be promoted directly into the default UI just because it is newer than
Whisper. Sort candidates into low-latency dictation, multilingual/dialect,
realtime/heavy runtime, or rich-transcript lanes. Only the low-latency
dictation lane competes directly with the current global-hotkey
`large-v3-turbo` path; rich-transcript models such as IBM Granite Speech,
VibeVoice-ASR, Cohere Transcribe, and MOSS-Transcribe belong to future
meeting-note or structured-output work unless the product scope changes.

## D014 - Prefer Manual Updates Plus Explicit Update Notification

Do not add a full in-place auto-updater to the public `v3.0.0` Whisper-only
release. The app is unsigned, the installer replaces files that may be in use,
and a reliable updater needs a signed manifest, checksum verification, and a
rollback plan. This release keeps manual installation through GitHub Releases
and adds an explicit "Check for Updates" action. It makes no startup network
request; when clicked, it queries the latest GitHub release with a short
timeout, compares it to the installed version, and opens the release page when
a newer version exists.
