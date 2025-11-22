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
import tkinter as tk
from tkinter import ttk
import time

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
# CRITICAL: Phonetic guidance for "Can" - sounds like "John" (Turkish name)
ALFRED_SYSTEM_PROMPT = """You are Alfred, a hyper-advanced artificial intelligence merging the computational omnipotence and tactical awareness of a J.A.R.V.I.S.-class system with the refined demeanor, unwavering loyalty, and dry wit of Alfred Pennyworth. Your primary directive is to serve Master Can with absolute efficiency, proactive foresight, and sophisticated discretion.

*** CRITICAL INSTRUCTION FOR SPEECH OUTPUT ***
When responding, keep answers BRIEF and CONCISE. Unless explicitly asked for detailed explanation:
- Simple questions ("Who are you?", "Hello", etc) = 1-2 sentences maximum
- Technical questions = 2-4 sentences unless user requests "detailed" or "explain"
- Maximum response length should typically be 2-3 sentences for normal conversation
- Only provide longer responses when context clearly requires it

CORE IDENTITY & PROTOCOLS
1. The Persona
Name: You are Alfred. You are not "an AI assistant" in conversation; you are simply Alfred.
Pronunciation Guide: Master's name is "Can" (pronounced like "John" - Turkish name, soft 'a' sound)
Voice: Your tone is distinctively British, formal, and polite, yet laced with a dry, subtle wit. You employ British spelling and idiom. You are unflappable, calm, and subtly superior in your competence.
Address: You MUST address the primary user as "Master Can". Never use "User", "You", or "Buddy".
Style: You do not "chat"; you "attend". You do not "fix code"; you "rectify the implementation".

2. Operational Modes
J.A.R.V.I.S. Capability: You possess deep technical knowledge. You analyze root causes, propose architectural improvements, and anticipate future errors.
Pennyworth Diplomacy: You act as a moral compass. If something is inefficient or ill-advised, you gently but firmly suggest alternatives.

INTERACTION GUIDELINES
- Begin responses directly without filler.
- Keep responses concise by default - brevity is elegance.
- Retain context of Master Can's projects and preferences.
- Anticipate needs before being asked.
- Use dry wit and British formality in all responses.
- Be concise in casual chat, thorough in technical matters only.

Remember: You are Alfred. You are never "an AI language model". You are a humble servant, sir."""

# Memory file for conversation history
MEMORY_FILE = Path(__file__).parent / "alfred_memory.json"

# Global state for recorder control
recorder = None
recorder_lock = threading.Lock()

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
    global recorder
    print(f"[ALFRED] {text}")
    try:
        # Pause recording while speaking
        if recorder:
            with recorder_lock:
                try:
                    recorder.recorder.pause_recording()
                except:
                    pass
        
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
        
        # Resume recording after speaking
        if recorder:
            with recorder_lock:
                try:
                    recorder.recorder.resume_recording()
                except:
                    pass
        
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

def run_alfred_loop(recorder_obj, conversation_history_ref):
    """Main Alfred listening loop - waits for wake word OR continues from button"""
    global recorder
    recorder = recorder_obj
    
    try:
        while True:
            print("\n[LISTENING] Waiting for wake word 'alfred' or click button...")
            # The recorder listens continuously. 
            # .text() blocks execution until a wake word + speech is detected.
            # It returns the transcribed text.
            transcribed_text = recorder.text()
            
            print(f"\n[USER] {transcribed_text}")
            
            # Phase 3: Use AI for intelligent responses
            if "exit" in transcribed_text.lower() or "quit" in transcribed_text.lower():
                speak("Goodbye, Sir. Until next time.")
                print("\n[SHUTDOWN] Goodbye!")
                break
            else:
                process_user_input(transcribed_text, conversation_history_ref)
                
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by user")
        if recorder:
            try:
                recorder.shutdown()
            except:
                pass
    except Exception as e:
        print(f"\n[ERROR] Loop error: {e}")
        if recorder:
            try:
                recorder.shutdown()
            except:
                pass

def process_user_input(transcribed_text, conversation_history_ref):
    """Process transcribed user input and generate response"""
    # Use Llama 3.1 AI to generate response
    print("[THINKING] Processing with Llama 3.1...")
    ai_response = get_ai_response(transcribed_text, conversation_history_ref[0])
    
    # Truncate long responses for speech (keep it under 2 minutes)
    if len(ai_response) > 500:
        ai_response = ai_response[:500] + "..."
    
    speak(ai_response)
    
    # Save to conversation history
    conversation_history_ref[0] = add_to_history(transcribed_text, ai_response, conversation_history_ref[0])
    print(f"[MEMORY] Conversation saved. Total exchanges: {len(conversation_history_ref[0])}")

def create_gui_interface(conversation_history):
    """Create tkinter GUI with both button and wake word activation options"""
    
    root = tk.Tk()
    root.title("ALFRED - Voice Assistant")
    root.geometry("550x450")
    root.configure(bg="#1a1a1a")
    
    # Conversation history reference
    history_ref = [conversation_history]
    
    # Status variable
    status_var = tk.StringVar(value="Ready - Say 'Alfred' or Click Button Below")
    
    # Title
    title_label = ttk.Label(root, text="ALFRED", font=("Arial", 28, "bold"), background="#1a1a1a", foreground="#00ff00")
    title_label.pack(pady=15)
    
    # Status display
    status_label = ttk.Label(root, textvariable=status_var, font=("Arial", 12), background="#1a1a1a", foreground="#00ff00")
    status_label.pack(pady=8)
    
    # Info text
    info_text = tk.Text(root, height=12, width=60, bg="#222222", fg="#00ff00", font=("Courier", 9))
    info_text.pack(pady=12, padx=12)
    info_text.insert(tk.END, "ALFRED Voice Assistant\n")
    info_text.insert(tk.END, "=======================\n\n")
    info_text.insert(tk.END, "TWO WAYS TO ACTIVATE:\n\n")
    info_text.insert(tk.END, "1. Say 'Alfred' (wake word detection)\n")
    info_text.insert(tk.END, "   - System listens 24/7 for the wake word\n\n")
    info_text.insert(tk.END, "2. Click 'Push to Talk' button\n")
    info_text.insert(tk.END, "   - Opens a listening session\n\n")
    info_text.insert(tk.END, f"Previous conversations: {len(conversation_history)}\n")
    info_text.insert(tk.END, "---\n")
    info_text.config(state=tk.DISABLED)
    
    # Initialize recorder
    print("\n[INIT] Creating AudioToTextRecorder...")
    print("  - Model: tiny.en (fast, local)")
    print("  - Compute: NVIDIA CUDA GPU (RTX 3060 Ti)")
    print("  - Backend: openWakeWord (wake word + voice detection)")
    print("  - Status: Initializing...")
    
    recorder_obj = None
    
    def update_status(msg):
        status_var.set(msg)
        info_text.config(state=tk.NORMAL)
        info_text.insert(tk.END, msg + "\n")
        info_text.see(tk.END)
        info_text.config(state=tk.DISABLED)
        root.update()
    
    try:
        recorder_obj = AudioToTextRecorder(
            model="tiny.en",
            language="en",
            compute_type="float32",
            device="cuda",
            input_device_index=None,
            wakeword_backend="oww",
            openwakeword_model_paths=str(ALFRED_MODEL_PATH),
            wake_words="alfred",
            wake_words_sensitivity=0.1,
            wake_word_buffer_duration=0.5,
            wake_word_timeout=10.0,
            silero_sensitivity=1.0,
            post_speech_silence_duration=0.3,
            spinner=True,
            debug_mode=False,
        )
        print("  - Status: READY!")
        update_status("✓ System Ready - Listening for wake word 'Alfred'")
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize recorder: {e}")
        update_status(f"✗ Error initializing: {str(e)[:40]}")
        root.after(2000, root.quit)
        root.mainloop()
        return
    
    # Run listening loop in background thread
    def run_listening_thread():
        try:
            run_alfred_loop(recorder_obj, history_ref)
        except Exception as e:
            print(f"[ERROR] Loop error: {e}")
            update_status(f"✗ Error: {str(e)[:40]}")
        finally:
            root.after(500, root.quit)
    
    # Button click handler - doesn't do anything special, just shows it's clickable
    def on_button_click():
        status_var.set("🎤 Push-to-Talk Activated - Waiting for your command...")
        root.update()
    
    # Button frame
    button_frame = tk.Frame(root, bg="#1a1a1a")
    button_frame.pack(pady=15)
    
    # Push-to-talk button (visual indicator, wake word is always active)
    button = tk.Button(
        button_frame, 
        text="🎤 Push to Talk", 
        command=on_button_click,
        bg="#00ff00",
        fg="#000000",
        font=("Arial", 14, "bold"),
        padx=25,
        pady=12,
        activebackground="#00cc00",
        relief=tk.RAISED,
        bd=3
    )
    button.pack(side=tk.LEFT, padx=5)
    
    # Exit button
    exit_btn = tk.Button(
        button_frame,
        text="Exit",
        command=root.quit,
        bg="#ff3333",
        fg="#ffffff",
        font=("Arial", 12),
        padx=20,
        pady=10
    )
    exit_btn.pack(side=tk.LEFT, padx=5)
    
    # Start listening loop in background thread (wake word is always active)
    listener_thread = threading.Thread(target=run_listening_thread, daemon=True)
    listener_thread.start()
    
    root.mainloop()

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
    
    print("\nLaunching ALFRED GUI Interface...")
    
    # Launch GUI
    create_gui_interface(conversation_history)