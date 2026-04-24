#!/bin/bash
# Start all Roboboy voice chat servers

echo "🚀 Starting Roboboy Voice Chat Servers..."
echo ""

# Check if Python packages are installed
echo "📦 Checking dependencies..."
pip3 install -q -r requirements.txt 2>/dev/null || pip install -q -r requirements.txt

# Start STT server in background
echo "🎤 Starting STT server on port 5000..."
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
python3 stt-server.py &
STT_PID=$!
sleep 2

# Start TTS server in background
echo "🔊 Starting TTS server on port 5001..."
python3 tts-server.py &
TTS_PID=$!
sleep 2

# Start voice server (main server with UI + proxy)
echo "🎤 Starting voice server on port 8080..."
python3 voice-server.py &
VOICE_PID=$!
sleep 2

echo ""
echo "✅ All servers started!"
echo ""
echo "📱 Open: http://localhost:8080/"
echo "🎤 STT:  http://localhost:5000/transcribe"
echo "🔊 TTS:  http://localhost:5001/tts"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for interrupt
trap "kill $STT_PID $TTS_PID $VOICE_PID 2>/dev/null; echo 'Servers stopped'; exit" INT

wait
