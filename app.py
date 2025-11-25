"""
ALFRED - Flask Web Server Backend
Provides REST API for the web UI
"""

from flask import Flask, request, jsonify, render_template, send_file
from pathlib import Path
import json
import threading
from datetime import datetime
import sys
import os
import base64
import io
from PIL import Image
import ollama

# Import core Alfred functions from main.py
sys.path.insert(0, str(Path(__file__).parent))

# Import translation system
from translation import detect_language, translate_text, speak_turkish_async, save_translation_correction, get_language_name

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')

# Global state
state = {
    'conversation_history': [],
    'recording': False,
    'mode': 'wake_word',  # wake_word, push_to_talk, text
    'recorder': None,
    'ppt_recorder': None,  # Separate recorder for push-to-talk without wake word
    'init_complete': False,
    'last_transcription': '',
    'ppt_transcription': '',
    'ppt_response_ready': False,
    'wake_word_triggered': False,
    'greeting_said': False,
    'pending_recording_audio': None,
    'ptt_thread': None,
    'ptt_active': False,
    'wake_word_stop': False,
    'recorder_lock': threading.Lock(),
    'language': 'en',  # Current language (en, tr, de, fr, es)
    'last_english_response': '',  # Store for bilingual display
}

def wake_word_listener():
    """Background thread that listens for wake word"""
    if not state['recorder']:
        return
    
    try:
        print("[WAKE WORD] Starting listener thread...")
        while not state['wake_word_stop']:
            # Only actually listen when in wake-word mode
            if state['mode'] != 'wake_word':
                threading.Event().wait(0.1)
                continue
            
            # Use lock to ensure exclusive access to recorder
            with state['recorder_lock']:
                if state['mode'] != 'wake_word' or state['wake_word_stop']:
                    break
                    
                try:
                    print("[WAKE WORD] Listening for 'Alfred'...")
                    text = state['recorder'].text()
                    
                    if text and not state['wake_word_stop'] and state['mode'] == 'wake_word':
                        state['last_transcription'] = text
                        print(f"[TRANSCRIBED] {text}")
                        
                        from main import get_ai_response, speak, save_conversation_history
                        
                        response = get_ai_response(text, state['conversation_history'])
                        state['conversation_history'].append({
                            "timestamp": datetime.now().isoformat(),
                            "user": text,
                            "alfred": response
                        })
                        save_conversation_history(state['conversation_history'])
                        
                        # Speak response
                        threading.Thread(target=speak, args=(response,), daemon=True).start()
                except Exception as e:
                    if not state['wake_word_stop']:
                        print(f"[WAKE WORD ERROR] {e}")
        print("[WAKE WORD] Listener thread stopped")
    except Exception as e:
        print(f"[WAKE WORD LISTENER ERROR] {e}")

def push_to_talk_handler():
    """Handle push-to-talk recording in a separate thread"""
    # Use the PTT recorder (without wake word detection) if available
    recorder_to_use = state['ppt_recorder'] if state['ppt_recorder'] else state['recorder']
    
    if not recorder_to_use:
        print("[PTT] No recorder available")
        state['ptt_active'] = False
        return
    
    try:
        print("[PTT] Handler: Waiting for speech...")
        
        # Wait for exclusive access to recorder
        with state['recorder_lock']:
            if not state['ptt_active']:
                print("[PTT] PTT cancelled")
                return
                
            print("[PTT] Handler: Got recorder lock, calling text()...")
            # Set a timeout for recorder.text() - max 30 seconds of listening
            try:
                print("[PTT] About to call recorder.text() on PTT recorder...")
                text = recorder_to_use.text()
                print(f"[PTT] recorder.text() returned: type={type(text)}, len={len(text) if text else 0}, value='{text}'")
            except Exception as record_error:
                print(f"[PTT] Recorder error: {record_error}")
                import traceback
                traceback.print_exc()
                text = ""
            print(f"[PTT] Handler: Got response from recorder: '{text}'")
        
        if text and text.strip():
            print(f"[PTT TRANSCRIBED] {text}")
            state['ptt_transcription'] = text
            state['last_transcription'] = text
            
            from main import get_ai_response, speak, save_conversation_history
            
            # Get response
            response = get_ai_response(text, state['conversation_history'])
            state['conversation_history'].append({
                "timestamp": datetime.now().isoformat(),
                "user": text,
                "alfred": response
            })
            save_conversation_history(state['conversation_history'])
            state['ppt_response_ready'] = True  # Signal UI to refresh - stays True until next recording
            
            # Speak response
            threading.Thread(target=speak, args=(response,), daemon=True).start()
            
            print("[PTT] Response processed")
        else:
            print(f"[PTT] Handler: Got empty text: '{text}'")
            print("[PTT] No speech detected")
    except Exception as e:
        print(f"[PTT HANDLER ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[PTT] Handler: Cleaning up")
        state['ptt_active'] = False
        state['recording'] = False

# Load conversation history on startup
def load_conversation_history():
    """Load conversation history from file"""
    try:
        memory_file = Path(__file__).parent / "alfred_memory.json"
        if memory_file.exists():
            with open(memory_file, 'r') as f:
                state['conversation_history'] = json.load(f)
                return state['conversation_history']
    except Exception as e:
        print(f"[ERROR] Failed to load conversation history: {e}")
    return []

# API Routes

@app.route('/')
def index():
    """Serve the main web UI"""
    return render_template('index.html')

@app.route('/portrait')
def get_portrait():
    """Serve Alfred's portrait image"""
    portrait_path = Path(__file__).parent / "AlfredPortrait.png"
    if portrait_path.exists():
        return send_file(str(portrait_path), mimetype='image/png')
    return jsonify({'error': 'Portrait not found'}), 404

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current system status"""
    return jsonify({
        'status': 'ready' if state['init_complete'] else 'initializing',
        'mode': state['mode'],
        'recording': state['recording'],
        'last_transcription': state['last_transcription'],
        'greeting_said': state['greeting_said'],
        'ptt_transcription': state.get('ppt_transcription', ''),
        'ppt_response_ready': state.get('ppt_response_ready', False)
    })

@app.route('/api/greeting', methods=['GET'])
def get_greeting():
    """Get Alfred's startup greeting"""
    if not state['greeting_said']:
        from main import speak
        
        response = "Good morning, Master Bruce."
        state['greeting_said'] = True
        
        # Speak greeting in background
        threading.Thread(target=speak, args=(response,), daemon=True).start()
        
        return jsonify({
            'greeting': response,
            'conversation_count': len(state['conversation_history'])
        })
    
    return jsonify({
        'conversation_count': len(state['conversation_history'])
    })

@app.route('/api/mode', methods=['POST'])
def set_mode():
    """Change input mode"""
    data = request.json
    new_mode = data.get('mode')
    
    if new_mode not in ['wake_word', 'push_to_talk', 'text']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    state['mode'] = new_mode
    return jsonify({'mode': new_mode, 'message': f'Switched to {new_mode} mode'})

@app.route('/api/mode/cycle', methods=['POST'])
def cycle_mode():
    """Cycle through modes"""
    modes = ['wake_word', 'push_to_talk', 'text']
    current_idx = modes.index(state['mode'])
    new_mode = modes[(current_idx + 1) % 3]
    
    old_mode = state['mode']
    state['mode'] = new_mode
    
    # If switching FROM wake word, restart listener when switching back
    if old_mode == 'wake_word' and new_mode != 'wake_word':
        print(f"[MODE] Pausing wake word listener...")
    elif new_mode == 'wake_word':
        print(f"[MODE] Resuming wake word listener...")
    
    mode_names = {
        'wake_word': '🎤 Wake Word',
        'push_to_talk': '🎙️ Push-to-Talk',
        'text': '⌨️ Text Mode'
    }
    
    return jsonify({
        'mode': state['mode'],
        'display': mode_names[state['mode']]
    })

@app.route('/api/chat', methods=['POST'])
def send_message():
    """Send a text message to Alfred with multi-language support"""
    data = request.json
    user_text = data.get('message', '').strip()
    correction_mode = data.get('correction_mode', False)  # Is this a translation correction?
    
    if not user_text:
        return jsonify({'error': 'Empty message'}), 400
    
    from main import get_ai_response, speak, save_conversation_history
    
    try:
        # Detect input language
        detected_lang = detect_language(user_text)
        print(f"[DETECT] User text: '{user_text}' -> Detected language: {detected_lang}")
        
        # Check for translation correction pattern
        if correction_mode and state['last_english_response']:
            # Save the correction
            save_translation_correction(state['last_english_response'], user_text, 'user_correction')
            return jsonify({
                'success': True,
                'message': 'Translation correction saved',
                'user': user_text,
                'alfred': 'Tessekkür ederim. Bundan sonra daha iyi çeviri yapacağım.'
            })
        
        # Translate to English if needed
        if detected_lang != 'en':
            print(f"[TRANSLATE] Converting {detected_lang.upper()} to EN...")
            english_text = translate_text(user_text, source_lang=detected_lang, target_lang='en')
            print(f"[TRANSLATION] {detected_lang.upper()}: {user_text}")
            print(f"[TRANSLATION] EN: {english_text}")
        else:
            english_text = user_text
            detected_lang = 'en'
            print(f"[TRANSLATE] English input, no translation needed")
        
        # Get AI response in English
        response_en = get_ai_response(english_text, state['conversation_history'])
        state['last_english_response'] = response_en
        
        # Store conversation in English
        state['conversation_history'].append({
            "timestamp": datetime.now().isoformat(),
            "user": english_text,
            "alfred": response_en,
            "original_language": detected_lang
        })
        save_conversation_history(state['conversation_history'])
        
        # Translate response if needed
        if detected_lang != 'en':
            print(f"[TRANSLATE] Converting response EN to {detected_lang.upper()}...")
            response = translate_text(response_en, source_lang='en', target_lang=detected_lang)
            print(f"[TRANSLATION] Response to {detected_lang.upper()}: {response}")
            
            # Speak Turkish response
            if detected_lang == 'tr':
                speak_turkish_async(response)
            # Could add other language TTS here
        else:
            response = response_en
            # Speak English response (default)
            threading.Thread(target=speak, args=(response,), daemon=True).start()
        
        # Return bilingual response if Turkish
        result = {
            'user': user_text,
            'alfred': response,
            'timestamp': datetime.now().isoformat(),
            'language': detected_lang
        }
        
        # Include English version for non-English languages
        if detected_lang != 'en':
            result['alfred_en'] = response_en
        
        return jsonify(result)
    except Exception as e:
        print(f"[CHAT ERROR] {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get conversation history"""
    limit = request.args.get('limit', 10, type=int)
    return jsonify(state['conversation_history'][-limit:])

@app.route('/api/bulk-learn', methods=['POST'])
def bulk_learn():
    """Bulk learn from uploaded .txt or .json files"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file content
        content = file.read().decode('utf-8')
        learned_count = 0
        errors = []
        
        from main import save_conversation_history
        
        # Handle .json format
        if file.filename.endswith('.json'):
            try:
                data = json.loads(content)
                
                # Support both array and object formats
                if isinstance(data, list):
                    qa_pairs = data
                elif isinstance(data, dict) and 'conversations' in data:
                    qa_pairs = data['conversations']
                elif isinstance(data, dict) and 'qa' in data:
                    qa_pairs = data['qa']
                else:
                    qa_pairs = [data] if isinstance(data, dict) else []
                
                for item in qa_pairs:
                    if isinstance(item, dict) and ('user' in item or 'question' in item) and ('alfred' in item or 'answer' in item):
                        user_text = item.get('user') or item.get('question')
                        alfred_text = item.get('alfred') or item.get('answer')
                        
                        state['conversation_history'].append({
                            "timestamp": datetime.now().isoformat(),
                            "user": user_text,
                            "alfred": alfred_text,
                            "imported": True
                        })
                        learned_count += 1
                    else:
                        errors.append(f"Invalid Q&A format in item")
                        
            except json.JSONDecodeError as e:
                return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400
        
        # Handle .txt format (one Q&A per line, separated by | or tab)
        elif file.filename.endswith('.txt'):
            lines = content.strip().split('\n')
            for idx, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):  # Skip empty and comment lines
                    continue
                
                # Try to split by | or tab
                if '|' in line:
                    parts = line.split('|', 1)
                elif '\t' in line:
                    parts = line.split('\t', 1)
                else:
                    errors.append(f"Line {idx}: No separator found (use | or tab)")
                    continue
                
                if len(parts) == 2:
                    user_text, alfred_text = parts[0].strip(), parts[1].strip()
                    if user_text and alfred_text:
                        state['conversation_history'].append({
                            "timestamp": datetime.now().isoformat(),
                            "user": user_text,
                            "alfred": alfred_text,
                            "imported": True
                        })
                        learned_count += 1
                    else:
                        errors.append(f"Line {idx}: Empty question or answer")
                else:
                    errors.append(f"Line {idx}: Could not parse Q&A")
        
        else:
            return jsonify({'error': 'Unsupported file format. Use .json or .txt'}), 400
        
        # Save updated history
        save_conversation_history(state['conversation_history'])
        
        return jsonify({
            'success': True,
            'learned': learned_count,
            'total_conversations': len(state['conversation_history']),
            'errors': errors if errors else None
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    """Analyze an image using LLaVA vision model and get Alfred's response"""
    try:
        data = request.json
        image_data = data.get('image')  # base64 encoded image
        
        if not image_data:
            return jsonify({'error': 'No image provided'}), 400
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            return jsonify({'error': f'Invalid image format: {str(e)}'}), 400
        
        # Save temporarily
        temp_image_path = Path(__file__).parent / "temp_analysis.png"
        image.save(temp_image_path)
        
        print(f"[IMAGE] Analyzing image with LLaVA...")
        
        # Analyze with LLaVA using ollama
        try:
            # Read image as base64 for ollama
            with open(temp_image_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            response = ollama.generate(
                model='llava',
                prompt='Please describe what you see in this image in detail. Be specific about objects, people, text, colors, and composition.',
                images=[image_base64],
                stream=False
            )
            
            analysis = response['response'].strip()
            print(f"[IMAGE] Analysis complete: {analysis[:60]}...")
            
            # Clean up temp file
            try:
                temp_image_path.unlink()
            except:
                pass
            
            # Now add to conversation and get Alfred's response
            from main import get_ai_response, save_conversation_history
            
            # Add image analysis to conversation as a system message
            image_message = f"[Image Analysis]: {analysis}"
            state['conversation_history'].append({
                "timestamp": datetime.now().isoformat(),
                "user": image_message,
                "alfred": ""
            })
            
            # Get Alfred's brief response about the image
            alfred_response = get_ai_response(image_message, state['conversation_history'])
            
            # Update the last entry with Alfred's response
            state['conversation_history'][-1]['alfred'] = alfred_response
            save_conversation_history(state['conversation_history'])
            
            print(f"[IMAGE] Alfred responded: {alfred_response}")
            
            return jsonify({
                'analysis': analysis,
                'alfred_response': alfred_response,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            print(f"[IMAGE ERROR] LLaVA analysis failed: {e}")
            import traceback
            traceback.print_exc()
            # Clean up
            try:
                temp_image_path.unlink()
            except:
                pass
            return jsonify({'error': f'Analysis failed: {str(e)}'}), 500
            
    except Exception as e:
        print(f"[IMAGE ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/record/start', methods=['POST'])
def start_recording():
    """Start recording audio for push-to-talk"""
    if state['mode'] != 'push_to_talk':
        return jsonify({'error': 'Not in PTT mode'}), 400
    
    if state['ptt_active']:
        return jsonify({'error': 'Already recording'}), 400
    
    # Clear any stale audio from recorder buffer
    print("[PTT] Clearing recorder buffer...")
    try:
        state['recorder'].end_listening()
        print("[PTT] Recorder buffer cleared")
    except:
        pass
    
    state['recording'] = True
    state['ptt_active'] = True
    state['ptt_transcription'] = ""  # Clear previous transcription
    state['ptt_response_ready'] = False
    
    # Start recording handler in background thread
    state['ptt_thread'] = threading.Thread(target=push_to_talk_handler, daemon=True)
    state['ptt_thread'].start()
    print("[PTT] Recording thread started")
    return jsonify({'status': 'recording'})

@app.route('/api/record/stop', methods=['POST'])
def stop_recording():
    """Stop recording audio"""
    state['recording'] = False
    
    # The handler will finish and set ptt_active to False
    print("[PTT] Stop signal sent")
    return jsonify({'status': 'processing'})

def initialize_system():
    """Initialize Alfred system on startup"""
    print("[WEB] Initializing ALFRED backend...")
    print("=" * 60)
    
    # Load conversation history
    load_conversation_history()
    conversation_count = len(state['conversation_history'])
    print(f"[MEMORY] Loaded {conversation_count} previous conversations")
    print(f"[STATUS] Alfred remembers {conversation_count} conversations with Master Bruce")
    
    # Try to initialize recorder (optional - may fail if audio not available)
    try:
        from main import init_recorder
        state['recorder'] = init_recorder()
        
        # Also initialize PTT recorder without wake word detection
        print("[PTT] Initializing PTT recorder without wake word...")
        try:
            from RealtimeSTT import AudioToTextRecorder
            state['ppt_recorder'] = AudioToTextRecorder(
                model="tiny.en",
                language="en",
                compute_type="float32",
                device="cuda",
                input_device_index=None,
                wake_words=None,  # NO wake word for PTT mode
                silero_sensitivity=1.0,
                post_speech_silence_duration=1.5,
                spinner=False,
                debug_mode=False,
            )
            print("[PTT] PTT recorder initialized successfully")
        except Exception as ptt_e:
            print(f"[PTT] Warning: Could not initialize PTT recorder: {ptt_e}")
            print("[PTT] Will use main recorder for PTT mode")
            state['ppt_recorder'] = None
        
        state['init_complete'] = True
        print("[AUDIO] Audio recorder initialized")
        print("[STATUS] System initialized successfully")
        print("=" * 60)
        print("[WEB] Server ready on http://localhost:5000\n")
        
        # Start wake word listener in background
        wake_word_thread = threading.Thread(target=wake_word_listener, daemon=True)
        wake_word_thread.start()
        print("[WEB] Wake word listener started\n")
    except Exception as e:
        print(f"[AUDIO] Warning: Could not initialize recorder: {e}")
        print("[STATUS] System will work in text-only mode")
        print("=" * 60)
        print("[WEB] Server ready on http://localhost:5000\n")
        state['init_complete'] = True

if __name__ == '__main__':
    print("=" * 60)
    print("ALFRED - Web Backend Server")
    print("=" * 60)
    
    # Initialize
    initialize_system()
    
    # Run Flask server
    print("\n[WEB] Starting server on http://localhost:5000")
    app.run(debug=False, host='localhost', port=5000, threaded=True)
