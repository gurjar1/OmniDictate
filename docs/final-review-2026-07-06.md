# OmniDictate Final Review - 2026-07-06

Scope: final pre-publication review for the `v3.0.0` Whisper-only recovery release after package-size, UI, typing-target, and README concerns.

## Verdict

The smaller public package is sufficient for a fresh Windows install if the release claim stays Whisper-only and the README clearly states the external requirements. The final installer includes the app runtime, embedded Python, Qt/PySide, Faster-Whisper/CTranslate2, PyAV/FFmpeg support, and packaged runtime files. It intentionally excludes model weights, CUDA/cuDNN DLLs, Torch/Transformers, Gemma/GGUF stacks, alternative STT models, and local test caches.

That package strategy is better than bundling everything into one very large installer for this release. Whisper model weights change independently, users may choose different model sizes, and NVIDIA GPU runtime DLLs are platform/driver-sensitive. Bundling Gemma/Torch/GGUF again would recreate the multi-GB artifact and re-open the exact unstable lanes that `v3.0.0` is meant to recover from.

## Fresh Machine Requirements

A fresh Windows user should need only the public installer plus:

- Windows 10/11 x64.
- Microphone permission.
- First-run internet access, unless Whisper model files are already present in the Hugging Face cache.
- Disk space for the selected Whisper model cache.
- NVIDIA driver and CUDA/cuDNN runtime availability for GPU acceleration.
- Microsoft Visual C++ Redistributable 2015-2022 x64 only if Windows reports missing runtime DLLs.

Python, Git, PyTorch, Transformers, Gemma weights, GGUF models, and developer CUDA compiler tools are not required for normal public-installer use.

## README Review

The README has been reframed around the public `v3.0.0` Whisper-only product instead of the older `v2.0.2` style language and Gemma-era experiment copy. The critical public-facing corrections are:

- The public installer is described as Whisper-only.
- Gemma/GGUF/visual context/reasoning are moved to source/dev lanes.
- The smaller package size is explained as intentional.
- Fresh Windows requirements distinguish install-time requirements from first-run model/GPU dependencies.
- Update guidance now points users to GitHub Releases and recommends a future lightweight in-app update check instead of a full auto-updater.

Remaining README caveat: the screenshot asset is still `images/app_screenshot_v2.png`. It should be replaced before GitHub publication if a current packaged `v3.0.0` screenshot is available, but this is a presentation issue, not a runtime blocker.

## Threading And Process Review

Current architecture:

- `main_gui.py` owns the Qt UI and creates one `QThread` for `DictationWorker`.
- `DictationWorker.start_processing()` runs inside the worker `QThread`.
- Inside the worker, audio capture uses `sounddevice.InputStream`, a bounded audio queue, and a Qt timer that drains microphone chunks.
- Inference and typing each run on Python daemon threads owned by the worker.
- Transcripts return to the UI through Qt signals.
- Keystroke output now drops pending own-window text instead of replaying old transcripts into the next foreground app.

Strengths:

- Audio and transcription work are off the UI thread.
- Queues are bounded for audio and transcription requests.
- UI updates are signal-based.
- Stop paths close the audio stream, join worker-owned Python threads, and clear queues.
- Stale text replay into another app has a regression test.

Risks and improvements:

- Implemented on 2026-07-06: `stop_dictation()` now queues `stop_processing()` to the worker thread instead of using a blocking Qt invocation. `DictationWorker` emits `stop_completed`, the worker thread quits from that signal, and the UI stays in a visible stopping state until cleanup finishes.
- In-flight Whisper transcription is not cancellable. Stop now drops queued transcription requests before joining the inference thread, but it cannot interrupt a model call already inside CTranslate2. The practical mitigation remains a visible stopping state plus one in-flight-request limit.
- The worker mixes a Qt timer, a sounddevice callback, and Python daemon threads. This is workable, but lifecycle tests should stay strict because ownership is split across runtimes.
- Download and preload workers are separate `QThread` lanes. They already avoid the main dictation loop, but release tests should keep asserting that saved settings cannot trigger unexpected heavy model preload during smoke tests.
- Future alternative STT adapters should follow the same bounded request queue contract and must prove stop responsiveness before entering the public UI.

Small fixes made in this review: Start/Stop buttons now use explicit runtime states. Start is the primary action only when idle. Stop is the primary action only while dictation is running. During shutdown, Stop enters a neutral busy state instead of the UI pretending shutdown has already completed. The non-blocking stop path is guarded by `tools\threading_lifecycle_test.py`.

## Update Strategy

Full in-app auto-update is not recommended for `v3.0.0`.

Reasons:

- The app is currently unsigned.
- Windows installers may need to replace files while the app is running.
- A robust updater needs manifest signing, checksum verification, rollback behavior, and clear handling for per-user installs under `%LOCALAPPDATA%\OmniDictate`.
- A broken updater can strand users more severely than a missing updater.

Implemented `v3.0.0` solution:

- Keep manual updates through GitHub Releases.
- Add a "Check for Updates" button in Settings.
- On explicit user action, call the GitHub latest-release API with a short timeout, compare the latest tag to the installed app version, and open the release page if a newer version exists.
- Do not auto-download or auto-run installers until releases are signed and the update manifest includes a verified SHA256.

Acceptance criteria for update notification:

- No network call unless the user clicks "Check for Updates".
- If offline, show a readable non-blocking message.
- If current, show "You are up to date".
- If newer, show the version and open the GitHub release page through the default browser.
- Test version parsing for `v3.0.0` and `3.0.0`.

## Release Recommendation

Do not add Gemma, GGUF, alternative STT, or a full updater to the `v3.0.0` public build. Ship the Whisper-only recovery release only after the existing release gate remains green with the updated README/UI state. Treat a real long-run memory soak and packaged update-check screenshot as optional follow-up evidence, not a reason to re-expand the release scope.
