# OmniDictate: Real-time AI Dictation for Windows

**Summary:** Real-time AI dictation using faster-whisper—type anywhere with instant, accurate speech-to-text conversion.

This project provides a real-time dictation tool for Windows, built using the `faster-whisper` library (a fast implementation of OpenAI's Whisper model), `sounddevice` for audio input, and `pywinauto` for typing into the active window.

## Features

*   **Real-time Transcription:** Transcribes your speech to text in real time.
*   **Voice Activity Detection (VAD):** Automatically starts transcribing when speech is detected.
*   **Push-to-Talk:** Hold the right Shift key (`Shift_R`) to transcribe, overriding VAD.
*   **Commands:**
    *   "delete last *n* words": Deletes the last *n* words. (e.g., "delete last three words")
    *   "new line" or "next line": Inserts a new line.
    *   Punctuation: Say punctuation marks like "question mark", "comma", "period", etc., to insert them. See the "Supported Punctuation" section below.
*   **Optimized for Speed:** Uses `faster-whisper` and threading for low latency.
*   **Uses Default Audio Input:** Automatically uses your system's default audio input device.
*    **Hallucination Mitigation**: The script is configured to minimize the occurrence of repetitive or nonsensical text.

## Minimum System Requirements

*   **OS:** Windows 10 or 11
*   **Processor:** Intel Core i5 or equivalent (quad-core or better)
*   **RAM:** 8GB (16GB+ recommended)
*   **GPU (Recommended):** NVIDIA GPU with CUDA support (4GB+ VRAM, 6GB+ for larger models)
*   **Storage:** Enough space for the Whisper model.

## Requirements

*   **Operating System:** Windows (tested on Windows 10 and 11).
*   **Python:** Python 3.7 or later.
*   **NVIDIA GPU (Highly Recommended):** A CUDA-enabled NVIDIA GPU is *highly recommended* for significantly faster transcription. The script will work on CPU, but it will be much slower.
*   **CUDA Toolkit (if using GPU):** You *must* have the correct CUDA Toolkit installed and configured for your GPU.  See the "CUDA Toolkit and cuDNN" section below for details.
*   **cuDNN (if using GPU):**  You need the NVIDIA cuDNN library, which is a GPU-accelerated library of primitives for deep neural networks.  See the "CUDA Toolkit and cuDNN" section below.
*   **ASIO Drivers (Optional, for Low Latency):** For the lowest possible latency on Windows, ASIO drivers are recommended. If your sound card doesn't have native ASIO drivers, install ASIO4ALL: [http://www.asio4all.org/](http://www.asio4all.org/). The script will use the default Windows audio drivers if ASIO is not available.

## Installation

1.  **Install Python:** If you don't have Python installed, download it from [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/). Make sure to check the box that says "Add Python x.x to PATH" during installation.

2.  **Clone the Repository:**

    ```bash
    git clone https://github.com/gurjar1/OmniDictate.git
    cd OmniDictate
    ```

3.  **Create a Virtual Environment (Recommended):**

    ```bash
    python -m venv venv
    venv\Scripts\activate  # On Windows (PowerShell)
    ```

4.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

5.  **Install PyTorch (with CUDA support):**

    *   **Crucially, you *must* install a CUDA-enabled version of PyTorch if you have an NVIDIA GPU.** The standard `pip install torch` will likely install the CPU-only version.
    *   Go to the PyTorch website: [https://pytorch.org/get-started/locally/](https://pytorch.org/get-started/locally/)
    *   Select your OS (Windows), package (Pip), language (Python), and *Compute Platform* (choose the appropriate CUDA version for your GPU and cuDNN version - see below).
    *   The website will give you the correct `pip install` command. Copy and run that command. It will look something like this (but the exact command will vary):

        ```bash
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        ```
6. **CUDA Toolkit and cuDNN:**
    *   **Determine Required CUDA Version:** The PyTorch installation command from the previous step will indicate the required CUDA version (e.g., `cu118` means CUDA 11.8).
    *    **Download CUDA Toolkit:** Go to the NVIDIA CUDA Toolkit Archive: [https://developer.nvidia.com/cuda-toolkit-archive](https://developer.nvidia.com/cuda-toolkit-archive).  Download the CUDA Toolkit version that matches the PyTorch requirement.  *Do not* just install the *latest* version; it might not be compatible.
    *   **Install CUDA Toolkit:** Run the installer.  Choose the "Custom (Advanced)" installation option.
        *   **Important:**  Make sure the "CUDA" component (and all its subcomponents) is selected.
        *   **Driver:** You can usually uncheck the "Driver components" if you already have a recent NVIDIA driver installed.  However, if you're unsure, it's generally safe to let the CUDA Toolkit installer update the driver.
        *   **Visual Studio Integration:** If you don't use Visual Studio, you can uncheck the Visual Studio integration components.
        *   **Note the Installation Path:** Pay attention to where the CUDA Toolkit is installed (the default is usually `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.Y`, where `X.Y` is the version number).
    *   **cuDNN:** The CUDA Deep Neural Network library (cuDNN) is required for GPU acceleration.
    *   **Download:** You need to download cuDNN from the NVIDIA website: [https://developer.nvidia.com/cudnn](https://developer.nvidia.com/cudnn)
        *   You'll need to create a free NVIDIA Developer account (or log in if you already have one).
        *   Download the cuDNN version that matches your CUDA Toolkit version.  For example, if you installed CUDA Toolkit 11.8, download cuDNN for CUDA 11.x.  The cuDNN download page will list the compatible CUDA versions.  **Important:** Download the version "for CUDA 11.x" even if you have, say, CUDA 11.8.
        *   Choose the "Library for Windows (x86_64)" (or the appropriate version for your system).  It will be a `.zip` file.

    *   **Installation:**
        1.  **Unzip:** Unzip the downloaded cuDNN `.zip` file.
        2.  **Copy Files:**  Inside the unzipped folder, you'll find three folders: `bin`, `include`, and `lib`.  You need to copy the *contents* of these folders into the corresponding folders in your CUDA Toolkit installation directory.  The default CUDA Toolkit installation path is usually:
            `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.Y` (where `X.Y` is your CUDA version, e.g., `v11.8`).
            *   Copy the contents of the cuDNN `bin` folder to `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.Y\bin`.
            *   Copy the contents of the cuDNN `include` folder to `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.Y\include`.
            *   Copy the contents of the cuDNN `lib\x64` folder to `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\vX.Y\lib\x64`.
            **Do not** replace the entire folders; copy only the *contents* of the folders.

    * **Verification**
        * You don't typically "run" cuDNN directly. Its presence and correct installation are verified by the fact that PyTorch with CUDA support works correctly. If PyTorch can use your GPU, then cuDNN is installed correctly.

7.  **Install ASIO4ALL (Optional):** If your sound card doesn't have native ASIO drivers, download and install ASIO4ALL from [http://www.asio4all.org/](http://www.asio4all.org/). After installation, you may need to configure it to enable your microphone.

## Usage

1.  **Run the Script:**

    ```bash
    python dictation.py
    ```

2.  **Dictation:**
    *   The script will start in VAD mode, automatically transcribing when it detects speech.
    *   Hold down the **right Shift key (`Shift_R`)** to use push-to-talk mode. This overrides VAD.
    *   Speak clearly and at a consistent volume.

3.  **Stopping the Script:** Press the **Escape key (`Esc`)** to stop the script.

4.  **Commands:**
    *  "delete last *n* words": Delete last few words.
    *  "new line" or "next line": Insert a new line.

5. **Supported Punctuation:**
    *   "question mark"
    *   "exclamation mark"
    *   "comma"
    *   "period" / "full stop"
    *   "colon"
    *   "semicolon"
    *   "open parenthesis"
    *   "close parenthesis"
    *   "open bracket"
    *   "close bracket"
    *   "open brace"
    *   "close brace"
    *   "hyphen" / "dash"
    *   "underscore"
    *   "plus"
    *   "equals"
    *   "at"
    *   "hash"
    *   "dollar"
    *   "percent"
    *   "caret"
    *   "ampersand"
    *   "asterisk"

## Configuration

You can modify the following settings in the `dictation.py` file:

*   **`SILENCE_THRESHOLD`:** Adjust this value to control the sensitivity of the Voice Activity Detection (VAD). Higher values require louder speech to trigger transcription.
*   **`SILENCE_FRAMES`:** The number of consecutive silent audio chunks required to stop recording in VAD mode.
*   **`RECORD_KEY`:** Change the push-to-talk key (default is right Shift).
*   **`STOP_KEY`:** Change the key to stop the script (default is Escape).

### Changing the Whisper Model

The script currently uses the `large-v3` model. You can change this to a different model size:

1.  **Find the `MODEL_SIZE` variable:** Near the top of the `dictation.py` file.

2.  **Change the value:** Change `"large-v3"` to one of:

    *   `"large-v3"` (Best accuracy, slowest)
    *   `"medium"` (Good balance)
    *   `"small"` (Faster, less accurate)
    *   `"base"` (Even faster)
    *   `"tiny"` (Fastest, least accurate)

    For example:

    ```python
    MODEL_SIZE = "medium"
    ```

3.  **Save the file.** The script will automatically download the model on first use.

### Changing the Transcription Language

By default, this script is configured for **English (`en`)** transcription only. To transcribe other languages supported by Whisper:

1.  **Locate the `process_audio_buffer` function** in the `dictation.py` file.
2.  **Find the `model.transcribe` line** within that function. It looks like this:

    ```python
    segments, info = model.transcribe(audio_float32, beam_size=5, language="en", temperature=0.0, condition_on_previous_text=False)
    ```

3.  **Change the `language="en"` parameter** to the appropriate two-letter language code for the language you want to transcribe.

    *   Example for **Hindi**: `language="hi"`
    *   Example for **Spanish**: `language="es"`
    *   Example for **French**: `language="fr"`

    The modified line would look like this (for Hindi):

    ```python
    segments, info = model.transcribe(audio_float32, beam_size=5, language="hi", temperature=0.0, condition_on_previous_text=False)
    ```

4.  **Save the `dictation.py` file.**

**Important Notes:**

*   The standard Whisper models used by `faster-whisper` (like `large-v3`, `medium`, etc.) are **multilingual**. You generally *do not* need to download a different model file just to change the language.
*   Specifying the correct language code helps the model perform more accurately and potentially faster for that specific language.
*   Refer to the Whisper documentation for a list of supported languages and their corresponding two-letter codes: [https://github.com/openai/whisper#available-models-and-languages](https://github.com/openai/whisper#available-models-and-languages)

### Microphone Sample Rate

Ensure your microphone is set to 16000 Hz in Windows sound settings:

1.  Right-click speaker icon -> "Sounds" or "Open Sound settings."
2.  "Recording" tab.
3.  Select microphone -> "Properties."
4.  "Advanced" tab.
5.  "Default Format": select "16000 Hz".

## Troubleshooting

*   **No audio input:** Check microphone selection and Windows sound settings (make sure it's set to 16000 Hz).
*   **ASIO not detected:** Ensure ASIO4ALL is installed and configured (enable your microphone).
*   **`CUDA is not available`:**
    *   Verify NVIDIA GPU and driver.
    *   Verify *correct* CUDA Toolkit and cuDNN are installed (matching PyTorch). Run `nvcc --version`.
    *   Check CUDA Toolkit `bin` and `libnvvp` are in your PATH.
    *   Reinstall PyTorch (CUDA-enabled!) *within* the virtual environment.
    *   Check for conflicting installations.
*   **Slow transcription:** Use a GPU. Try a smaller model.
*   **Hallucinations:** The script is configured to minimize this. Improve audio quality.
*   **`ModuleNotFoundError`:** Activate your virtual environment and reinstall dependencies: `pip install -r requirements.txt`. If it persists, uninstall/reinstall the specific package, or recreate the virtual environment.
*   **COM Initialization Error:** If you encounter an error related to COM initialization (`CoInitializeEx` failed), ensure that the `typing_thread_function` in `dictation.py` includes the following lines at the beginning and end of the function:

    ```python
    def typing_thread_function():
        import pythoncom
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)  # Add this line
        try:
            # ... rest of the function ...
        finally:
            pythoncom.CoUninitialize()  # Add this line
    ```
   This ensures proper COM initialization and cleanup for `pywinauto`. This should prevent COM-related errors. If you still encounter issues, make sure no other applications are interfering with COM.

## License

MIT License

Copyright (c) 2023 GURJAR1

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
