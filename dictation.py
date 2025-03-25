# Standard library imports
import time
import threading
import sys
import os
import queue
import re

# Third-party library imports
import numpy as np
import torch
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard
# Removed: from spellchecker import SpellChecker

# --- Configuration ---
# Typing delay between characters (in seconds). Adjust if typing is garbled.
CHAR_DELAY = 0.02 # Adjusted delay (20ms)

# --- Dependency Checks ---
def check_dependencies():
    """Checks if all required third-party libraries are installed."""
    missing_deps = []
    try: import sounddevice
    except ImportError: missing_deps.append("sounddevice")
    try: import numpy
    except ImportError: missing_deps.append("numpy")
    try: import faster_whisper
    except ImportError: missing_deps.append("faster-whisper")
    try: import torch
    except ImportError: missing_deps.append("torch (with CUDA)")
    try: import pynput
    except ImportError: missing_deps.append("pynput")
    try: import ctranslate2
    except ImportError: missing_deps.append("ctranslate2")
    try: import transformers
    except ImportError: missing_deps.append("transformers")
    try: import sentencepiece
    except ImportError: missing_deps.append("sentencepiece")
    # Removed spellchecker check
    try: import pywinauto
    except ImportError: missing_deps.append("pywinauto")
    try: import pythoncom # Check for pywin32 dependency indirectly
    except ImportError: missing_deps.append("pywin32")


    # Check CUDA availability here as well for clarity
    try:
        if torch.cuda.is_available():
             print("CUDA is available! GPU will be used.")
        else:
            print("WARNING: CUDA not available. Ensure PyTorch CUDA version is installed. Using CPU.")
    except NameError: # If torch wasn't imported
        pass
    except Exception as e:
        print(f"Error checking CUDA: {e}")


    if missing_deps:
        print("--- Error: Missing Dependencies ---")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("------------------------------------")
        print("Please install them using 'pip install <dependency_name>' or 'pip install -r requirements.txt'")
        if "torch (with CUDA)" in missing_deps or "torch" in missing_deps:
             print("For PyTorch with CUDA, follow instructions at https://pytorch.org/get-started/locally/")
        exit()
    else:
        print("All core dependencies seem installed.")

check_dependencies()

# --- Configuration (Continued) ---
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.02
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
SILENCE_THRESHOLD = 500
SILENCE_FRAMES = int(0.5 * SAMPLE_RATE / CHUNK_SIZE)
RECORD_KEY = keyboard.Key.shift_r
STOP_KEY = keyboard.Key.esc

# --- Model Loading ---
MODEL_SIZE = "large-v3" # Change this to use a different model size

try:
    # Check CUDA again before loading model
    use_cuda = torch.cuda.is_available()
    if not use_cuda:
        print("Attempting to load model on CPU.")
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8") # Use int8 on CPU for better speed
    else:
        print("Attempting to load model on GPU (CUDA).")
        model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
    print(f"Model '{MODEL_SIZE}' loaded successfully on {'GPU' if use_cuda else 'CPU'}.")
except Exception as e:
    print(f"--- Error loading model ---")
    print(f"{e}")
    print("Ensure the model name is correct and dependencies are installed.")
    if not use_cuda:
        print("Loading on CPU can be memory intensive.")
    exit()

# --- Global Variables ---
recording = False
audio_buffer = []
vad_active = False
frames_since_speech = 0
is_recording = False
audio_queue = queue.Queue()
text_queue = queue.Queue()
stop_event = threading.Event()

# --- Helper Functions ---

def delete_last_n_words_direct(n):
    """Deletes the last n words directly in the active window."""
    try:
        from pywinauto import application
        import ctypes
        import time

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        app = application.Application().connect(handle=hwnd)
        active_window = app.top_window()
        active_window.type_keys("^c")
        time.sleep(0.05)
        for _ in range(n):
            active_window.type_keys("^+{LEFT}")
            time.sleep(0.05)
        active_window.type_keys("{DELETE}")
        time.sleep(0.05)
        return True
    except Exception as e:
        print(f"Error deleting text directly: {e}")
        return False

def insert_punctuation(punctuation_name):
    """Inserts punctuation based on a verbal command."""
    try:
        from pywinauto import application
        import ctypes

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        app = application.Application().connect(handle=hwnd)
        active_window = app.top_window()

        punctuation_map = {
            "question mark": "?", "exclamation mark": "!", "comma": ",",
            "period": ".", "full stop": ".", "colon": ":", "semicolon": ";",
            "open parenthesis": "(", "close parenthesis": ")", "open bracket": "[",
            "close bracket": "]", "open brace": "{", "close brace": "}",
            "hyphen": "-", "dash": "-", "underscore": "_", "plus": "+",
            "equals": "=", "at": "@", "hash": "#", "dollar": "$",
            "percent": "%", "caret": "^", "ampersand": "&", "asterisk": "*",
        }

        punctuation = punctuation_map.get(punctuation_name.lower())
        if punctuation:
            active_window.type_keys(punctuation)
            print(f"Inserted: {punctuation}")
            return True
        else:
            print(f"Unknown punctuation command: {punctuation_name}")
            return False
    except Exception as e:
        print(f"Error inserting punctuation: {e}")
        return False

def insert_new_line():
    """Inserts a new line."""
    try:
        from pywinauto import application
        import ctypes

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        app = application.Application().connect(handle=hwnd)
        active_window = app.top_window()

        active_window.type_keys("{ENTER}")
        print("Inserted new line.")
        return True

    except Exception as e:
        print(f"Error inserting new line: {e}")
        return False

# --- Audio Callback ---
def audio_callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    if not stop_event.is_set():
        audio_queue.put(indata.copy())

# --- Transcription Thread ---
def transcription_thread():
    global recording, audio_buffer, vad_active, frames_since_speech, is_recording

    while not stop_event.is_set():
        try:
            chunk = audio_queue.get(timeout=1)
        except queue.Empty:
            continue

        # Convert raw audio bytes to numpy array for VAD
        chunk_np = np.frombuffer(chunk, dtype=np.int16).flatten()

        if is_recording:
            if not recording:
                print("Recording started (Push-to-Talk)...")
                recording = True
                vad_active = False
                audio_buffer = []
            audio_buffer.append(chunk_np) # Store numpy array
            frames_since_speech = 0
            continue

        amplitude = np.abs(chunk_np).mean()

        if not recording:
            if amplitude > SILENCE_THRESHOLD:
                print("Recording started (VAD)...")
                recording = True
                vad_active = True
                audio_buffer = []
                audio_buffer.append(chunk_np) # Store numpy array
                frames_since_speech = 0

        elif recording and vad_active:
            if amplitude > SILENCE_THRESHOLD:
                frames_since_speech = 0
                audio_buffer.append(chunk_np) # Store numpy array
            else:
                frames_since_speech += 1
                if frames_since_speech > SILENCE_FRAMES:
                    print("Recording stopped (VAD). Transcribing...")
                    recording = False
                    vad_active = False
                    process_audio_buffer()

# --- Audio Processing Function (Spell Check Removed) ---
def process_audio_buffer():
    global audio_buffer
    if not audio_buffer:
        return

    # Concatenate audio data
    if not audio_buffer: return
    try:
        audio_data = np.concatenate(audio_buffer)
        audio_float32 = audio_data.astype(np.float32) / 32768.0
    except ValueError:
        print("Error concatenating audio buffer. Clearing.")
        audio_buffer = []
        return

    start_time = time.time()
    try:
        segments, info = model.transcribe(audio_float32, beam_size=5, language="en", temperature=0.0, condition_on_previous_text=False)
        transcribed_text = ""
        for segment in segments:
            transcribed_text += segment.text # Get the raw text including punctuation
    except Exception as e:
        print(f"Error during transcription: {e}")
        audio_buffer = []
        return

    end_time = time.time()

    # --- Targeted Filtering ---
    if transcribed_text.strip().lower() in ("thanks for watching!", "thank you.", "thanks for watching", "thank you"):
        print(f"Filtered out hallucinated phrase: '{transcribed_text.strip()}'")
        audio_buffer = []
        return

    if transcribed_text.strip():
        print(f"Transcribed: {transcribed_text.strip()} (Latency: {end_time - start_time:.2f}s)")

        # --- Command Parsing ---
        new_line_match = re.match(r"(new line|next line)", transcribed_text.strip().lower())
        if new_line_match:
            if insert_new_line():
                audio_buffer = []
                return

        punctuation_match = re.match(r"(question mark|exclamation mark|comma|period|full stop|colon|semicolon|open parenthesis|close parenthesis|open bracket|close bracket|open brace|close brace|hyphen|dash|underscore|plus|equals|at|hash|dollar|percent|caret|ampersand|asterisk)", transcribed_text.strip().lower())
        if punctuation_match:
            if insert_punctuation(punctuation_match.group(1)):
                audio_buffer = []
                return

        command_match = re.match(r"(delete|remove) last (\d+|one|two|three|four|five|six|seven|eight|nine|ten) words?", transcribed_text.strip().lower())
        if command_match:
            action = command_match.group(1)
            if command_match.group(2).isdigit():
                number = int(command_match.group(2))
            else:
                word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                               "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
                number = word_to_num.get(command_match.group(2), 0)

            if action in ("delete", "remove") and number > 0:
                if delete_last_n_words_direct(number):
                    print(f"Deleted last {number} words.")
            audio_buffer = []
            return

        # --- Regular Text Handling (Typo Correction Removed) ---
        # spell = SpellChecker() # Removed
        processed_text = transcribed_text.strip() # Use the transcribed text directly

        # No need to split/reconstruct if not doing typo correction
        if processed_text:
            text_queue.put(processed_text + " ") # Add trailing space

    audio_buffer = []

# --- Typing Thread (Using pynput Controller) ---
def typing_thread_function():
    import pythoncom
    pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
    try:
        import ctypes
        import time # Ensure time is imported

        # Use pynput controller for character-by-character typing
        keyboard_controller = keyboard.Controller()

        while not stop_event.is_set():
            try:
                text = text_queue.get(timeout=1)
                try:
                    # Type character by character
                    for char in text:
                        keyboard_controller.press(char)
                        keyboard_controller.release(char)
                        time.sleep(CHAR_DELAY) # Use the configured delay

                except Exception as e:
                    print(f"Error typing into active window: {e}")

            except queue.Empty:
                continue
    finally:
        pythoncom.CoUninitialize()

# --- Keyboard Listener Callbacks (Unchanged) ---
def on_press(key):
    global is_recording
    if key == RECORD_KEY:
        is_recording = True

def on_release(key):
    global is_recording
    if key == RECORD_KEY:
        is_recording = False
        print("Recording stopped (Push-to-Talk). Transcribing...")
        process_audio_buffer()

    if key == STOP_KEY:
        print("Stopping...")
        stop_event.set()

# --- Main Execution Block (Unchanged) ---
try:
    default_device_info = sd.default.device[0]
    print(f"Using default input device: {sd.query_devices(default_device_info)['name']}")

    with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=CHUNK_SIZE,
                        device=default_device_info, channels=1, dtype='int16',
                        callback=audio_callback):

        transcription_thread_instance = threading.Thread(target=transcription_thread, daemon=True)
        transcription_thread_instance.start()

        typing_thread = threading.Thread(target=typing_thread_function, daemon=True)
        typing_thread.start()

        print(f"\nReal-time dictation started. Hold '{RECORD_KEY}' to record (overrides VAD).")
        print(f"Press '{STOP_KEY}' to stop the script.")
        print("Waiting for speech...")

        while not stop_event.is_set():
            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join(timeout=0.1)

        print("Stopped.")

except KeyboardInterrupt:
    print("\nDictation stopped.")
    stop_event.set()
except Exception as e:
    print(f"Error: {e}")
finally:
    stop_event.set()
    if 'transcription_thread_instance' in locals() and transcription_thread_instance.is_alive():
        transcription_thread_instance.join()
    if 'typing_thread' in locals() and typing_thread.is_alive():
        typing_thread.join()