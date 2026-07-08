# OmniDictate Product Spec

## Purpose

OmniDictate is a local-first Windows dictation app that turns speech into text
and types the result into the user's active application.

## Primary Users

- A Windows user who wants private local dictation.
- A power user who needs push-to-talk and fast correction in any app.
- An experimental user with a GPU who wants multimodal context or speech
  translation.

## Core Workflow

1. Launch OmniDictate.
2. Select a safe default model or keep existing settings.
3. Start dictation.
4. Speak with VAD or hold the PTT key.
5. Review output in the app.
6. Text is typed into the active target window unless OmniDictate is focused.
7. Stop dictation and unload models cleanly.

## Baseline Feature Requirements

- Whisper-only dictation works without Gemma dependencies or external servers.
- VAD starts and stops recording on silence threshold.
- PTT overrides VAD while held and can queue completed phrases after silence
  without waiting for key release.
- Spoken punctuation maps to punctuation characters.
- Exact filter phrases are not typed.
- Language selection passes through to the backend.
- Settings persist across restarts.
- App avoids typing into its own window.

## Experimental Feature Requirements

- Hybrid Gemma mode uses Whisper as the audio draft and Gemma only for
  refinement when context/reasoning requires it.
- Native Gemma audio uses official Gemma 4 audio prompt structure and stays
  experimental until live gates pass.
- GGUF server mode never sends raw audio; it sends text plus optional images to
  a local OpenAI-compatible endpoint.
- Visual context controls are disabled when the active route cannot use them.
- Reasoning mode can require preview before typing.
- Alternative STT engines must stay behind adapter tooling until they beat the
  current Whisper baseline on a named product metric and preserve the
  Whisper-only package boundary.

## UX Principles

- Default screen should support immediate dictation, not onboarding.
- Whisper path should feel simple and stable.
- Experimental controls should be visible but clearly labeled by capability.
- Settings should be compact, scannable, and grouped by workflow.
- Do not market unreleased or unverified model paths as finished.

## Release Acceptance

A release candidate is acceptable only when:

- Quick gate passes.
- Whisper parity live gate passes.
- Any enabled Gemma route has a matching live gate.
- Packaging and installer smoke pass.
- README, installer version, screenshots, and release notes describe only
  verified behavior.

## Alternative STT Acceptance

An alternative STT engine is acceptable for visible product UI only when it:

- Belongs to a named evaluation lane: low-latency dictation,
  multilingual/dialect dictation, realtime/heavy runtime, or rich transcript.
- Matches or beats `large-v3-turbo` accuracy on the same generated fixture and
  any available physical microphone snippets.
- Improves a named product metric such as median short-utterance latency,
  streaming partials, multilingual/dialect accuracy, timestamps, or hotword
  support.
- Does not add eager heavy imports to the Whisper-only startup path.
- Does not add model files, candidate runtimes, or cache artifacts to the
  default installer.
- Has repeatable evidence for command, model id/version, latency, transcript,
  cache footprint, Windows warnings, and final keep/defer/reject decision.
- Rich-transcript models such as IBM Granite Speech, VibeVoice-ASR, Cohere
  Transcribe, or MOSS-Transcribe are not default dictation replacements unless
  the product scope explicitly expands beyond global hotkey dictation.
