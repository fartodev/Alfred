# ALFRED - Private AI Butler

A sophisticated local AI assistant inspired by Batman's butler. Runs entirely offline using Mistral 7B and LLaVA for vision.

## Current Features (Phase 3 - Complete)

✅ **Core AI**
- Mistral 7B model (local, powerful)
- 299+ conversations with context memory
- Hallucination prevention with grounding rules
- Dark Knight butler personality training (46 dialogue patterns)

✅ **Input Methods**
- Wake word detection ("Alfred")
- Push-to-talk (Web Speech API)
- Text input mode

✅ **Output & Personality**
- TTS with Thomas neural voice
- Real-time responses
- Context-aware butler replies

✅ **Vision**
- LLaVA local image analysis
- Image + text together support
- Screenshot analysis capability

✅ **Learning System**
- Bulk import from .json/.txt files
- Conversation memory with topic detection
- User correction learning

✅ **UI/UX**
- Modern dark theme
- Scrollable chat with visible scrollbar
- System log panel
- Mode indicators
- Image preview with camera button

## Architecture
- **Speech-to-Text**: Faster-Whisper + CTranslate2 (NVIDIA CUDA 11.8)
- **Text-to-Speech**: edge-tts (Microsoft cloud voices)
- **Wake Word**: OpenWakeWord with custom `alfred.onnx` model
- **GPU**: NVIDIA RTX 3060 Ti (12GB VRAM)
- **Audio**: PyAudio, winsound
- **Framework**: RealtimeSTT

## Quick Start

### Prerequisites
- Windows 10/11
- Python 3.10+
- NVIDIA GPU with CUDA support (optional but recommended)
- FFmpeg installed

### Installation

1. Clone the repository:
```bash
git clone https://github.com/fartodev/Alfred.git
cd Alfred
```

2. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run Alfred:
```bash
python main.py
```

## Usage

1. Say **"Alfred"** loudly and clearly
2. Wait for the listening tone
3. Speak your command or question
4. Alfred will respond in his British old man voice

### Example Commands
- "What time is it?"
- "Hello, how are you?"
- "Exit" (to shutdown)

## Project Structure

```
Alfred/
├── main.py              # Main application entry point
├── alfred.onnx          # Custom wake word model
├── venv/               # Python virtual environment
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Roadmap

- **Phase 1**: ✅ Auditory Cortex (Speech-to-Text)
- **Phase 2**: ✅ Voice Output (Text-to-Speech)
- **Phase 3**: 🔄 Brain (Local LLM with Ollama)
- **Phase 4**: ⏳ Agent (Open Interpreter integration)
- **Phase 5**: ⏳ Polish (Barge-in, long-term memory, personality)

## Developer

**Can** - Student Developer
- GitHub: [@fartodev](https://github.com/fartodev)

## License

This project is open source and available under the MIT License.

## Troubleshooting

### No Audio Output
- Check Windows Sound Settings
- Ensure speakers are connected and unmuted
- Verify FFmpeg is installed

### Wake Word Not Detecting
- Speak clearly and loudly
- Check microphone input device in Windows Sound Settings
- Ensure `alfred.onnx` model file exists in project root

### GPU Not Being Used
- Install NVIDIA CUDA 11.8 or compatible version
- Verify PyTorch can detect GPU: `python -c "import torch; print(torch.cuda.is_available())"`

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

- OpenWakeWord for wake word detection
- Faster-Whisper for fast speech recognition
- edge-tts for natural text-to-speech
- RealtimeSTT for real-time audio processing

---

**Status**: Phase 2 Complete | Active Development

Last Updated: November 22, 2025
