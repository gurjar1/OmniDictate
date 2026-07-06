# Gemma Transformers Live Evidence - 2026-07-04

Fixtures:

- Audio: `smoke_test_assets\gemma_live_smoke.wav`
- Image: `smoke_test_assets\gemma_live_smoke.png`
- Expected phrase: `hello world this is a simple speech test`
- Model files: `smoke_test_assets\models\gemma-4-E2B-it`
- GPU: NVIDIA GeForce RTX 3060 Laptop GPU, 6 GB VRAM

## Hybrid Context Route

Command:

```powershell
.\venv\Scripts\python.exe tools\gemma_smoke_test.py --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --runtime transformers --model google/gemma-4-E2B-it --quantization 4-bit --audio-mode hybrid-whisper --whisper-model tiny --duration 5 --expected "hello world this is a simple speech test" --min-word-ratio 0.75
```

Result: passed.

- Load: `Gemma model 'D:\OmniDictate - GUI\smoke_test_assets\models\gemma-4-E2B-it' loaded (4-bit).`
- Device map: `cuda:0`
- Route: `Whisper -> Gemma`
- Used visual context: `True`
- Generation latency: `10.47s`
- Match: `8/8 expected words`

## Native Audio Route

Command:

```powershell
.\venv\Scripts\python.exe tools\gemma_smoke_test.py --audio smoke_test_assets\gemma_live_smoke.wav --image smoke_test_assets\gemma_live_smoke.png --runtime transformers --model google/gemma-4-E2B-it --quantization 16-bit --audio-mode native-audio --whisper-model tiny --duration 5 --expected "hello world this is a simple speech test" --min-word-ratio 0.5
```

Result: passed, but too slow for the default product path on this machine.

- Load: `Gemma model 'D:\OmniDictate - GUI\smoke_test_assets\models\gemma-4-E2B-it' loaded (16-bit).`
- Device map: `cpu`
- Route: `Native Gemma audio`
- Used visual context: `True`
- Generation latency: `246.39s`
- Match: `8/8 expected words`

## Interpretation

The Gemma direction is technically salvageable for the local E2B model. The
hybrid path is the practical experimental route on this hardware. Native audio
works, but it fell back to CPU and should remain clearly labeled as an
experimental deep-context mode rather than a daily dictation path.

E4B was not tested in this pass because local E4B weights were not present.
