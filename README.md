# 🤵 Alfred - Your Personal AI Butler

<div align="center">

![Alfred Banner](AlfredPortrait.png)

**A sophisticated, fully local AI assistant with voice control, vision, multi-language support, and conversational memory.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Ollama](https://img.shields.io/badge/Powered%20by-Ollama-orange.svg)](https://ollama.ai)

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Configuration](#️-configuration) • [Contributing](#-contributing)

</div>

---

## 🌟 Features

### 🧠 Advanced AI
- **Mistral 7B** - Powerful language model running completely offline
- **Context-aware conversations** - Remembers topics and maintains coherent dialogue
- **Zero hallucinations** - Grounded responses based on real knowledge
- **Conversation history** - Full memory across sessions

### 👁️ Vision Capabilities
- **LLaVA 7B** integration for image understanding
- Upload images and ask questions about them
- Visual context awareness in conversations

### 🗣️ Voice Control
- **Wake Word Detection** - Just say "Alfred" to activate
- **Push-to-Talk** - Hold spacebar for quick voice input
- **Natural TTS** - High-quality text-to-speech responses
- **Hands-free operation** - True voice assistant experience

### 🌍 Multi-Language Support
- **Automatic language detection**
- **Real-time translation** - Speak in your language, Alfred responds in your language
- **Bilingual display** - See both original and translated text
- **Currently supports**: English, Turkish (extensible to more)

### 💾 Learning & Memory
- **Bulk Learning** - Import training data from JSON/TXT files
- **Conversation Memory** - Learns from your interactions
- **Context Retention** - Remembers what you talked about
- **Custom Training** - Teach Alfred your preferences

### 🎨 Modern Interface
- Beautiful dark theme UI
- Scrollable conversation history
- Real-time status indicators
- Responsive design
- Image upload with preview

---

## 📋 Requirements

- **Python 3.8+**
- **Ollama** (for AI models)
- **Microphone** (for voice input)
- **Windows** (Linux/Mac compatible with minor adjustments)

---

## 🚀 Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/fartodev/Alfred.git
cd Alfred
```

### 2️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Install Ollama & Models
Download Ollama from [ollama.ai](https://ollama.ai), then:
```bash
ollama pull mistral
ollama pull llava
```

### 4️⃣ Initialize Data Files
```bash
# Windows
copy alfred_memory.json.example alfred_memory.json
copy alfred_learning.json.example alfred_learning.json
copy alfred_training.json.example alfred_training.json

# Linux/Mac
cp alfred_memory.json.example alfred_memory.json
cp alfred_learning.json.example alfred_learning.json
cp alfred_training.json.example alfred_training.json
```

### 5️⃣ Launch Alfred
```bash
python app.py
```

Open your browser to **http://localhost:5000**

---

## 💡 Usage

### 🎤 Voice Interaction

**Wake Word Mode:**
1. Say **"Alfred"** to wake him up
2. Speak your question or command
3. Alfred responds with voice and text

**Push-to-Talk:**
1. Hold **Spacebar**
2. Speak while holding
3. Release when done

### 💬 Text Chat
- Type directly in the input box
- Press Enter to send
- Full conversation history displayed

### 📷 Image Analysis
1. Click the 📷 **camera icon**
2. Select an image file
3. Ask questions about the image
4. Alfred will analyze and respond

### 🌐 Language Selection
1. Click the language dropdown in header
2. Select your preferred language (🇬🇧 English / 🇹🇷 Türkçe)
3. Alfred will automatically translate all conversations

### 📚 Bulk Learning
Create training files in this format:

**JSON Format:**
```json
{
  "conversations": [
    {
      "user": "What's your favorite color?",
      "alfred": "I prefer dark themes, sir.",
      "timestamp": "2025-01-01T12:00:00"
    }
  ]
}
```

**TXT Format:**
```
User: How do I install packages?
Alfred: Use pip install <package-name>, sir.

User: What's the weather like?
Alfred: I'm a local AI, sir. I don't have access to weather data.
```

Import via the UI or place files in the project directory.

---

## 🗂️ Project Structure

```
Alfred/
├── 📄 app.py                    # Main Flask backend server
├── 📄 main.py                   # Wake word detection system
├── 📄 translation.py            # Multi-language translation engine
├── 📄 requirements.txt          # Python dependencies
├── 🖼️ AlfredPortrait.png        # Alfred's avatar
│
├── 📁 web/                      # Frontend application
│   ├── templates/
│   │   └── index.html           # Main UI
│   └── static/
│       ├── css/
│       │   └── style.css        # Dark theme styling
│       ├── js/
│       │   └── app.js           # Frontend logic
│       └── sounds/
│           └── wake.mp3         # Wake word sound effect
│
├── 📁 Data Files (created at runtime)
│   ├── alfred_memory.json       # Conversation context
│   ├── alfred_learning.json     # Learned facts
│   └── alfred_training.json     # Training conversations
│
└── 📁 Examples (templates)
    ├── alfred_memory.json.example
    ├── alfred_learning.json.example
    └── alfred_training.json.example
```

---

## ⚙️ Configuration

### Change AI Model
Edit `app.py`:
```python
MODEL_NAME = "mistral"  # Change to any Ollama model
```

### Adjust Voice Settings
Edit `app.py`:
```python
VOICE = "en-US-ChristopherNeural"  # English voice
# Turkish voice is automatically selected when language is Turkish
```

### Add More Languages
Edit `translation.py`:
```python
def detect_language(text):
    # Add your language detection logic
    # Current: English, Turkish
```

### Customize Wake Word
Edit `main.py`:
```python
recorder_config = {
    "wake_words": "alfred",  # Change to your preferred wake word
}
```

---

## 🛡️ Privacy & Security

- ✅ **100% Local** - All AI processing happens on your machine
- ✅ **No cloud dependencies** - Models run offline
- ✅ **Your data stays yours** - Conversations stored locally
- ✅ **Optional translation API** - Only used for multi-language (can be replaced)
- ✅ **No telemetry** - Zero data collection

---

## 🔧 Troubleshooting

### "Ollama not found"
Make sure Ollama is installed and running:
```bash
ollama serve
```

### "Model not found"
Pull the required models:
```bash
ollama pull mistral
ollama pull llava
```

### Microphone not working
- Check microphone permissions
- Ensure microphone is set as default device
- Try push-to-talk mode instead of wake word

### No voice output
- Check system volume
- Verify edge-tts/gTTS installation
- Check browser audio permissions

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. 🐛 **Report bugs** - Open an issue
2. 💡 **Suggest features** - Share your ideas
3. 🔧 **Submit PRs** - Fix bugs or add features
4. 📖 **Improve docs** - Help others understand Alfred

### Development Setup
```bash
git clone https://github.com/fartodev/Alfred.git
cd Alfred
pip install -r requirements.txt
# Make your changes
# Test thoroughly
# Submit PR
```

---

## 📝 Changelog

### Version 2.0 (Current)
- ✨ Multi-language support (Turkish)
- ✨ Image recognition with LLaVA
- ✨ Bulk learning from files
- ✨ Context-aware conversations
- ✨ Improved UI with scrollable chat
- 🐛 Fixed hallucination issues
- 🐛 Fixed time accuracy in responses

### Version 1.0
- Initial release
- Wake word detection
- Push-to-talk
- Mistral 7B integration
- Basic conversation

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

Feel free to use, modify, and distribute as you wish.

---

## 🙏 Credits & Acknowledgments

### Core Technologies
- **[Ollama](https://ollama.ai)** - Local AI model hosting
- **[Mistral AI](https://mistral.ai)** - Mistral 7B language model
- **[LLaVA](https://llava-vl.github.io/)** - Visual understanding
- **[Flask](https://flask.palletsprojects.com/)** - Web framework
- **[RealtimeSTT](https://github.com/KoljaB/RealtimeSTT)** - Wake word detection

### Speech & Translation
- **[edge-tts](https://github.com/rany2/edge-tts)** - Text-to-speech (English)
- **[gTTS](https://github.com/pndurette/gTTS)** - Text-to-speech (Turkish)
- **[langdetect](https://github.com/Mimino666/langdetect)** - Language detection
- **[MyMemory API](https://mymemory.translated.net/)** - Translation service

### UI & Assets
- Dark theme inspired by modern AI assistants
- Icons and styling: Custom CSS
- Alfred portrait: AI-generated

---

## 📧 Contact

**Developer**: Farto  
**GitHub**: [@fartodev](https://github.com/fartodev)  
**Project**: [Alfred Repository](https://github.com/fartodev/Alfred)

---

<div align="center">

**⭐ If you find Alfred useful, please give it a star! ⭐**

Made with ❤️ by the community

</div>
