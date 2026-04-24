#!/bin/bash
# Roboboy Server Watchdog
# Automatically restarts servers if they crash

LOG_FILE="/tmp/roboboy-watchdog.log"
WORKSPACE="/root/.openclaw/workspace/Huiwen2"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_and_restart() {
    local port=$1
    local name=$2
    local script=$3
    
    if ! ss -tlnp | grep -q ":$port "; then
        log "❌ $name (port $port) is DOWN - Restarting..."
        cd "$WORKSPACE"
        nohup python3 "$script" > "/tmp/${name,,}.log" 2>&1 &
        sleep 2
        
        if ss -tlnp | grep -q ":$port "; then
            log "✅ $name restarted successfully"
        else
            log "❌ Failed to restart $name"
        fi
    fi
}

check_cloudflare() {
    if ! pgrep -x "cloudflared" > /dev/null; then
        log "❌ Cloudflare tunnel is DOWN - Restarting..."
        cloudflared tunnel --url http://localhost:8080 2>&1 &
        sleep 5
        
        if pgrep -x "cloudflared" > /dev/null; then
            log "✅ Cloudflare tunnel restarted successfully"
            # Get and log new URL
            NEW_URL=$(curl -s http://localhost:44447/quickstart 2>/dev/null | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | head -1)
            if [ -n "$NEW_URL" ]; then
                log " New URL: $NEW_URL"
                echo "$NEW_URL" > /tmp/cloudflare-url.txt
            fi
        else
            log "❌ Failed to restart Cloudflare tunnel"
        fi
    fi
}

# Main loop
log " Watchdog started"

while true; do
    # Check servers
    check_and_restart 5004 "STT Server" "stt-server.py"
    check_and_restart 5001 "TTS Server" "tts-server.py"
    check_and_restart 8080 "Voice UI" "voice-server.py"
    
    # Check Cloudflare tunnel
    check_cloudflare
    
    # Wait 30 seconds before next check
    sleep 30
done
