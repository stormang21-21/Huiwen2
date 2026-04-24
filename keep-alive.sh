#!/bin/bash
# Keep Roboboy servers alive

echo "🔄 Checking server status..."

# Kill any existing processes
pkill -f "stt-server.py" 2>/dev/null
pkill -f "tts-server.py" 2>/dev/null
pkill -f "voice-server.py" 2>/dev/null
pkill -f "cloudflared" 2>/dev/null
sleep 2

# Start servers
cd /root/.openclaw/workspace/Huiwen2

echo "🎤 Starting STT server..."
nohup python3 stt-server.py > /tmp/stt.log 2>&1 &
sleep 1

echo "🔊 Starting TTS server..."
nohup python3 tts-server.py > /tmp/tts.log 2>&1 &
sleep 1

echo "🌐 Starting Voice UI server..."
nohup python3 voice-server.py > /tmp/voice.log 2>&1 &
sleep 2

echo "🔗 Starting Cloudflare tunnel..."
cloudflared tunnel --url http://localhost:8080 2>&1 &
sleep 5

# Get tunnel URL
TUNNEL_URL=$(curl -s http://localhost:44447/quickstart 2>/dev/null | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | head -1)

echo ""
echo "✅ All servers started!"
echo ""
echo "📱 Voice UI: http://146.190.97.153:8080/"
echo "🔗 HTTPS: $TUNNEL_URL"
echo ""
echo "📊 Status:"
ss -tlnp | grep -E '5001|5004|8080'
