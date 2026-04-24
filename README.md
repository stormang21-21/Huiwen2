# Roboboy2 - Singaporean Voice Chat Assistant

A voice chat application with **Singapore English TTS** and **Whisper STT**.

## Features

- 🎤 **Voice Input** - Tap microphone to speak
- 🎙️ **Speech-to-Text** - OpenAI Whisper API (or local Whisper)
- 🔊 **Singapore English TTS** - Natural sounding responses (Luna voice)
- 🌏 **Multiple Voices** - UK, US, Australian, Singapore English
- 📱 **Mobile Friendly** - Works on any device with a browser
- 🔄 **Real-time** - Low latency voice-to-voice responses

## Quick Start

```bash
# Install dependencies
pip3 install --break-system-packages edge-tts flask flask-cors

# Start all servers
./start.sh

# Or start individually:
python3 tts-server.py      # TTS server (port 5001)
python3 voice-server.py    # Main server (port 8080)
```

## Usage

1. Open `http://localhost:8080/` in your browser
2. Tap the microphone button
3. Speak your message
4. Tap again to stop recording
5. Listen to Roboboy's response!

## API Endpoints

### STT Server (port 5000)

```bash
# Transcribe audio file (multipart form data)
curl -X POST http://localhost:5000/transcribe \
  -F "file=@audio.webm"

# Transcribe base64 audio
curl -X POST http://localhost:5000/transcribe/json \
  -H "Content-Type: application/json" \
  -d '{"audio": "base64_encoded_audio_data"}'

# Health check
curl http://localhost:5000/health
```

**STT Configuration:**
- Set `OPENAI_API_KEY` environment variable for Whisper API
- Or set `USE_LOCAL_WHISPER = True` in `stt-server.py` for local Whisper

### TTS Server (port 5001)

```bash
# Generate speech (returns audio file)
curl -X POST http://localhost:5001/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello!", "voice": "singapore"}' \
  --output speech.mp3

# Generate speech (returns base64)
curl -X POST http://localhost:5001/tts/json \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello!", "voice": "singapore"}'

# List available voices
curl http://localhost:5001/voices
```

### Available Voices

| ID | Voice | Description |
|----|-------|-------------|
| `singapore` | en-SG-LunaNeural | Singapore English (female) - Default |
| `singapore-male` | en-SG-WayneNeural | Singapore English (male) |
| `uk` | en-GB-SoniaNeural | UK English |
| `us` | en-US-JennyNeural | US English |
| `australia` | en-AU-NatashaNeural | Australian English |

## Architecture

```
Browser (port 8080)
  ├─> voice-server.py (UI + proxy)
  │    ├─> Static files (voice-chat-v2.html)
  │    ├─> /tts/* → TTS server (port 5001)
  │    └─> /api/* → OpenClaw Gateway (port 18789)
  │
  └─> TTS responses → Edge TTS → Singapore English audio
```

## Files

- `voice-chat-v2.html` - Main UI with TTS integration
- `voice-server.py` - Main server (UI + proxy)
- `tts-server.py` - Microsoft Edge TTS server
- `whisper-server.py` - Whisper STT server (optional)
- `start.sh` - One-command startup script

## Deployment

### Local Development
```bash
./start.sh
```

### With ngrok (HTTPS)
```bash
# Start servers
./start.sh

# Create ngrok tunnel
ngrok http 8080

# Share the HTTPS URL
```

## Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS
- **Backend**: Python (Flask + edge-tts)
- **TTS**: Microsoft Edge TTS (free, high quality)
- **STT**: OpenAI Whisper (local or API)
- **Proxy**: Custom Python HTTP server

## License

MIT
