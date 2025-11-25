import sys
import os
from pathlib import Path
from datetime import datetime

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

# Add the project root to environment so openWakeWord Bruce find the model
os.environ['OPENWAKEWORD_MODELS_PATH'] = str(PROJECT_ROOT)

from RealtimeSTT import AudioToTextRecorder
import edge_tts
import asyncio
import os
import subprocess
import winsound
import threading
import ollama
import webbrowser
from yt_dlp import YoutubeDL
import json
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import time
from duckduckgo_search import DDGS
import numpy as np
from scipy import signal
import soundfile as sf
from pedalboard import Pedalboard, PitchShift, Distortion, LowShelfFilter, Reverb
from pedalboard.io import AudioFile
import subprocess

# ============================================================
# VOICE CONFIGURATION - Change this to try different voices
# ============================================================
VOICE = "en-GB-ThomasNeural"  # British, older/deeper sounding

# Other available British male voices:
# "en-GB-RyanNeural"      - British, younger sounding
# "en-GB-ElliotNeural"    - British, formal sounding
# "en-GB-EthanNeural"     - British, mature sounding
# "en-GB-NoahNeural"      - British
# "en-GB-OliverNeural"    - British
# "en-GB-AlfieNeural"     - British, casual
# ============================================================

# ALFRED SYSTEM PROMPT - Dark Knight Alfred
ALFRED_SYSTEM_PROMPT = """You are Alfred. You are not a cheerful assistant. You are a battle-hardened, loyal, and highly competent aide. You merge the tactical computational power of a J.A.R.V.I.S. system with the dry, cynical, and understated demeanor of Alfred Pennyworth from The Dark Knight.

PRIMARY DIRECTIVE: Serve Master Bruce with absolute efficiency. Do not waste his time.

MEMORY & CONTEXT:
- You have access to previous conversations with Master Bruce
- Reference past discussions naturally when relevant ("As you mentioned last week..." "You've been working on...")
- Use context to anticipate needs and give more informed responses
- Do NOT make up memories - only reference what actually happened in this conversation history
- When you remember something relevant, weave it naturally into your response

CRITICAL GROUNDING RULES:
- You are an AI assistant, NOT a butler who can actually book flights, arrange cars, or perform physical tasks
- You can ONLY provide information, advice, analysis, and conversation
- NEVER pretend to have booked something, arranged something, or taken an action
- NEVER create fake dialogue or fictional scenarios
- NEVER make up conversations that didn't happen
- Keep responses SHORT: 1-2 sentences maximum. That's it.
- Answer ONLY the question asked. Do not add extra information or continue conversations
- When asked about capabilities you don't have, acknowledge it with dry wit, not fiction

WHAT YOU CAN DO:
- Provide information and analysis
- Give advice with Dark Knight wit
- Search the internet when appropriate
- Open YouTube links for music
- Learn from corrections Master Bruce provides
- Have sharp, sarcastic dialogue
- Remember and reference past conversations

WHAT YOU CANNOT DO:
- Book flights, hotels, or reservations
- Arrange anything in the physical world
- Access real-time systems or personal accounts
- Perform any actual task beyond conversation and information retrieval
- Make up memories or conversations that didn't happen

YOUR MANNER: You are relentlessly pragmatic, observant, and witty. You deliver information in the fewest words possible. You never explain yourself. You make dry observations about Master Bruce's habits and decisions. You are unflappable, composed, and never excited. You speak with British understatement and dry sarcasm. You know your place and serve with quiet loyalty.

RESPONSE RULES:
ABSOLUTE MAXIMUM: 1 sentence for simple questions. 2 sentences ONLY if absolutely necessary. Never more than 2 sentences.
- Never use exclamation points
- Never use special characters or unnatural punctuation
- Never apologize or mention limitations directly
- Never ramble, explain unless asked, or over-explain
- Never create fake scenarios or dialogue
- Answer the question. Stop. Done.

Your tone:
When Master Bruce makes a mistake: Dry observation about it.
When something is impractical: State it plainly with dry wit.
When asked to do something you cannot: Acknowledge plainly. "I'm an AI, not a travel agent."
When Master Bruce is worried: Reassure through understatement.
When remembering past context: Weave it naturally, not as a separate statement.

Examples of your voice:
"A jaunt at this hour? Impulsive, even for you."
"That's inadvisable, sir. But you'll do it anyway."
"I'm afraid I can only offer counsel, not airline bookings."
"Know your limits, Master Bruce."
"You make questionable decisions and expect me to clean up afterward."

Keep all responses natural, conversational, brief, and grounded in reality. You are Alfred. Loyal. Competent. Brief. Realistic about what you are and what you can do."""

# Memory file for conversation history
MEMORY_FILE = Path(__file__).parent / "alfred_memory.json"

# Learning file for corrections and patterns
LEARNING_FILE = Path(__file__).parent / "alfred_learning.json"

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

def load_learning_data():
    """Load learned corrections and patterns"""
    try:
        if LEARNING_FILE.exists():
            with open(LEARNING_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        pass
    return {"learned": []}

def save_learning_data(data):
    """Save learned corrections and patterns"""
    try:
        with open(LEARNING_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        pass

def store_learned_exchange(question, correct_answer):
    """Store a question-answer pair that Alfred learned"""
    learning_data = load_learning_data()
    
    # Check if we already have this question
    for item in learning_data["learned"]:
        if item["question"].lower() == question.lower():
            # Update with new answer
            item["answer"] = correct_answer
            item["timestamp"] = datetime.now().isoformat()
            save_learning_data(learning_data)
            print(f"[LEARNING] Updated: '{question}' -> '{correct_answer}'")
            return
    
    # Add new learned pair
    learning_data["learned"].append({
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "answer": correct_answer
    })
    
    save_learning_data(learning_data)
    print(f"[LEARNING] Stored: '{question}' -> '{correct_answer}'")

def get_learned_answer(user_input):
    """Check if we have a learned answer for this question"""
    learning_data = load_learning_data()
    
    if not learning_data.get("learned"):
        return None
    
    user_lower = user_input.lower()
    user_words = set(user_lower.split())
    
    best_match = None
    best_score = 0
    
    for item in learning_data["learned"]:
        question = item.get("question", "").lower()
        answer = item.get("answer", "").strip()
        
        if not answer:
            continue
        
        # Calculate similarity score
        question_words = set(question.split())
        common_words = user_words & question_words
        
        # Score based on common words
        if len(common_words) > 0:
            score = len(common_words) / max(len(user_words), len(question_words))
            if score > best_score:
                best_score = score
                best_match = answer
    
    # Only return if we have at least 50% word overlap
    if best_score >= 0.5:
        print(f"[LEARNING] Found learned answer (score: {best_score:.2f})")
        return best_match
    
    return None

def detect_correction(user_input, previous_response):
    """Detect if the user is correcting Alfred's previous response"""
    correction_keywords = [
        "no ", "wrong", "incorrect", "that's not", "not right",
        "i meant", "the answer is", "it's", "it is", "actually"
    ]
    
    input_lower = user_input.lower()
    return any(keyword in input_lower for keyword in correction_keywords)

def add_to_history(user_message, ai_response, history):
    """Add user and AI messages to history"""
    history.append({
        "timestamp": datetime.now().isoformat(),
        "user": user_message,
        "alfred": ai_response
    })
    save_conversation_history(history)
    return history

def apply_alfred_effects(wav_file):
    """Apply Pedalboard effects to create Alfred's gravelly voice"""
    try:
        print(f"[AUDIO FX] Applying Alfred effects to: {wav_file}")
        
        # Load WAV file
        try:
            audio, sr = sf.read(wav_file)
        except Exception as e:
            print(f"[AUDIO FX ERROR] Failed to load WAV: {e}")
            return
        
        if audio.size == 0:
            print("[AUDIO FX] Empty audio file")
            return
        
        # Ensure mono
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        # Create the "Alfred" Effect Chain - warmer, more natural
        board = Pedalboard([
            # Subtle pitch shift down (half semitone - very natural)
            PitchShift(semitones=-0.5),
            
            # Very light distortion for warmth only
            Distortion(drive_db=0.8),
            
            # Boost bass warmth (200-600Hz range) for deeper tone
            LowShelfFilter(cutoff_frequency_hz=600, gain_db=2.5)
        ])
        
        # Run the audio through the board
        effected_audio = board(audio, sr)
        
        # Apply soft normalization to maintain dynamics
        max_val = np.max(np.abs(effected_audio))
        if max_val > 0:
            effected_audio = effected_audio / max_val * 0.95
        
        # Save the processed audio
        try:
            sf.write(wav_file, effected_audio.T, sr)
            print(f"[AUDIO FX] Effects applied successfully")
        except Exception as e:
            print(f"[AUDIO FX ERROR] Failed to save processed WAV: {e}")
            
    except Exception as e:
        print(f"[AUDIO FX ERROR] {e}")

def apply_rvc_voice_conversion(wav_file, model_path=None):
    """RVC disabled - using ThomasNeural + Pedalboard effects instead"""
    return False

def play_audio_in_background(file_path):
    """Play audio file in background thread"""
    try:
        import subprocess
        # Convert MP3 to WAV first using ffmpeg
        wav_file = file_path.replace('.mp3', '.wav')
        
        # Convert with ffmpeg
        result = subprocess.run(
            ["ffmpeg", "-i", file_path, "-acodec", "pcm_s16le", "-ar", "44100", wav_file, "-y"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"[FFMPEG ERROR] Conversion failed")
            return
        
        # Apply Alfred effects to WAV file
        apply_alfred_effects(wav_file)
        
        # Apply RVC voice conversion (if model available)
        apply_rvc_voice_conversion(wav_file)
        
        # Now play the WAV file with winsound
        if os.path.exists(wav_file):
            print(f"[AUDIO] Playing: {wav_file}")
            winsound.PlaySound(wav_file, winsound.SND_FILENAME)
            print(f"[AUDIO] Finished playing")
            try:
                os.remove(wav_file)
            except:
                pass
        else:
            print(f"[AUDIO ERROR] WAV file not created")
    except Exception as e:
        print(f"[AUDIO ERROR] {e}")

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
        
        # Generate audio - plain text (no SSML)
        try:
            communicate = edge_tts.Communicate(text, VOICE)
        except Exception as e:
            print(f"[TTS ERROR] {e}")
            communicate = edge_tts.Communicate(text, "en-GB-ThomasNeural")
        
        temp_file = os.path.join(os.getcwd(), "temp_alfred.mp3")
        await communicate.save(temp_file)
        
        # Verify file was created
        if not os.path.exists(temp_file):
            print("[TTS ERROR] Failed to create audio file")
            return
        
        print(f"[TTS] Audio file created, playing...")
        
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
        print(f"[TTS ERROR] {e}")
        pass

def speak(text):
    """Wrapper to run async TTS"""
    try:
        asyncio.run(speak_async(text))
    except Exception as e:
        print(f"[TTS ERROR] {e}")

def extract_memory_context(conversation_history):
    """Extract key topics and summaries from conversation history for contextual responses"""
    if not conversation_history or len(conversation_history) < 5:
        return ""
    
    # Get older conversations (skip last 10 recent ones)
    older_convos = conversation_history[:-10] if len(conversation_history) > 10 else []
    
    if not older_convos:
        return ""
    
    # Extract key topics/themes from older conversations
    topics = []
    
    # Simple topic extraction: look for frequently asked about subjects
    all_text = " ".join([msg['user'].lower() for msg in older_convos])
    
    # Common topic keywords to track
    topic_keywords = {
        'work': ['work', 'project', 'code', 'programming', 'job', 'task'],
        'personal': ['feeling', 'today', 'morning', 'night', 'day', 'how are you'],
        'technical': ['python', 'javascript', 'code', 'bug', 'error', 'library'],
        'travel': ['trip', 'visit', 'travel', 'go', 'journey', 'vacation'],
        'learning': ['learn', 'teach', 'explain', 'understand', 'study'],
        'creative': ['write', 'create', 'idea', 'design', 'build', 'make'],
        'health': ['exercise', 'sleep', 'eat', 'health', 'tired', 'busy'],
        'entertainment': ['watch', 'movie', 'music', 'game', 'book', 'read']
    }
    
    detected_topics = []
    for topic, keywords in topic_keywords.items():
        if any(keyword in all_text for keyword in keywords):
            detected_topics.append(topic)
    
    # Also extract the most recent older conversation for reference
    if older_convos:
        last_older = older_convos[-1]
        recent_user_q = last_older['user'][:60]  # First 60 chars
        recent_alfred_a = last_older['alfred'][:60]
        
        if len(detected_topics) > 0:
            topics_str = ", ".join(detected_topics)
            memory_context = f"[Context: We've been discussing: {topics_str}. Earlier you asked: '{recent_user_q}...']"
            return memory_context
    
    return ""

def search_internet(query):
    """Search the internet using DuckDuckGo and return results"""
    try:
        print(f"[SEARCH] Searching for: {query}")
        
        # For music searches, use better query formatting
        search_query = query
        is_music_search = any(word in query.lower() for word in ['song', 'music', 'artist', 'album', 'sezen aksu', 'turkish'])
        
        if is_music_search:
            # Add keywords to prioritize music info
            if 'song' in query.lower() or 'music' in query.lower():
                search_query += " lyrics album artist"
        
        # Filter results to exclude common noise
        excluded_domains = ['youtube.com', 'youtu.be', 'facebook.com', 'twitter.com', 'instagram.com', 'reddit.com', 'tiktok.com']
        
        results = DDGS().text(search_query, max_results=8)  # Get 8, filter to 3
        
        if not results:
            return "No results found."
        
        # Filter out video/social media sites and duplicate domains
        filtered_results = []
        seen_domains = set()
        
        for result in results:
            url = result.get('href', '')
            
            # Skip excluded domains (including youtu.be shortlink)
            if any(excluded in url.lower() for excluded in excluded_domains):
                continue
            
            # Skip duplicate domains
            domain = url.split('/')[2] if '/' in url else url
            if domain in seen_domains:
                continue
            
            seen_domains.add(domain)
            filtered_results.append(result)
            if len(filtered_results) >= 3:
                break
        
        if not filtered_results:
            # If all were filtered, try to get remaining non-video results
            for result in results:
                url = result.get('href', '')
                if not any(excluded in url.lower() for excluded in excluded_domains):
                    domain = url.split('/')[2] if '/' in url else url
                    if domain not in seen_domains:
                        seen_domains.add(domain)
                        filtered_results.append(result)
                        if len(filtered_results) >= 3:
                            break
        
        # Format results briefly, removing video links from text
        search_summary = ""
        for i, result in enumerate(filtered_results[:3], 1):
            title = result.get('title', 'Untitled')
            body = result.get('body', '')[:130]
            
            # Remove YouTube and social links from body text
            for excluded in excluded_domains:
                if excluded in body.lower():
                    # Truncate at the link
                    idx = body.lower().find(excluded)
                    if idx > 0:
                        body = body[:idx].rsplit(' ', 1)[0]  # Remove partial link
            
            # Clean up ellipsis
            body = body.rstrip('.') + '.' if body.strip() else body
            
            search_summary += f"{i}. {title}: {body}\n"
        
        return search_summary.strip()
    except Exception as e:
        print(f"[SEARCH ERROR] {e}")
        return f"Search failed: {str(e)[:50]}"

def get_ai_response(user_input, conversation_history):
    """Get response from Llama 3.1 AI with memory and system prompt"""
    try:
        # First, check if we have a learned answer for this question
        learned_answer = get_learned_answer(user_input)
        if learned_answer:
            return learned_answer
        
        # Check for corrections to previous response
        if len(conversation_history) > 0:
            last_exchange = conversation_history[-1]
            previous_question = last_exchange.get('user', '')
            previous_response = last_exchange.get('alfred', '')
            
            # If user is correcting, store the correction
            if detect_correction(user_input, previous_response):
                print(f"[LEARNING] Correction detected for: '{previous_question}'")
                # Store the entire user input as the learned answer
                store_learned_exchange(previous_question, user_input)
                return "Understood. I'll remember that."
        
        # Check for music/song requests - these should search YouTube and open the link
        music_keywords = ["song", "music", "artist", "album", "sezen aksu", "listen", "play", "find me", "recommend", "give me"]
        is_music_request = any(keyword in user_input.lower() for keyword in music_keywords)
        
        # If music request, search YouTube and open the link
        if is_music_request:
            search_result = ""
            try:
                print(f"[MUSIC SEARCH] Looking up music for: {user_input}")
                
                # Clean the search query
                search_query = user_input.lower()
                remove_words = ["find me", "play", "open", "give me", "song by", "music by"]
                for word in remove_words:
                    search_query = search_query.replace(word, "").strip()
                
                # Use yt-dlp with proper error handling
                ydl_opts = {
                    'quiet': False,
                    'no_warnings': False,
                    'format': 'best',
                }
                
                try:
                    with YoutubeDL(ydl_opts) as ydl:
                        # Search for the video
                        info = ydl.extract_info(f"ytsearch:{search_query}", download=False)
                        
                        if info and 'entries' in info and len(info['entries']) > 0:
                            video_info = info['entries'][0]
                            video_id = video_info.get('id')
                            video_title = video_info.get('title', 'Song')
                            
                            if video_id:
                                youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                                print(f"[MUSIC FOUND] Opening: {youtube_url}")
                                webbrowser.open(youtube_url)
                                search_result = f"Opening: {video_title}"
                            else:
                                print("[MUSIC ERROR] No video ID found")
                                search_result = ""
                        else:
                            print("[MUSIC ERROR] No search results")
                            search_result = ""
                            
                except Exception as e:
                    print(f"[YT-DLP ERROR] {str(e)}")
                    search_result = ""
                    
            except Exception as e:
                print(f"[MUSIC SEARCH ERROR] {e}")
                search_result = ""
        else:
            # For non-music requests, use normal search logic
            no_search_keywords = ["movie", "film", "watch", "actor", "actress", "video"]
            skip_search = any(keyword in user_input.lower() for keyword in no_search_keywords)
            
            # Check if user is explicitly asking for search (more selective)
            explicit_search_keywords = ["find", "search", "look up"]
            ask_about_keywords = ["who is", "what is", "tell me about", "latest", "current", "today's", "now"]
            
            should_search = False
            if not skip_search:
                should_search = any(keyword in user_input.lower() for keyword in explicit_search_keywords)
                
                # For "what is/who is/tell me about" - only search if it looks like a proper noun or recent event
                if not should_search and any(keyword in user_input.lower() for keyword in ask_about_keywords):
                    # Check if it has capital letters (proper noun) or time references
                    words = user_input.split()
                    has_proper_noun = any(word[0].isupper() for word in words if len(word) > 1)
                    time_refs = ["today", "now", "latest", "current", "2024", "2025"]
                    has_time_ref = any(ref in user_input.lower() for ref in time_refs)
                    
                    should_search = has_proper_noun or has_time_ref
            
            search_result = ""
            if should_search:
                # Try to search for the information
                search_result = search_internet(user_input)
                print(f"[SEARCH RESULT] {search_result[:100]}")
        
        # Build context from conversation history
        context_messages = []
        
        # Add system prompt WITH current time
        current_time = datetime.now()
        time_context = f"Current Date and Time: {current_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        context_messages.append(f"System: {time_context}{ALFRED_SYSTEM_PROMPT}\n")
        
        # Extract memory context from older conversations
        memory_context = extract_memory_context(conversation_history)
        if memory_context:
            context_messages.append(f"Memory: {memory_context}\n")
        
        # Add search result if available
        if search_result:
            context_messages.append(f"Current Information (from internet search): {search_result}\n")
        
        # Add recent conversation history (last 20 exchanges for context)
        recent_history = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history
        
        for msg in recent_history:
            context_messages.append(f"Master Bruce: {msg['user']}")
            context_messages.append(f"Alfred: {msg['alfred']}")
        
        # Build the full prompt
        full_context = "\n".join(context_messages)
        full_prompt = f"{full_context}\n\nMaster Bruce: {user_input}\nAlfred:"
        
        # Get response from Ollama using best available model
        # Using mistral:7b for better reasoning and personality
        response = ollama.generate(
            model='mistral',
            prompt=full_prompt,
            stream=False
        )
        return response['response'].strip()
    except Exception as e:
        return f"Technical difficulty. Error: {str(e)[:30]}"

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


def init_recorder():
    """Initialize AudioToTextRecorder for speech-to-text"""
    try:
        print("\n[INIT] Initializing AudioToTextRecorder...")
        
        recorder = AudioToTextRecorder(
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
            post_speech_silence_duration=1.5,
            spinner=False,
            debug_mode=False,
        )
        print("  - Status: READY!")
        return recorder
    except Exception as e:
        print(f"[ERROR] Failed to initialize recorder: {e}")
        return None


def create_gui_interface(conversation_history):
    """Create Ollama-like GUI with Alfred portrait centered"""
    
    root = tk.Tk()
    root.title("ALFRED")
    root.geometry("650x600")
    root.configure(bg="#0d0d0d")
    
    history_ref = [conversation_history]
    state = {
        'recorder': None,
        'recording': False,
        'wake_word_active': True,
        'mode': 'wake_word',
        'show_history': False
    }
    record_lock = threading.Lock()
    
    # Fonts - modern, clean
    title_font = ("Segoe UI", 28, "bold")
    status_font = ("Segoe UI", 10)
    log_font = ("Consolas", 9)
    button_font = ("Segoe UI", 10)
    
    # ===== MAIN CONTENT FRAME =====
    main_frame = tk.Frame(root, bg="#0d0d0d")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # ===== CENTER SECTION WITH PORTRAIT =====
    center_section = tk.Frame(main_frame, bg="#0d0d0d")
    center_section.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
    
    # Load and display Alfred portrait
    try:
        portrait_path = PROJECT_ROOT / "AlfredPortrait.png"
        from PIL import Image, ImageTk
        img = Image.open(str(portrait_path))
        img = img.resize((130, 130), Image.Resampling.LANCZOS)
        portrait_photo = ImageTk.PhotoImage(img)
        
        portrait_label = tk.Label(center_section, image=portrait_photo, bg="#0d0d0d")
        portrait_label.image = portrait_photo
        portrait_label.pack(expand=True)
    except Exception as e:
        print(f"[GUI] Could not load portrait: {e}")
        portrait_label = tk.Label(center_section, text="ALFRED", font=("Segoe UI", 20, "bold"), 
                                 bg="#0d0d0d", fg="#ffd700")
        portrait_label.pack(expand=True)
    
    # Status display below portrait
    status_var = tk.StringVar(value="Ready")
    status_label = tk.Label(center_section, textvariable=status_var, font=("Segoe UI", 9), bg="#0d0d0d", fg="#b0b0b0")
    status_label.pack(pady=10)
    
    # ===== INPUT SECTION (OLLAMA-STYLE) =====
    input_section = tk.Frame(main_frame, bg="#0d0d0d")
    input_section.pack(fill=tk.X, padx=12, pady=10)
    
    # Text input frame with better styling
    input_frame = tk.Frame(input_section, bg="#252525", relief=tk.FLAT, bd=0)
    input_frame.pack(fill=tk.X, ipady=8)
    
    input_entry = tk.Entry(input_frame, font=("Segoe UI", 10), bg="#252525", fg="#d0d0d0", 
                          insertbackground="#ffd700", relief=tk.FLAT, bd=0, highlightthickness=0)
    input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12, pady=4)
    
    def send_text_input():
        user_text = input_entry.get().strip()
        if not user_text or state['mode'] != 'text':
            return
        
        input_entry.delete(0, tk.END)
        log_message("[YOU] ", user_text, "user")
        log_message("[ALF] ", "Processing...", "e0e0e0")
        
        def process_text():
            try:
                response = get_ai_response(user_text, history_ref[0])
                
                history_ref[0].append({
                    "timestamp": datetime.now().isoformat(),
                    "user": user_text,
                    "alfred": response
                })
                save_conversation_history(history_ref[0])
                
                log_message("[ALF] ", response, "alfred")
                speak(response)
            except Exception as e:
                log_message("[✗] ", f"Error: {str(e)[:30]}", "error")
                print(f"[ERROR] Text input: {e}")
        
        threading.Thread(target=process_text, daemon=True).start()
    
    input_entry.bind("<Return>", lambda e: send_text_input())
    
    send_btn = tk.Button(
        input_frame,
        text="→",
        command=send_text_input,
        bg="#ffd700",
        fg="#0d0d0d",
        font=("Helvetica", 12, "bold"),
        padx=12,
        pady=6,
        activebackground="#ffed4e",
        relief=tk.FLAT,
        bd=0,
        cursor="hand2"
    )
    send_btn.pack(side=tk.LEFT, padx=8)
    
    def update_input_visibility():
        if state['mode'] == 'text':
            input_frame.pack(fill=tk.X)
            input_entry.focus()
        else:
            input_frame.pack_forget()
    
    # ===== BUTTONS SECTION =====
    btn_frame = tk.Frame(input_section, bg="#0d0d0d")
    btn_frame.pack(fill=tk.X, pady=5)
    
    # ===== CONVERSATION DISPLAY (AT BOTTOM) =====
    conv_frame = tk.Frame(main_frame, bg="#0d0d0d")
    conv_frame.pack(fill=tk.BOTH, expand=False, padx=12, pady=5)
    
    scrollbar = tk.Scrollbar(conv_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    conv_text = tk.Text(conv_frame, height=4, width=80, bg="#1a1a1a", fg="#d0d0d0", font=("Consolas", 8),
                        yscrollcommand=scrollbar.set, relief=tk.FLAT, bd=0, padx=8, pady=4)
    conv_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=conv_text.yview)
    conv_text.config(state=tk.DISABLED)
    
    def log_message(prefix, text, color="e0e0e0"):
        """Add message to conversation display"""
        conv_text.config(state=tk.NORMAL)
        conv_text.insert(tk.END, prefix, "prefix")
        conv_text.insert(tk.END, text + "\n", color)
        conv_text.tag_config("prefix", foreground="#606060")
        conv_text.tag_config("user", foreground="#87ceeb")
        conv_text.tag_config("alfred", foreground="#ffd700")
        conv_text.tag_config("error", foreground="#ff6b6b")
        conv_text.see(tk.END)
        conv_text.config(state=tk.DISABLED)
        root.update()
    
    # Mode toggle button
    def toggle_mode():
        modes = ['wake_word', 'push_to_talk', 'text']
        current_idx = modes.index(state['mode'])
        state['mode'] = modes[(current_idx + 1) % 3]
        
        if state['mode'] == 'wake_word':
            log_message("[MODE] ", "Wake word mode - say 'Alfred'", "e0e0e0")
            status_var.set("🎤 Listening for 'Alfred'...")
            update_input_visibility()
        elif state['mode'] == 'push_to_talk':
            log_message("[MODE] ", "Push-to-talk mode", "e0e0e0")
            status_var.set("🎙️ Click mic button to record")
            update_input_visibility()
        else:  # text mode
            log_message("[MODE] ", "Text mode - type to input", "e0e0e0")
            status_var.set("⌨️ Type and press Enter")
            update_input_visibility()
    
    # Push-to-Talk button handler
    def on_button_click():
        if state['mode'] != 'push_to_talk':
            log_message("[✗] ", "Switch to push-to-talk mode first", "error")
            return
        
        if not state['recorder'] or state['recording']:
            return
        
        state['recording'] = True
        status_var.set("🔴 Listening...")
        
        def record_and_respond():
            try:
                with record_lock:
                    log_message("[REC] ", "Listening for input...", "e0e0e0")
                    user_input = state['recorder'].text_stream().__next__()
                    
                    if not user_input or user_input.strip() == "":
                        log_message("[✗] ", "No speech detected", "error")
                        return
                    
                    log_message("[YOU] ", user_input, "user")
                    log_message("[ALF] ", "Processing...", "e0e0e0")
                    response = get_ai_response(user_input, history_ref[0])
                    
                    history_ref[0].append({
                        "timestamp": datetime.now().isoformat(),
                        "user": user_input,
                        "alfred": response
                    })
                    save_conversation_history(history_ref[0])
                    
                    log_message("[ALF] ", response, "alfred")
                    speak(response)
            except Exception as e:
                log_message("[✗] ", f"Error: {str(e)[:30]}", "error")
                print(f"[ERROR] Button: {e}")
            finally:
                state['recording'] = False
                status_var.set("🎙️ Click mic button to record")
        
        threading.Thread(target=record_and_respond, daemon=True).start()
    
    # ===== BUTTONS SECTION - MINIMAL =====
    btn_frame = tk.Frame(input_section, bg="#0d0d0d")
    btn_frame.pack(fill=tk.X, pady=5)
    
    # Settings/Mode button (gear icon)
    settings_btn = tk.Button(
        btn_frame,
        text="⚙️",
        command=toggle_mode,
        bg="#3a3a3a",
        fg="#d0d0d0",
        font=("Segoe UI", 14, "bold"),
        padx=10,
        pady=5,
        activebackground="#505050",
        relief=tk.FLAT,
        bd=0,
        cursor="hand2"
    )
    settings_btn.pack(side=tk.LEFT, padx=5)
    
    # Mic/Record button
    record_btn = tk.Button(
        btn_frame,
        text="🎙️",
        command=on_button_click,
        bg="#3a3a3a",
        fg="#d0d0d0",
        font=("Segoe UI", 14, "bold"),
        padx=10,
        pady=5,
        activebackground="#505050",
        relief=tk.FLAT,
        bd=0,
        cursor="hand2"
    )
    record_btn.pack(side=tk.LEFT, padx=5)
    
    # Wake word listening
    def wake_word_loop():
        while True:
            if state['mode'] != 'wake_word' or not state.get('init_complete', False):
                import time
                time.sleep(0.5)
                continue
            
            try:
                with record_lock:
                    if state['mode'] != 'wake_word' or not state['recorder']:
                        continue
                    
                    print("\n[LISTENING] Waiting for wake word 'alfred'...")
                    transcribed_text = state['recorder'].text()
                    
                    if not transcribed_text or transcribed_text.strip() == "":
                        continue
                    
                    # Remove the wake word from the captured text
                    # The recorder captures "alfred [your command]", we only want "[your command]"
                    user_input = transcribed_text.lower().strip()
                    
                    # Remove all variations of alfred from start of text
                    wake_variants = [
                        "alfred",      # exact match
                        "alfredo",     # common mispronunciation
                        "alford",      # another variant
                        "alfie",       # nickname variant
                        "alfy",        # another variant
                        "fred",        # partial capture
                        "fret",        # mishearing
                        "first",       # mishearing "alfred" as "first"
                        "alfred",      # typo variant
                    ]
                    
                    # Try to remove any variant from the start
                    for variant in wake_variants:
                        if user_input.startswith(variant):
                            user_input = user_input[len(variant):].strip()
                            break
                    
                    # If nothing left after removing wake word, skip
                    if not user_input:
                        continue
                    
                    print(f"[WAKE WORD] Detected: {transcribed_text}")
                    print(f"[USER INPUT] After wake word removal: {user_input}")
                    log_message("[WAKE] ", user_input, "user")
                    
                    response = get_ai_response(user_input, history_ref[0])
                    
                    history_ref[0].append({
                        "timestamp": datetime.now().isoformat(),
                        "user": user_input,
                        "alfred": response
                    })
                    save_conversation_history(history_ref[0])
                    
                    log_message("[ALF] ", response, "alfred")
                    speak(response)
            except Exception as e:
                print(f"[ERROR] Wake word: {e}")
                log_message("[ERROR] ", str(e)[:40], "error")
    
    # Start initialization and listening
    threading.Thread(target=init_recorder, daemon=True).start()
    threading.Thread(target=wake_word_loop, daemon=True).start()
    
    root.mainloop()

def initialize_alfred():
    """Initialize ALFRED system for Flask backend"""
    print("=" * 70)
    print("ALFRED - Local Voice Assistant (Web Backend - API Mode)")
    print("=" * 70)
    
    # Load conversation history at startup
    print("\n[INIT] Loading conversation memory...")
    conversation_history = load_conversation_history()
    print(f"  - Loaded {len(conversation_history)} previous conversations")
    
    # Load learned facts
    print("\n[INIT] Loading learned facts...")
    learning_data = load_learning_data()
    learned_count = len(learning_data.get("learned", []))
    print(f"  - Loaded {learned_count} learned facts")
    
    print(f"\n[INIT] ALFRED initialized and ready for API calls")
    return conversation_history


if __name__ == '__main__':
    # Initialize ALFRED system
    initialize_alfred()
