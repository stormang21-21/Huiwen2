#!/usr/bin/env python3
"""
Simple TTS server using Microsoft Edge TTS (no Flask dependency)
Supports Singapore English (en-SG-LunaNeural)
"""

import http.server
import socketserver
import urllib.parse
import json
import asyncio
import tempfile
import os
import uuid
import base64

PORT = 5001

# Available voices
VOICES = {
    'singapore': 'en-SG-LunaNeural',      # Singapore English (female)
    'singapore-male': 'en-SG-WayneNeural', # Singapore English (male)
    'indian': 'hi-IN-SwaraNeural',         # Indian English (female)
    'indian-male': 'hi-IN-MadhurNeural',   # Indian English (male)
    'uk': 'en-GB-SoniaNeural',             # UK English
    'us': 'en-US-JennyNeural',             # US English
    'australia': 'en-AU-NatashaNeural',    # Australian English
    # Chinese voices
    'chinese': 'zh-CN-XiaoxiaoNeural',     # Chinese (female)
    'chinese-male': 'zh-CN-YunxiNeural',   # Chinese (male)
    'chinese-girl': 'zh-CN-XiaoyiNeural',  # Chinese (girl)
    'chinese-boy': 'zh-CN-YunyangNeural',  # Chinese (narrator/male)
}

class TTSHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/voices':
            self.send_json({
                'voices': [
                    {'id': k, 'name': k.replace('-', ' ').title(), 'voice': v}
                    for k, v in VOICES.items()
                ]
            })
        elif self.path == '/health':
            self.send_json({'status': 'ok'})
        else:
            self.send_error(404, 'Not Found')
    
    def do_POST(self):
        if self.path == '/tts':
            self.handle_tts()
        elif self.path == '/tts/json':
            self.handle_tts_json()
        else:
            self.send_error(404, 'Not Found')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
    
    def handle_tts(self):
        """Return audio file directly"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            text = data.get('text')
            voice_name = data.get('voice', 'singapore')
            
            if not text:
                self.send_json({'error': 'Missing text'}, 400)
                return
            
            voice = VOICES.get(voice_name, VOICES['singapore'])
            output_path = asyncio.run(generate_speech(text, voice))
            
            # Send audio file
            with open(output_path, 'rb') as f:
                audio_data = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', len(audio_data))
            self.end_headers()
            self.wfile.write(audio_data)
            
            os.remove(output_path)
            
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def handle_tts_json(self):
        """Return base64 encoded audio"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            text = data.get('text')
            voice_name = data.get('voice', 'singapore')
            
            if not text:
                self.send_json({'error': 'Missing text'}, 400)
                return
            
            voice = VOICES.get(voice_name, VOICES['singapore'])
            output_path = asyncio.run(generate_speech(text, voice))
            
            # Read as base64
            with open(output_path, 'rb') as f:
                audio_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            os.remove(output_path)
            
            self.send_json({
                'audio': audio_base64,
                'voice': voice,
                'format': 'mp3'
            })
            
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def send_json(self, data, status=200):
        response = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response)
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

async def generate_speech(text, voice):
    """Generate speech using Edge TTS"""
    import edge_tts
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f"tts_output_{uuid.uuid4()}.mp3")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path

if __name__ == '__main__':
    print("🔊 Edge TTS Server starting on port 5001...")
    print("Available voices:")
    for name, voice in VOICES.items():
        print(f"  - {name}: {voice}")
    print()
    
    with socketserver.TCPServer(("", PORT), TTSHandler) as httpd:
        httpd.serve_forever()
