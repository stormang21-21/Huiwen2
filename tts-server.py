#!/usr/bin/env python3
"""
TTS server using Microsoft Edge TTS
Supports Singapore English (en-SG-LunaNeural) and other voices
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import edge_tts
import asyncio
import tempfile
import os
import uuid

app = Flask(__name__)
CORS(app)

# Available voices
VOICES = {
    # Singapore English
    'singapore': 'en-SG-LunaNeural',
    'singapore-male': 'en-SG-WayneNeural',
    # Australian
    'australia-male': 'en-AU-WilliamMultilingualNeural',
    'australia': 'en-AU-NatashaNeural',
    # Indian
    'india-male': 'en-IN-PrabhatNeural',
    # Philippine
    'philippines-male': 'en-PH-JamesNeural',
    # UK
    'uk': 'en-GB-SoniaNeural',
    # US
    'us': 'en-US-JennyNeural',
    # Chinese (Mandarin)
    'chinese-female': 'zh-CN-XiaoxiaoNeural',
    'chinese-male': 'zh-CN-YunxiNeural',
    # Chinese (Cantonese)
    'cantonese-female': 'zh-HK-HiuGaaiNeural',
    'cantonese-male': 'zh-HK-WanLungNeural',
    # Malay
    'malay-male': 'ms-MY-OsmanNeural',
    # Tamil
    'tamil-male': 'ta-IN-ValluvarNeural',
    'tamil-female': 'ta-IN-PallaviNeural',
}

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """Convert text to speech using Edge TTS"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text'}), 400
        
        text = data['text']
        voice_name = data.get('voice', 'singapore')  # Default to Singapore English
        
        # Get voice ID
        voice = VOICES.get(voice_name, VOICES['singapore'])
        
        # Generate unique filename
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"tts_output_{uuid.uuid4()}.mp3")
        
        # Generate speech asynchronously
        asyncio.run(generate_speech(text, voice, output_path))
        
        # Return the audio file
        return send_file(
            output_path,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name='speech.mp3'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rate limiting - add small delay between requests
import time
_last_request_time = 0
MIN_REQUEST_INTERVAL = 3.0  # Minimum 3 seconds between requests

@app.route('/tts/json', methods=['POST'])
def text_to_speech_json():
    """Convert text to speech, return base64 encoded audio"""
    global _last_request_time
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text'}), 400
        
        text = data['text']
        voice_name = data.get('voice', 'singapore')
        
        voice = VOICES.get(voice_name, VOICES['singapore'])
        
        # Rate limiting - wait if needed
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - elapsed
            print(f"Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"tts_output_{uuid.uuid4()}.mp3")
        
        # Generate speech with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                asyncio.run(generate_speech(text, voice, output_path))
                break
            except Exception as e:
                if "rate" in str(e).lower() or "limit" in str(e).lower():
                    wait_time = (attempt + 1) * 2
                    print(f"Rate limited, retrying in {wait_time}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise
        
        _last_request_time = time.time()
        
        # Read file as base64
        import base64
        with open(output_path, 'rb') as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Cleanup
        os.remove(output_path)
        
        return jsonify({
            'audio': audio_base64,
            'voice': voice,
            'format': 'mp3'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/voices', methods=['GET'])
def list_voices():
    """List available voices"""
    return jsonify({
        'voices': [
            {'id': k, 'name': k.replace('-', ' ').title(), 'voice': v}
            for k, v in VOICES.items()
        ]
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

async def generate_speech(text, voice, output_path, max_retries=3):
    """Generate speech using Edge TTS with retry logic"""
    import time
    
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return  # Success
        except Exception as e:
            if "rate" in str(e).lower() or "limit" in str(e).lower():
                wait_time = (attempt + 1) * 2  # 2s, 4s, 6s
                print(f"Rate limited, waiting {wait_time}s (attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                raise  # Re-raise non-rate-limit errors
    
    raise Exception("TTS failed after multiple retries due to rate limiting")

if __name__ == '__main__':
    print("🔊 Edge TTS Server starting on port 5001...")
    print("Available voices:")
    for name, voice in VOICES.items():
        print(f"  - {name}: {voice}")
    print()
    app.run(host='0.0.0.0', port=5001, debug=False)
