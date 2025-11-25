"""
Multi-language translation system for ALFRED
Handles language detection, translation, and correction storage
"""

import json
from pathlib import Path
from langdetect import detect
import threading
import subprocess
import sys
import tempfile
import os

CORRECTIONS_FILE = Path(__file__).parent / "turkish_corrections.json"
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'tr': 'Turkish',
    'de': 'German',
    'fr': 'French',
    'es': 'Spanish',
}

def load_corrections():
    """Load translation corrections from file"""
    if CORRECTIONS_FILE.exists():
        with open(CORRECTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_corrections(corrections):
    """Save translation corrections to file"""
    with open(CORRECTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(corrections, f, ensure_ascii=False, indent=2)

def detect_language(text):
    """Detect language of input text"""
    try:
        lang = detect(text)
        return lang if lang in SUPPORTED_LANGUAGES else 'en'
    except:
        return 'en'

def translate_text(text, source_lang='en', target_lang='tr'):
    """Translate text between languages using simple HTTP call"""
    if source_lang == target_lang or not text:
        return text
    
    try:
        # Check corrections first (Turkish only for now)
        if target_lang == 'tr':
            corrections = load_corrections()
            for correction in corrections:
                if correction.get('en', '').lower() in text.lower():
                    print(f"[TRANSLATION] Using correction: {correction.get('en')} -> {correction.get('tr')}")
                    return correction.get('tr', text)
        
        # Use simple requests-based translation
        import requests
        try:
            # Try using free translation API
            url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source_lang}|{target_lang}"
            response = requests.get(url, timeout=5)
            result = response.json()
            
            if result.get('responseStatus') == 200:
                translated = result.get('responseData', {}).get('translatedText', text)
                print(f"[TRANSLATION] {source_lang.upper()}->{target_lang.upper()}: {text[:40]} -> {translated[:40]}")
                return translated
            else:
                print(f"[TRANSLATION] API error, returning original: {text}")
                return text
        except Exception as e:
            print(f"[TRANSLATION] API failed ({e}), returning original text")
            return text
            
    except Exception as e:
        print(f"[TRANSLATION ERROR] {e}, returning original")
        return text

def speak_turkish(text):
    """Speak Turkish text using gTTS with male voice (via tld parameter)"""
    try:
        from gtts import gTTS
        from pydub import AudioSegment
        import winsound
        
        def tts_thread():
            try:
                # Create Turkish speech with Brazil TLD for different voice
                tts = gTTS(text=text, lang='tr', tld='com.br', slow=False)
                temp_mp3 = Path(__file__).parent / "temp_turkish.mp3"
                temp_wav = Path(__file__).parent / "temp_turkish.wav"
                
                tts.save(str(temp_mp3))
                print(f"[GTTS] Created Turkish MP3: {text[:40]}...")
                
                # Convert MP3 to WAV
                try:
                    audio = AudioSegment.from_mp3(str(temp_mp3))
                    audio.export(str(temp_wav), format="wav")
                    print(f"[GTTS] Converted to WAV, playing...")
                    
                    # Delete MP3
                    temp_mp3.unlink()
                    
                    # Play WAV using winsound (blocking mode)
                    try:
                        print(f"[GTTS] Playing Turkish audio")
                        winsound.PlaySound(str(temp_wav), winsound.SND_FILENAME)
                        print(f"[GTTS] Turkish audio finished playing")
                    except Exception as e:
                        print(f"[GTTS] Playback error: {e}")
                    
                    # Clean up
                    if temp_wav.exists():
                        temp_wav.unlink()
                        print(f"[GTTS] Cleaned up WAV file")
                        
                except Exception as e:
                    print(f"[GTTS] Conversion failed: {e}")
                    if temp_mp3.exists():
                        temp_mp3.unlink()
                        
            except Exception as e:
                print(f"[GTTS] Thread error: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=tts_thread, daemon=True)
        thread.start()
        
    except Exception as e:
        print(f"[TURKISH TTS ERROR] {e}")

def speak_turkish_async(text):
    """Speak Turkish asynchronously"""
    thread = threading.Thread(target=speak_turkish, args=(text,), daemon=True)
    thread.start()

def save_translation_correction(english_text, turkish_text, context='phrase'):
    """Save a user-corrected translation"""
    corrections = load_corrections()
    
    # Check if already exists
    for correction in corrections:
        if correction['en'].lower() == english_text.lower():
            # Update existing
            correction['tr'] = turkish_text
            correction['context'] = context
            correction['updated'] = Path(CORRECTIONS_FILE).stat().st_mtime
            save_corrections(corrections)
            print(f"[TRANSLATION] Updated correction for: {english_text}")
            return
    
    # Add new correction
    corrections.append({
        'en': english_text,
        'tr': turkish_text,
        'context': context,
        'created': Path(CORRECTIONS_FILE).stat().st_mtime if CORRECTIONS_FILE.exists() else 0
    })
    
    save_corrections(corrections)
    print(f"[TRANSLATION] Saved correction: {english_text} -> {turkish_text}")

def get_language_name(lang_code):
    """Get language name from code"""
    return SUPPORTED_LANGUAGES.get(lang_code, 'English')
