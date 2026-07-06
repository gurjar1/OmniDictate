# STT Model Research Snapshot

Date: 2026-07-05

This research uses primary sources where possible: official model cards,
official docs, GitHub repositories, and papers.

## Recommendation

Keep `faster-whisper` plus Whisper `large-v3-turbo` as the default dictation
engine for the next checkpoint. Add any new STT model behind an adapter spike,
not directly in the main UI.

This recommendation still holds after the first adapter spike and benchmark:
Moonshine-tiny loaded through the optional Transformers ASR adapter, matched
the short fixture, and met the synthetic latency promotion bar after warmup.
It still needs real microphone snippets, package/import proof, and explicit
cache/runtime handling before any visible UI or release promotion.

Best next candidates after the 2026-07-05 refresh and live source check:

1. NVIDIA Parakeet unified English or Nemotron 3.5 ASR for a streaming/offline
   ASR spike.
2. Moonshine Streaming for low-latency edge dictation.
3. Parakeet TDT v3, Qwen3-ASR, or GLM-ASR-Nano for multilingual/dialect ASR
   coverage.
4. Voxtral Realtime for native streaming ASR experimentation if a heavier
   runtime is acceptable.
5. VibeVoice-ASR, MOSS-Transcribe, Cohere Transcribe, and Gemma 4 for
   long-form, structured, or multimodal ASR/translation/reasoning, not as the
   default
   fastest dictation engine.
6. IBM Granite Speech 4.1 Plus for speaker-attributed ASR, word-level
   timestamps, and keyword-biasing experiments, not for the default
   short-dictation release path.

## 2026-07-05 Live Source Refresh

The live Hugging Face ASR catalog still supports the same release stance:
`openai/whisper-large-v3-turbo` remains a mature local baseline, while the
newer active models split into separate evaluation lanes rather than one
obvious replacement.

Use these lanes for the next phase:

- Low-latency dictation lane: Moonshine-tiny/streaming, Parakeet unified
  English, and Nemotron English/multilingual streaming. These are the only
  candidates that should be compared directly against the global-hotkey
  `large-v3-turbo` path first.
- Multilingual/dialect lane: Nemotron 3.5 ASR, Parakeet TDT v3, Qwen3-ASR, and
  GLM-ASR-Nano. Promotion requires physical microphone snippets in the target
  languages, not just the English fixture.
- Realtime/heavy lane: Voxtral Realtime. Treat it as a server/runtime spike
  because its recommended path is vLLM/realtime-oriented and the model is much
  heavier than Whisper.
- Rich-transcript lane: IBM Granite Speech 4.1 Plus, VibeVoice-ASR, Cohere
  Transcribe, and MOSS-Transcribe. These are meeting-note or structured-output
  candidates; do not benchmark them as direct replacements for short
  push-to-talk dictation unless the product goal changes.

Source highlights from the live refresh:

- Hugging Face currently lists many actively updated ASR models, including
  NVIDIA Nemotron/Parakeet, Qwen3-ASR, Cohere Transcribe, Voxtral Realtime, and
  IBM Granite Speech:
  [Hugging Face ASR models](https://huggingface.co/models?pipeline_tag=automatic-speech-recognition).
- Nemotron 3.5 ASR is a 600M multilingual streaming model with punctuation,
  capitalization, 40 language-locales, and configurable chunk sizes from 80 ms
  to 1120 ms:
  [nvidia/nemotron-3.5-asr-streaming-0.6b](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b).
- Parakeet TDT v3 is a 600M multilingual ASR model for 25 European languages
  with automatic language detection:
  [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3).
- Qwen3-ASR HF variants expose Transformers usage and Apache-2.0 licensing:
  [Qwen/Qwen3-ASR-1.7B-hf](https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf).
- Voxtral Mini Realtime advertises configurable streaming delay, 13 languages,
  Apache-2.0 licensing, and a recommended vLLM path:
  [mistralai/Voxtral-Mini-4B-Realtime-2602](https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602).
- IBM Granite Speech 4.1 Plus adds speaker-attributed ASR and word-level
  timing, but explicitly targets richer transcript workflows rather than the
  minimal dictation loop:
  [ibm-granite/granite-speech-4.1-2b-plus](https://huggingface.co/ibm-granite/granite-speech-4.1-2b-plus).

Decision from this refresh: do not promote any newly discovered ASR model into
the release UI. Add candidates only through a named lane, keep all heavy
runtimes lazy, and require a physical-microphone report before a candidate can
graduate beyond source/dev tooling.

## Adapter Promotion Criteria

A non-Whisper STT model can be promoted from research to visible product UI
only after a named adapter spike proves all of the following against the
current `large-v3-turbo` baseline on the same machine:

- Accuracy: at least the same expected-word match on the generated short WAV
  fixture and no obvious punctuation/filter regression in worker tests.
- Latency: at least 20% faster median inference on short dictation snippets,
  or a documented product win that Whisper does not cover, such as streaming
  partials, multilingual/dialect accuracy, timestamps, or hotword control.
- Runtime isolation: baseline `main_gui`/`core_logic` imports still avoid
  eager `torch`, `transformers`, `huggingface_hub`, NeMo, or server-runtime
  imports.
- Packaging: the Whisper-only bundle remains under the current release size
  limit and does not include the candidate model, candidate runtime, model
  cache, or downloaded weights.
- Evidence: the spike records command, model id/version, latency, transcript,
  cache footprint, Windows warnings, and pass/fail decision in `docs/evidence`
  or this research document.

Until those checks pass, keep the model behind source/dev tooling and do not
add it to the default installer or first-run UI.

Use the benchmark harness for repeatable evidence:

```powershell
.\venv\Scripts\python.exe tools\stt_adapter_benchmark.py --whisper-model large-v3-turbo --candidate-model UsefulSensors/moonshine-tiny --runs 3 --whisper-package-dir smoke_test_assets\packaging\dist-whisper\OmniDictate --check-import-boundary --check-command-routing --command-check "comma=," --command-check "period=." --report-json smoke_test_assets\stt-benchmarks\moonshine-tiny-vs-large-v3-turbo.json
```

The harness reports baseline/candidate median latency, word-match ratio, audio
source, candidate Hugging Face cache footprint when available, optional
Whisper-only package-boundary evidence, optional baseline import-boundary
evidence, a decision string such as `candidate-meets-latency-promotion-bar` or
`defer-candidate-no-measured-win`, optional command-routing checks, and
`promotion_blockers` so a synthetic latency win is not mistaken for release
approval.

To close the physical-snippet blocker, first record and validate a spoken
microphone WAV with `tools\microphone_capture_diagnostic.py`, then pass that
saved file into the same benchmark with an explicit source label:

```powershell
.\venv\Scripts\python.exe tools\stt_adapter_benchmark.py --audio smoke_test_assets\microphone\spoken-phrase-large-v3-turbo.wav --audio-source physical-microphone --whisper-model large-v3-turbo --candidate-model UsefulSensors/moonshine-tiny --runs 3 --whisper-package-dir smoke_test_assets\packaging\dist-whisper\OmniDictate --check-import-boundary --check-command-routing --command-check "comma=," --command-check "period=." --report-json smoke_test_assets\stt-benchmarks\moonshine-tiny-physical-mic.json
```

## Current Sources And Notes

### Whisper / faster-whisper

- OpenAI Whisper `large-v3-turbo` is a pruned `large-v3` variant with fewer
  decoding layers, trading minor quality loss for speed:
  [openai/whisper-large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo).
- `faster-whisper` is a CTranslate2 reimplementation that reports faster
  inference and lower memory than the OpenAI implementation:
  [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper).

Fit for OmniDictate: keep as baseline. It is already integrated and matches
the product's short-utterance local dictation workflow.

### Gemma 4

- Gemma 4 E2B/E4B support text, image, and audio inputs:
  [google/gemma-4-E2B-it](https://huggingface.co/google/gemma-4-E2B-it).
- Google documents Gemma 4 E2B, E4B, and 12B Unified for multilingual speech
  recognition and speech translation:
  [Gemma audio understanding](https://ai.google.dev/gemma/docs/capabilities/audio).
- Transformers documents `AutoModelForMultimodalLM` audio usage for Gemma 4:
  [Transformers Gemma4 docs](https://huggingface.co/docs/transformers/en/model_doc/gemma4).

Fit for OmniDictate: useful for context-aware correction, translation, and
reasoning. Keep native audio experimental until live model generation passes.

### NVIDIA Parakeet

- `nvidia/parakeet-tdt-0.6b-v3` is a 600M multilingual ASR model for 25
  European languages with punctuation, capitalization, timestamps, and long
  audio support:
  [Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3).
- `nvidia/parakeet-unified-en-0.6b` is an English RNN-T ASR model combining
  offline and streaming inference, with model-card latency as low as 160 ms:
  [Parakeet unified English](https://huggingface.co/nvidia/parakeet-unified-en-0.6b).

Fit for OmniDictate: strong candidate for a dedicated ASR adapter spike,
especially if lower latency than Whisper is needed.

### NVIDIA Nemotron 3.5 ASR

- `nvidia/nemotron-3.5-asr-streaming-0.6b` is a 600M multilingual streaming
  ASR model with punctuation/capitalization and configurable chunk sizes from
  80 ms through 1120 ms:
  [Nemotron 3.5 ASR streaming](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b).

Fit for OmniDictate: good candidate for the same low-latency adapter lane as
Parakeet unified English. The likely integration risk is runtime packaging:
the model card points at NeMo/Transformers-style use, so it needs an isolated
spike before any UI promotion.

Current refresh note: prioritize this ahead of heavier LLM-style ASR for a
streaming adapter only if the next phase explicitly targets partial dictation
or lower end-to-end latency.

### Moonshine

- Moonshine is designed for real-time transcription and voice commands:
  [Transformers Moonshine docs](https://huggingface.co/docs/transformers/en/model_doc/moonshine).
- `UsefulSensors/moonshine-tiny` is a 27M-parameter English-only ASR model:
  [UsefulSensors/moonshine-tiny](https://huggingface.co/UsefulSensors/moonshine-tiny).
- Moonshine Streaming uses a lightweight audio frontend and sliding-window
  encoder for low-latency ASR on edge-class hardware:
  [UsefulSensors/moonshine-streaming-tiny](https://huggingface.co/UsefulSensors/moonshine-streaming-tiny).

Fit for OmniDictate: good candidate for low-resource or command-focused
dictation. Needs Windows packaging validation.

Local spike result: viable as an experimental adapter, not a baseline
replacement. `UsefulSensors/moonshine-tiny` loaded through Transformers,
transcribed the generated short fixture with an 8/8 word match, and initially
reported 1.83s inference latency. A later repeated benchmark with
`tools\stt_adapter_benchmark.py --whisper-model large-v3-turbo
--candidate-model UsefulSensors/moonshine-tiny --runs 3` reported Whisper
`large-v3-turbo` median latency `0.47s`, Moonshine-tiny median latency `0.31s`,
100% word match for both, decision
`candidate-meets-latency-promotion-bar`, package-boundary `passed: true`,
import-boundary `passed: true`, command-routing `comma` -> `,` and `period`
-> `.`, and `promotion_ready: false`. The local Hugging Face cache footprint
for Moonshine-tiny was 110,376,063 bytes across 12 files, Hugging Face warned
about unauthenticated Hub requests, and Windows previously emitted a
symlink-cache warning without Developer Mode/admin. The report still lists
blockers for physical microphone snippets and release UI approval. This moves
Moonshine-tiny to "promising follow-up" for real microphone snippets, not into
the default installer.

### Qwen3-ASR

- Qwen3-ASR 0.6B/1.7B support language identification and ASR for 52 languages
  and dialects:
  [Qwen/Qwen3-ASR-1.7B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B).

Fit for OmniDictate: strong multilingual candidate. Needs adapter isolation
because runtime/tooling may be heavier than Whisper.

2026-07-04 refresh: `Qwen/Qwen3-ASR-0.6B-hf` appeared as a recent smaller
variant, but the family is still heavier than the Moonshine tiny spike and
should remain behind adapter isolation.

### GLM-ASR-Nano

- `zai-org/GLM-ASR-Nano-2512` is a 1.5B-parameter open-source speech
  recognition model with strong dialect support, especially Cantonese and
  Mandarin/English scenarios:
  [zai-org/GLM-ASR-Nano-2512](https://huggingface.co/zai-org/GLM-ASR-Nano-2512).
- Transformers has a dedicated GLM-ASR model doc:
  [Transformers GLM-ASR docs](https://huggingface.co/docs/transformers/en/model_doc/glmasr).

Fit for OmniDictate: worth tracking for multilingual/dialect-heavy users, but
too large and too new for the baseline package without a measured adapter
spike.

### NVIDIA Canary-Qwen

- Canary-Qwen-2.5B is an English ASR model with punctuation/capitalization and
  ASR/LLM modes:
  [nvidia/canary-qwen-2.5b](https://huggingface.co/nvidia/canary-qwen-2.5b).

Fit for OmniDictate: promising for accuracy, but 2.5B is likely too heavy for
default low-friction dictation.

### Voxtral Realtime

- Voxtral Mini 4B Realtime is a multilingual real-time transcription model
  with configurable streaming delays and a model-card claim of less than
  500 ms delay:
  [mistralai/Voxtral-Mini-4B-Realtime-2602](https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602).
- The paper describes a natively streaming ASR model:
  [Voxtral Realtime paper](https://arxiv.org/html/2602.11298v2).

Fit for OmniDictate: interesting for future streaming dictation, but heavier
than the current app and should be spiked separately.

Current refresh note: because the model card recommends vLLM/realtime serving
and calls out GPU memory needs, treat this as a server/runtime experiment, not
as a direct `TransformersASRBackend` replacement.

### MOSS-Transcribe

- `OpenMOSS-Team/MOSS-Transcribe-preview-2B` is an English STT model using a
  Qwen3-1.7B language backbone and Qwen3-Omni-MoE audio encoder:
  [MOSS-Transcribe preview 2B](https://huggingface.co/OpenMOSS-Team/MOSS-Transcribe-preview-2B).

Fit for OmniDictate: interesting as an English accuracy experiment, especially
because it exposes a Transformers pipeline path, but still heavier than the
current Whisper-only release target.

### Microsoft VibeVoice-ASR

- `microsoft/VibeVoice-ASR` is a long-form structured ASR model designed for
  up to 60-minute audio in a single pass, with speaker/timestamp/content
  output, customized hotwords, and 50+ languages:
  [microsoft/VibeVoice-ASR](https://huggingface.co/microsoft/VibeVoice-ASR).

Fit for OmniDictate: better aligned with meeting transcription or long-form
notes than short dictation. Track it for future product expansion, not the
current global hotkey dictation release.

### Cohere Transcribe

- Cohere Transcribe is a 2B dedicated audio-in/text-out ASR model supporting
  14 languages:
  [CohereLabs/cohere-transcribe-03-2026](https://huggingface.co/CohereLabs/cohere-transcribe-03-2026).
- The Hugging Face release notes describe it as Apache 2.0 and intended for
  high-accuracy multilingual transcription:
  [Cohere Transcribe release blog](https://huggingface.co/blog/CohereLabs/cohere-transcribe-03-2026-release).

Fit for OmniDictate: evaluate only after lighter local-first candidates.

### IBM Granite Speech 4.1 Plus

- Granite Speech 4.1 Plus exposes Transformers usage, Apache-2.0 licensing,
  speaker-attributed ASR, word-level timestamps, incremental decoding, and
  keyword list biasing:
  [ibm-granite/granite-speech-4.1-2b-plus](https://huggingface.co/ibm-granite/granite-speech-4.1-2b-plus).
- The model card says the plus model adds speaker labels and word transcripts,
  but the base mode does not provide punctuation/capitalization.

Fit for OmniDictate: useful for future meeting-note or rich-transcript modes.
Do not use it for the current minimal dictation loop until punctuation,
latency, and packaging are proven on physical snippets.

### SenseVoice

- SenseVoiceSmall supports ASR, language ID, emotion recognition, and audio
  event detection:
  [FunAudioLLM/SenseVoiceSmall](https://huggingface.co/FunAudioLLM/SenseVoiceSmall).

Fit for OmniDictate: useful for multilingual experiments, but extra emotion
and event labels may not match plain dictation without careful output cleaning.
