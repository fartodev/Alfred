import sys
import os
from pathlib import Path

# Fix Windows encoding issues (Turkish locale / cp1254)
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# WORKAROUND: Use CPU for Whisper if CUDA library is missing
# This ensures the system works even without NVIDIA GPU drivers properly configured
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

# Set the path to the alfred.onnx wake word model
PROJECT_ROOT = Path(__file__).parent  # Now main.py is in project root
ALFRED_MODEL_PATH = PROJECT_ROOT / "alfred.onnx"

# Add the project root to environment so openWakeWord can find the model
os.environ['OPENWAKEWORD_MODELS_PATH'] = str(PROJECT_ROOT)

from RealtimeSTT import AudioToTextRecorder
import edge_tts
import asyncio
import os
import subprocess
import winsound
import threading
import ollama

# ============================================================
# VOICE CONFIGURATION - Change this to try different voices
# ============================================================
VOICE = "en-GB-RyanNeural"  # British, mature sounding male voice

# Other voice options to try:
# "en-US-BrianNeural"     - Older, mature sounding male
# "en-US-GuyNeural"       - Casual, mature male
# "en-AU-WilliamNeural"   - Australian, mature male
# ============================================================

def play_audio_in_background(file_path):
    """Play audio file in background thread"""
    try:
        import subprocess
        # Convert MP3 to WAV first using ffmpeg
        wav_file = file_path.replace('.mp3', '.wav')
        
        # Convert with ffmpeg
        subprocess.run(
            ["ffmpeg", "-i", file_path, "-acodec", "pcm_s16le", "-ar", "44100", wav_file, "-y"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10
        )
        
        # Now play the WAV file with winsound
        if os.path.exists(wav_file):
            winsound.PlaySound(wav_file, winsound.SND_FILENAME)
            try:
                os.remove(wav_file)
            except:
                pass
    except Exception as e:
        pass

async def speak_async(text):
    """Text-to-Speech using edge-tts (cloud, high quality voices)"""
    print(f"[ALFRED] {text}")
    try:
        # Generate audio to temporary file
        communicate = edge_tts.Communicate(text, VOICE)
        temp_file = os.path.join(os.getcwd(), "temp_alfred.mp3")
        await communicate.save(temp_file)
        
        # Verify file was created
        if not os.path.exists(temp_file):
            return
        
        # Play in background thread (non-blocking, but in thread so it plays fully)
        thread = threading.Thread(target=play_audio_in_background, args=(temp_file,))
        thread.daemon = True
        thread.start()
        
        # Wait for audio to finish playing (approximate based on text length)
        await asyncio.sleep(len(text) * 0.05 + 1.5)
        
        # Clean up temp file
        try:
            os.remove(temp_file)
        except:
            pass
            
    except Exception as e:
        pass

def speak(text):
    """Wrapper to run async TTS"""
    try:
        asyncio.run(speak_async(text))
    except Exception as e:
        print(f"[TTS ERROR] {e}")

def get_ai_response(user_input):
    """Get response from Llama 3.1 AI"""
    try:
        response = ollama.generate(
            model='llama3.1',
            prompt=user_input,
            stream=False
        )
        return response['response'].strip()
    except Exception as e:
        return f"I encountered an error: {str(e)}"

if __name__ == '__main__':
    print("=" * 70)
    print("ALFRED - Local Voice Assistant (Phase 1+2+3: Ear + Mouth + Brain)")
    print("=" * 70)
    print("\nInitializing Local Voice Assistant...")
    print(f"  Project Root: {PROJECT_ROOT}")
    print(f"  Alfred Model: {ALFRED_MODEL_PATH.name} ({'Found' if ALFRED_MODEL_PATH.exists() else 'NOT FOUND'})")

    # Configuration for OpenWakeWord
    # Ensure you strictly follow the parameter naming from the research 
    
    print("\n[INIT] Creating AudioToTextRecorder...")
    print("  - Model: tiny.en (fast, local)")
    print("  - Compute: NVIDIA CUDA GPU (RTX 3060 Ti)")
    print("  - Backend: openWakeWord")
    print("  - Wake Word Model: alfred.onnx")
    print("  - Wake Word Sensitivity: 0.1 (VERY LOW - catch everything)")
    print("  - Speech Sensitivity: 1.0 (MAXIMUM - detect quiet speech)")
    print("  - Status: Initializing (this may take 10-20 seconds)...")
    
    try:
        recorder = AudioToTextRecorder(
            model="tiny.en", # Use 'tiny.en' for speed, 'small.en' for accuracy
            language="en",
            compute_type="float32",  # GPU acceleration with float32 precision
            device="cuda",  # Explicitly use GPU (NVIDIA CUDA)
            
            # Input Device - explicitly use default
            input_device_index=None,
            
            # Wake Word Config - using EXPLICIT model path
            wakeword_backend="oww",
            openwakeword_model_paths=str(ALFRED_MODEL_PATH),  # Explicitly pass the model file path
            wake_words="alfred",
            wake_words_sensitivity=0.1,  # VERY LOW - detect anything that resembles alfred
            wake_word_buffer_duration=0.5,
            wake_word_timeout=10.0,  # 10 second timeout for wake word
            
            # Voice Activity Detection - MAXIMUM sensitivity
            silero_sensitivity=1.0,  # Maximum: 1.0 = very sensitive
            post_speech_silence_duration=0.3,  # 300ms of silence to detect speech end
            
            # System Config
            spinner=True,
            debug_mode=False,
        )
        print("  - Status: READY!")
        print("\n" + "=" * 70)
        print("System Ready. Say 'Alfred' LOUDLY and CLEARLY")
        print("(GPU Acceleration Enabled - RTX 3060 Ti)")
        print("=" * 70)
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize recorder")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    try:
        while True:
            print("\n[LISTENING] Waiting for wake word 'alfred'...")
            print("(Say 'alfred' now...)")
            # The recorder listens continuously. 
            #.text() blocks execution until a wake word + speech is detected.
            # It returns the transcribed text.
            transcribed_text = recorder.text()
            
            print(f"\n[USER] {transcribed_text}")
            
            # Phase 3: Use AI for intelligent responses
            if "exit" in transcribed_text.lower() or "quit" in transcribed_text.lower():
                speak("Goodbye, Sir. Until next time.")
                print("\n[SHUTDOWN] Goodbye!")
                break
            else:
                # Use Llama 3.1 AI to generate response
                print("[THINKING] Processing with Llama 3.1...")
                ai_response = get_ai_response(transcribed_text)
                
                # Truncate long responses for speech (keep it under 2 minutes)
                if len(ai_response) > 500:
                    ai_response = ai_response[:500] + "..."
                
                speak(ai_response)
                
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by user")
        recorder.shutdown()