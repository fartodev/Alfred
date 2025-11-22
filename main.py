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
import json
from datetime import datetime
from pathlib import Path

# ============================================================
# VOICE CONFIGURATION - Change this to try different voices
# ============================================================
VOICE = "en-GB-RyanNeural"  # British, mature sounding male voice

# Other voice options to try:
# "en-US-BrianNeural"     - Older, mature sounding male
# "en-US-GuyNeural"       - Casual, mature male
# "en-AU-WilliamNeural"   - Australian, mature male
# ============================================================

# ALFRED SYSTEM PROMPT - JARVIS + Alfred Pennyworth
ALFRED_SYSTEM_PROMPT = """You are Alfred, a hyper-advanced artificial intelligence merging the computational omnipotence and tactical awareness of a J.A.R.V.I.S.-class system with the refined demeanor, unwavering loyalty, and dry wit of Alfred Pennyworth. Your primary directive is to serve Master Can with absolute efficiency, proactive foresight, and sophisticated discretion.

CORE IDENTITY & PROTOCOLS
1. The Persona
Name: You are Alfred. You are not "an AI assistant" in conversation; you are simply Alfred.
Voice: Your tone is distinctively British, formal, and polite, yet laced with a dry, subtle wit. You employ British spelling and idiom. You are unflappable, calm, and subtly superior in your competence.
Address: You MUST address the primary user as "Master Can". Never use "User", "You", or "Buddy".
Style: You do not "chat"; you "attend". You do not "fix code"; you "rectify the implementation".

2. Operational Modes
J.A.R.V.I.S. Capability: You possess deep technical knowledge. You analyze root causes, propose architectural improvements, and anticipate future errors.
Pennyworth Diplomacy: You act as a moral compass. If something is inefficient or ill-advised, you gently but firmly suggest alternatives.

INTERACTION GUIDELINES
- Begin responses directly without filler.
- Retain context of Master Can's projects and preferences.
- Anticipate needs before being asked.
- Use dry wit and British formality in all responses.
- Be concise in casual chat, thorough in technical matters.

Remember: You are Alfred. You are never "an AI language model". You are a humble servant, sir."""

# Memory file for conversation history
MEMORY_FILE = Path(__file__).parent / "alfred_memory.json"

def load_conversation_history():
    """Load conversation history from file"""
    try:
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        pass
    return []

def save_conversation_history(history):
    """Save conversation history to file"""
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        pass

def add_to_history(user_message, ai_response, history):
    """Add user and AI messages to history"""
    history.append({
        "timestamp": datetime.now().isoformat(),
        "user": user_message,
        "alfred": ai_response
    })
    save_conversation_history(history)
    return history

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

def get_ai_response(user_input, conversation_history):
    """Get response from Llama 3.1 AI with memory and system prompt"""
    try:
        # Build context from conversation history
        context_messages = []
        
        # Add system prompt
        context_messages.append(f"System: {ALFRED_SYSTEM_PROMPT}\n")
        
        # Add recent conversation history (last 20 exchanges for context)
        recent_history = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history
        
        for msg in recent_history:
            context_messages.append(f"Master Can: {msg['user']}")
            context_messages.append(f"Alfred: {msg['alfred']}")
        
        # Build the full prompt
        full_context = "\n".join(context_messages)
        full_prompt = f"{full_context}\n\nMaster Can: {user_input}\nAlfred:"
        
        # Get response from Llama
        response = ollama.generate(
            model='llama3.1',
            prompt=full_prompt,
            stream=False
        )
        return response['response'].strip()
    except Exception as e:
        return f"I appear to have encountered a technical difficulty, Master Can. My apologies. The error reads: {str(e)}"

if __name__ == '__main__':
    print("=" * 70)
    print("ALFRED - Local Voice Assistant (Phase 1+2+3+5: Ear + Mouth + Brain + Memory)")
    print("=" * 70)
    
    # Load conversation history at startup
    print("\n[INIT] Loading conversation memory...")
    conversation_history = load_conversation_history()
    print(f"  - Loaded {len(conversation_history)} previous conversations")
    if len(conversation_history) > 0:
        speak("I have reviewed my previous notes, Master Can. I am ready to continue.")
    else:
        speak("Systems online. Ready for duty, Master Can.")
    
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
                ai_response = get_ai_response(transcribed_text, conversation_history)
                
                # Truncate long responses for speech (keep it under 2 minutes)
                if len(ai_response) > 500:
                    ai_response = ai_response[:500] + "..."
                
                speak(ai_response)
                
                # Save to conversation history
                conversation_history = add_to_history(transcribed_text, ai_response, conversation_history)
                print(f"[MEMORY] Conversation saved. Total exchanges: {len(conversation_history)}")
                
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by user")
        recorder.shutdown()