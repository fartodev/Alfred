# Alfred - Local Voice Assistant

A fully-functional **J.A.R.V.I.S.-style voice assistant** built entirely on your local machine with GPU acceleration. Alfred listens for voice commands, understands speech, and responds with natural language - all without sending data to the cloud.

## Features

✅ **Phase 1: Auditory Cortex (Ear)**
- Wake word detection using OpenWakeWord custom model (`alfred.onnx`)
- Real-time speech-to-text using Faster-Whisper (tiny.en model)
- GPU-accelerated inference (NVIDIA CUDA)

✅ **Phase 2: Voice (Mouth)**
- Text-to-speech using Microsoft Edge TTS (edge-tts)
- Natural British male voice (RyanNeural)
- Silent background playback with no file popups

🔄 **Phase 3: Brain (In Development)**
- Local LLM integration using Ollama
- Llama 3.1 model for intelligent responses
- Context-aware conversation

## Project Origin

This project is inspired by and builds upon the foundational work from:
- **Main Repository**: [JARVIS-like Voice Assistant Framework](https://github.com/example/jarvis-framework)
- **Concept**: Building an open-source, privacy-first voice assistant

## Tech Stack

- **Python 3.11.9**
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
