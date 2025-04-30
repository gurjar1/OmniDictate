# core_logic.py

# Standard library imports
import time
import threading
import sys
import os
import queue
import re
import logging

# Third-party library imports
import numpy as np
import torch
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard # Keep for Controller in typing thread
from model_downloader import ModelDownloader
import webrtcvad
import noisereduce as nr

# PySide6 imports for threading and signals
from PySide6.QtCore import QObject, Signal, QTimer, Slot

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.02
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
# CHAR_DELAY passed via __init__

# --- Helper Functions ---
# (Unchanged - delete_last_n_words_direct, insert_punctuation, insert_new_line)
def delete_last_n_words_direct(n):
    """Deletes the last n words directly in the active window."""
    try:
        from pywinauto import application
        import ctypes, time
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd == 0: print("Error: Could not get foreground window handle."); return False
        app = application.Application().connect(handle=hwnd)
        active_window = app.top_window()
        active_window.set_focus(); time.sleep(0.05)
        for _ in range(n): active_window.type_keys("^+{LEFT}"); time.sleep(0.05)
        active_window.type_keys("{DELETE}"); time.sleep(0.05)
        return True
    except ImportError: print("Error: pywinauto not installed."); return False
    except Exception as e: print(f"Error deleting text: {e}"); return False

def insert_punctuation(punctuation_name):
    """Inserts punctuation based on a verbal command."""
    try:
        from pywinauto import application
        import ctypes, time
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd == 0: print("Error: Could not get foreground window handle."); return False
        app = application.Application().connect(handle=hwnd)
        active_window = app.top_window()
        active_window.set_focus(); time.sleep(0.05)
        pmap = {"question mark": "?", "exclamation mark": "!", "comma": ",", "period": ".", "full stop": ".", "colon": ":", "semicolon": ";", "open parenthesis": "(", "close parenthesis": ")", "open bracket": "[", "close bracket": "]", "open brace": "{", "close brace": "}", "hyphen": "-", "dash": "-", "underscore": "_", "plus": "+", "equals": "=", "at": "@", "hash": "#", "dollar": "$", "percent": "%", "caret": "^", "ampersand": "&", "asterisk": "*"}
        punc = pmap.get(punctuation_name.lower())
        if punc: active_window.type_keys(punc, pause=0.01); print(f"Inserted: {punc}"); return True
        else: print(f"Unknown punctuation: {punctuation_name}"); return False
    except ImportError: print("Error: pywinauto not installed."); return False
    except Exception as e: print(f"Error inserting punctuation: {e}"); return False

def insert_new_line():
    """Inserts a new line."""
    try:
        from pywinauto import application
        import ctypes, time
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd == 0: print("Error: Could not get foreground window handle."); return False
        app = application.Application().connect(handle=hwnd)
        active_window = app.top_window()
        active_window.set_focus(); time.sleep(0.05)
        active_window.type_keys("{ENTER}"); print("Inserted new line."); return True
    except ImportError: print("Error: pywinauto not installed."); return False
    except Exception as e: print(f"Error inserting new line: {e}"); return False


# --- Worker Class ---
class DictationWorker(QObject):
    status_updated = Signal(str)
    transcription_ready = Signal(str)
    error_occurred = Signal(str)
    volume_level = Signal(float)  # New signal for volume level updates
    processed_volume_level = Signal(float)  # New signal for processed volume level updates
    recording_state_changed = Signal(bool)  # Emitted when recording starts/stops
    vad_state_changed = Signal(bool)  # Emitted when VAD state changes

    def __init__(self, gui_wid, model_size="large-v3", language="en", vad_enabled=True,
                 silence_threshold=500, silence_duration=0.5, char_delay=0.02,
                 filter_words=None, new_line_commands=None, parent=None, hf_token=None,
                 use_gpu=True, audio_device=None, audio_gain=1.0):
        super().__init__(parent)
        self.gui_wid = gui_wid
        self.model_size = model_size
        self.language_code = language
        self._vad_enabled = vad_enabled
        self.silence_threshold = silence_threshold
        self.silence_frames = int(silence_duration * SAMPLE_RATE / CHUNK_SIZE)
        self.char_delay = char_delay
        self.filter_words = set(word.lower().strip() for word in filter_words) if filter_words else set()
        self.new_line_commands = set(cmd.lower().strip() for cmd in new_line_commands) if new_line_commands else {"new line", "next line"}
        self.hf_token = hf_token
        self.use_gpu = use_gpu
        self.audio_device = audio_device
        self.audio_gain = audio_gain

        # Add max volume tracking
        self.max_volume = 0.0
        self.volume_decay = 0.995  # Decay factor for max volume (allows it to decrease slowly over time)
        self.min_volume_threshold = 100.0  # Minimum threshold to consider for max volume

        print(f"Worker Init: GUI WID={self.gui_wid}, Model={self.model_size}, Lang={self.language_code}, VAD={self._vad_enabled}")
        print(f"Worker Init: Silence Thresh={self.silence_threshold}, Frames={self.silence_frames}, Char Delay={self.char_delay}")
        print(f"Worker Init: Audio Device={self.audio_device}, Gain={self.audio_gain}")

        self.model = None
        self.audio_stream = None
        self._is_running = False
        self._ptt_active = False
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        self.recording = False
        self.audio_buffer = []
        self.vad_active = False
        self.frames_since_speech = 0
        self.typing_thread_instance = None
        self.stop_typing_event = threading.Event()
        self.audio_check_timer = QTimer(self)
        self.audio_check_timer.timeout.connect(self._check_audio_queue)
        self.audio_check_interval = 50

        # Add audio monitoring thread
        self.audio_monitor_thread = None
        self.audio_monitor_stream = None
        self.stop_monitor = threading.Event()

        self._last_volume_update = 0.0
        self._smoothed_raw_volume = 0.0
        self._smoothed_processed_volume = 0.0
        self._smoothing_alpha = 0.3  # Smoothing factor for exponential smoothing

    # --- Public Slots ---
    @Slot(bool)
    def set_vad_enabled(self, enabled: bool):
        if self._vad_enabled != enabled:
            print(f"Setting VAD Enabled: {enabled}")
            self._vad_enabled = enabled
            if not enabled and self.vad_active:
                self.recording = False; self.vad_active = False; self.audio_buffer = []
                if self._is_running: self.status_updated.emit("Listening...")

    @Slot(bool)
    def set_ptt_state(self, is_pressed: bool):
        self._ptt_active = is_pressed
        if not is_pressed and self.recording and not self.vad_active:
            self.status_updated.emit("Transcribing...")
            self.recording = False
            self._process_audio_buffer()

    @Slot(float)
    def set_audio_gain(self, gain):
        """Set the audio gain level."""
        self.audio_gain = gain

    # --- Core Logic Methods ---
    def load_model(self, force_reload=False):
        if self.model and not force_reload:
            return True
            
        if self.model and force_reload:
            print("\n[MODEL] Force reloading model...")
            del self.model
            self.model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("[CUDA] Cleared CUDA cache")
            
        try:
            # Force CUDA initialization and debugging
            print("\n[CUDA] Checking CUDA availability...")
            print(f"├── CUDA Available: {torch.cuda.is_available()}")
            print(f"├── PyTorch Version: {torch.__version__}")
            if torch.cuda.is_available():
                print(f"├── CUDA Version: {torch.version.cuda}")
                print(f"├── GPU Device Count: {torch.cuda.device_count()}")
                print(f"├── Current Device: {torch.cuda.current_device()}")
                print(f"├── Device Name: {torch.cuda.get_device_name(0)}")
                # Try to create a test tensor on GPU
                try:
                    test_tensor = torch.cuda.FloatTensor([1.])
                    print(f"└── Test tensor created successfully on {test_tensor.device}")
                except Exception as e:
                    print(f"└── Error creating test tensor: {e}")
            else:
                print("└── No CUDA devices available")
            
            if not self.model_size:
                raise ValueError("Model size empty.")
            
            self.status_updated.emit(f"Loading model '{self.model_size}'...")
            
            # Configure device and compute type based on user preference and availability
            use_cuda = torch.cuda.is_available() and self.use_gpu
            device = "cuda" if use_cuda else "cpu"
            compute_type = "float16" if use_cuda else "int8"
            
            # Print configuration
            print("\n[DEVICE] Configuration:")
            print(f"├── Use GPU Setting: {self.use_gpu}")
            print(f"├── Selected Device: {device.upper()}")
            print(f"└── Compute Type: {compute_type}")
            
            # Load the model with explicit device setting
            self.status_updated.emit(f"Initializing model '{self.model_size}' on {device.upper()}...")
            if use_cuda:
                print("\n[MODEL] Loading model on GPU...")
                # Force CUDA device selection
                torch.cuda.set_device(0)
                with torch.cuda.device(0):
                    self.model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
                print(f"[MODEL] Successfully loaded model on GPU (Device: {torch.cuda.current_device()})")
            else:
                print("\n[MODEL] Loading model on CPU...")
                self.model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
                print("[MODEL] Successfully loaded model on CPU")
            
            status_msg = f"Model '{self.model_size}' loaded successfully on {device.upper()}."
            self.status_updated.emit(status_msg)
            return True
            
        except Exception as e:
            error_msg = f"Error loading model: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.error_occurred.emit(error_msg)
            self.model = None
            return False

    def start_audio_monitor(self):
        """Start a separate thread for continuous audio level monitoring."""
        if self.audio_monitor_thread is not None:
            return
            
        def audio_monitor_callback(indata, frames, time, status):
            if self.stop_monitor.is_set():
                raise sd.CallbackAbort
            try:
                audio_data = np.frombuffer(bytes(indata), dtype=np.int16)
                self.process_audio_chunk(audio_data)
            except Exception:
                pass

        try:
            self.audio_monitor_stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                blocksize=CHUNK_SIZE,
                device=self.audio_device,
                channels=1,
                dtype=np.int16,
                callback=audio_monitor_callback
            )
            self.audio_monitor_stream.start()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop_audio_monitor(self):
        """Stop the audio monitoring thread."""
        self.stop_monitor.set()
        if self.audio_monitor_stream is not None:
            try:
                self.audio_monitor_stream.abort()
                self.audio_monitor_stream.close()
            except Exception:
                pass
            finally:
                self.audio_monitor_stream = None
        self.stop_monitor.clear()

    @Slot()
    def start_processing(self):
        if self._is_running:
            return
        if not self.load_model(force_reload=True):
            self.error_occurred.emit("Model failed to load.")
            return

        self._is_running = True
        self.status_updated.emit("Starting...")
        self.audio_buffer = []
        self.recording = False
        self.vad_active = False
        self.frames_since_speech = 0

        # Clear queues
        while True:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                break

        while True:
            try:
                self.text_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                break

        # Start typing thread
        self.stop_typing_event.clear()
        if self.typing_thread_instance and self.typing_thread_instance.is_alive():
            pass
        self.typing_thread_instance = threading.Thread(target=self._typing_loop, daemon=True)
        self.typing_thread_instance.start()

        # Start audio monitor
        self.start_audio_monitor()

        # Setup and start audio stream
        try:
            self.audio_stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                blocksize=CHUNK_SIZE,
                device=self.audio_device,
                channels=1,
                dtype=np.int16,
                callback=self._audio_callback
            )
            self.audio_stream.start()
            self.status_updated.emit("Listening...")
            self.audio_check_timer.start(self.audio_check_interval)
            
        except Exception as e:
            error_msg = f"Audio stream error: {e}"
            self.error_occurred.emit(error_msg)
            self.stop_processing()

    @Slot()
    def stop_processing(self):
        if not self._is_running:
            return
        self.status_updated.emit("Stopping...")
        self._is_running = False
        self.audio_check_timer.stop()

        # Stop audio monitor
        self.stop_audio_monitor()

        if self.audio_stream:
            try:
                self.audio_stream.abort()
                self.audio_stream.close()
            except Exception:
                pass
            finally:
                self.audio_stream = None

        self.stop_typing_event.set()
        if self.typing_thread_instance and self.typing_thread_instance.is_alive():
            self.typing_thread_instance.join(timeout=1.5)
        self.typing_thread_instance = None

        # Clear queues
        while True:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                break

        while True:
            try:
                self.text_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                break

        if self.model:
            try:
                del self.model
                self.model = None
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

        self.recording = False
        self.vad_active = False
        self.audio_buffer = []
        self.status_updated.emit("Idle")

    # --- Internal Methods ---
    def _audio_callback(self, indata, frames, time, status):
        """Handle incoming audio data."""
        if status and status.flags != sd.CallbackFlags.complete:
            return
        if self._is_running:
            try:
                audio_bytes = bytes(indata)
                self.audio_queue.put(audio_bytes)
            except Exception:
                pass

    @Slot()
    def _check_audio_queue(self):
        if not self._is_running: return
        try:
            processed_chunk_count = 0; max_chunks_per_cycle = 5
            while not self.audio_queue.empty() and processed_chunk_count < max_chunks_per_cycle:
                raw_audio_chunk = self.audio_queue.get_nowait(); processed_chunk_count += 1
                try:
                    chunk_np = np.frombuffer(raw_audio_chunk, dtype=np.int16)
                    # Process the audio chunk
                    chunk_np = self.process_audio_chunk(chunk_np)
                    amplitude = np.abs(chunk_np).mean()

                except Exception as e: print(f"Error processing audio chunk: {e}"); continue

                if self._ptt_active:
                    if not self.recording: self.status_updated.emit("Recording (PTT)..."); self.recording = True; self.vad_active = False; self.audio_buffer = []
                    self.audio_buffer.append(chunk_np); self.frames_since_speech = 0; continue
                elif self.recording and not self.vad_active:  # PTT was active but now released
                    self.status_updated.emit("Transcribing...")
                    self.recording = False
                    self._process_audio_buffer()
                    continue
                elif self._vad_enabled:
                    if not self.recording:
                        if amplitude > self.silence_threshold: self.status_updated.emit("Recording (VAD)..."); self.recording = True; self.vad_active = True; self.audio_buffer = []; self.audio_buffer.append(chunk_np); self.frames_since_speech = 0
                    elif self.recording and self.vad_active:
                        if amplitude > self.silence_threshold: self.frames_since_speech = 0; self.audio_buffer.append(chunk_np)
                        else:
                            self.frames_since_speech += 1
                            if self.frames_since_speech > self.silence_frames:
                                self.status_updated.emit("Transcribing...")
                                self.recording = False
                                self.vad_active = False
                                self._process_audio_buffer()
        except queue.Empty: pass
        except Exception as e: error_msg = f"Audio check loop error: {e}"; print(error_msg); self.error_occurred.emit(error_msg)

    def process_audio_chunk(self, audio_chunk):
        """Process an audio chunk and return the processed data."""
        try:
            # Convert to numpy array if needed
            if isinstance(audio_chunk, bytes):
                audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
            elif isinstance(audio_chunk, np.ndarray):
                audio_data = audio_chunk
            else:
                return audio_chunk

            # Calculate RMS volume
            rms = np.sqrt(np.mean(np.square(audio_data.astype(np.float32))))
            
            # Update max volume with decay
            self.max_volume *= self.volume_decay
            if rms > self.min_volume_threshold and rms > self.max_volume:
                self.max_volume = rms
            
            # Ensure we have a minimum max_volume to prevent division by zero
            effective_max = max(self.max_volume, self.min_volume_threshold)
            
            # Calculate normalized volume (0-1 range)
            normalized_raw_volume = min(1.0, rms / effective_max)
            
            # Apply gain if needed
            if self.audio_gain != 1.0:
                audio_data = np.clip(audio_data * self.audio_gain, -32768, 32767).astype(np.int16)
            
            # Calculate processed volume level with same dynamic scaling
            processed_rms = np.sqrt(np.mean(np.square(audio_data.astype(np.float32))))
            normalized_processed_volume = min(1.0, processed_rms / effective_max)

            # --- Throttling and Smoothing ---
            now = time.time()
            if not hasattr(self, '_last_volume_update'):
                self._last_volume_update = 0.0
            if not hasattr(self, '_smoothed_raw_volume'):
                self._smoothed_raw_volume = normalized_raw_volume
            if not hasattr(self, '_smoothed_processed_volume'):
                self._smoothed_processed_volume = normalized_processed_volume
            alpha = self._smoothing_alpha if hasattr(self, '_smoothing_alpha') else 0.3

            # Exponential smoothing
            self._smoothed_raw_volume = alpha * normalized_raw_volume + (1 - alpha) * self._smoothed_raw_volume
            self._smoothed_processed_volume = alpha * normalized_processed_volume + (1 - alpha) * self._smoothed_processed_volume

            # Throttle updates to at most every ~16.7ms (60Hz)
            if now - self._last_volume_update >= 1.0/60.0:
                self.volume_level.emit(self._smoothed_raw_volume)
                self.processed_volume_level.emit(self._smoothed_processed_volume)
                self._last_volume_update = now
            
            return audio_data
            
        except Exception:
            return audio_chunk

    def _process_audio_buffer(self):
        # (Unchanged)
        if not self.audio_buffer: return
        buffer_copy = list(self.audio_buffer); self.audio_buffer = []
        try: audio_data = np.concatenate(buffer_copy); audio_float32 = audio_data.astype(np.float32) / 32768.0
        except ValueError: print("Error concatenating buffer copy."); return
        if audio_float32.size == 0: print("Concatenated audio empty."); return

        start_time = time.time(); transcribed_text = ""
        try:
            if not self.model: self.error_occurred.emit("Model not loaded."); return
            segments, info = self.model.transcribe(audio_float32, beam_size=5, language=self.language_code, temperature=0.0, condition_on_previous_text=False)
            transcribed_text = "".join(segment.text for segment in segments)
        except Exception as e: error_msg = f"Transcription error: {e}"; print(error_msg); self.error_occurred.emit(error_msg); return
        finally:
            if self._is_running and not self.recording and not self._ptt_active:
                self.status_updated.emit("Listening...")
        end_time = time.time()

        processed_text = transcribed_text.strip()
        if processed_text.lower() in self.filter_words: print(f"Filtered out phrase: '{processed_text}'"); return

        if processed_text:
            print(f"Transcribed: {processed_text} (Latency: {end_time - start_time:.2f}s)")
            self.transcription_ready.emit(processed_text)

            text_lower = processed_text.lower(); is_command = False
            if text_lower in self.new_line_commands: insert_new_line(); is_command = True
            if not is_command:
                punc_match = re.match(r"(question mark|exclamation mark|comma|period|full stop|colon|semicolon|open parenthesis|close parenthesis|open bracket|close bracket|open brace|close brace|hyphen|dash|underscore|plus|equals|at|hash|dollar|percent|caret|ampersand|asterisk)", text_lower)
                if punc_match: insert_punctuation(punc_match.group(1)); is_command = True
            if not is_command:
                cmd_match = re.match(r"(delete|remove) last (\d+|one|two|three|four|five|six|seven|eight|nine|ten) words?", text_lower)
                if cmd_match:
                    action, num_str = cmd_match.groups(); num = 0
                    if num_str.isdigit(): num = int(num_str)
                    else: w2n = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}; num = w2n.get(num_str, 0)
                    if action in ("delete", "remove") and num > 0:
                        if delete_last_n_words_direct(num): print(f"Deleted last {num} words.")
                    is_command = True

            # Add Ollama voice command handling
            if not is_command:
                ollama_match = re.match(r"(rewrite|rephrase|reformat|improve|fix|correct|enhance)(?: last)? (\d+|one|two|three|four|five|six|seven|eight|nine|ten) (?:words?|sentences?)", text_lower)
                if ollama_match:
                    action, num_str = ollama_match.groups()
                    if num_str.isdigit(): num = int(num_str)
                    else: w2n = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}; num = w2n.get(num_str, 0)
                    
                    if num > 0:
                        # Get last N words from the text queue
                        last_text = ""
                        try:
                            # Signal that we're processing an Ollama command
                            self.status_updated.emit(f"{action.capitalize()}ing last {num} words...")
                            
                            # Get the text to process from the queue
                            while not self.text_queue.empty():
                                last_text = self.text_queue.get() + last_text
                            
                            # Extract last N words
                            words = last_text.split()
                            if len(words) >= num:
                                text_to_process = " ".join(words[-num:])
                                remaining_text = " ".join(words[:-num])
                                
                                # Put back the remaining text
                                if remaining_text:
                                    self.text_queue.put(remaining_text + " ")
                                
                                # Process with Ollama
                                try:
                                    from ollama_handler import OllamaHandler
                                    ollama = OllamaHandler()
                                    improved_text = ollama.generate_text(
                                        "mistral",  # Default model
                                        f"You are a helpful assistant that improves text. {action.capitalize()} this text to be more clear and professional: {text_to_process}",
                                        text_to_process
                                    )
                                    
                                    if improved_text:
                                        # Put the improved text back in the queue
                                        self.text_queue.put(improved_text.strip() + " ")
                                        print(f"Ollama processed: '{text_to_process}' -> '{improved_text}'")
                                    
                                except Exception as e:
                                    error_msg = f"Ollama processing error: {e}"
                                    print(error_msg)
                                    self.error_occurred.emit(error_msg)
                                
                                finally:
                                    # Reset status
                                    if self._is_running and not self.recording and not self._ptt_active:
                                        self.status_updated.emit("Listening...")
                        
                        except Exception as e:
                            error_msg = f"Error processing Ollama command: {e}"
                            print(error_msg)
                            self.error_occurred.emit(error_msg)
                    
                    is_command = True

            if not is_command: self.text_queue.put(processed_text + " ")

    def _typing_loop(self):
        # (Unchanged)
        print("Typing thread started, ID:", threading.get_ident())
        import pythoncom
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
        try:
            import ctypes, time
            try: from pynput import keyboard; keyboard_controller = keyboard.Controller()
            except ImportError: print("ERROR: pynput not installed."); self.error_occurred.emit("pynput not installed."); return

            while self._is_running and not self.stop_typing_event.is_set():
                try:
                    text_to_type = self.text_queue.get(timeout=0.5)
                    try:
                        hwnd = ctypes.windll.user32.GetForegroundWindow()
                        if hwnd == self.gui_wid: print("Skipping typing: OmniDictate window active."); continue
                        for char in text_to_type:
                            if not self._is_running or self.stop_typing_event.is_set(): break
                            keyboard_controller.press(char)
                            keyboard_controller.release(char)
                            time.sleep(self.char_delay)
                    except Exception as e: error_msg = f"Error typing text: {e}"; print(error_msg); self.error_occurred.emit(error_msg)
                except queue.Empty: continue
                except Exception as e: error_msg = f"Typing queue error: {e}"; print(error_msg); self.error_occurred.emit(error_msg); time.sleep(0.1)
        finally:
            pythoncom.CoUninitialize()
            print("Typing thread exiting, ID:", threading.get_ident())