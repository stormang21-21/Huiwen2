#!/usr/bin/env python3
"""
STT (Speech-to-Text) server using OpenAI Whisper API
Supports multiple audio formats (webm, wav, mp3, m4a)
With automatic language detection
"""

import http.server
import socketserver
import json
import tempfile
import os
import uuid
import base64
import email
from email.parser import BytesParser
from langdetect import detect, DetectorFactory

# Set seed for consistent language detection
DetectorFactory.seed = 0

PORT = 5004

# Configuration
USE_LOCAL_WHISPER = False  # Set to True to use local Whisper instead of API
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

class STTHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/health':
            self.send_json({'status': 'ok', 'mode': 'local' if USE_LOCAL_WHISPER else 'api'})
        elif self.path == '/languages':
            self.send_json({
                'languages': [
                    {'code': k, 'name': v} for k, v in LANGUAGES.items()
                ]
            })
        else:
            self.send_error(404, 'Not found')
    
    def do_POST(self):
        if self.path == '/transcribe':
            self.handle_transcribe()
        elif self.path == '/transcribe/json':
            self.handle_transcribe_json()
        else:
            self.send_error(404, 'Not found')
    
    def handle_transcribe(self):
        """Transcribe audio file (returns JSON with text)"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            content_type = self.headers.get('Content-Type', '')
            
            print(f"Received audio: {content_length} bytes, type: {content_type}")
            
            # Handle multipart form data (file upload)
            if 'multipart/form-data' in content_type:
                audio_data, file_ext = self.parse_multipart(content_length, content_type)
            elif 'application/json' in content_type:
                # Handle base64 encoded audio in JSON
                body = self.rfile.read(content_length)
                data = json.loads(body)
                audio_data = base64.b64decode(data.get('audio', ''))
                file_ext = 'webm'  # Default
            else:
                # Raw audio data
                audio_data = self.rfile.read(content_length)
                file_ext = 'webm'  # Default
            
            if not audio_data:
                self.send_json({'error': 'No audio data received'}, 400)
                return
            
            print(f"Parsed audio: {len(audio_data)} bytes, ext: {file_ext}")
            
            # Save audio to temp file for debugging
            temp_dir = tempfile.gettempdir()
            debug_path = os.path.join(temp_dir, f"stt_debug_{uuid.uuid4()}.{file_ext}")
            with open(debug_path, 'wb') as f:
                f.write(audio_data)
            print(f"Saved debug audio: {debug_path} ({os.path.getsize(debug_path)} bytes)")
            
            # Transcribe using OpenAI API
            result = self.transcribe_api(audio_data, file_ext)
            
            # Cleanup debug file
            if os.path.exists(debug_path):
                os.remove(debug_path)
            
            self.send_json({
                'text': result.get('text', ''),
                'language': result.get('language', 'auto'),
                'duration': None
            })
            
        except Exception as e:
            print(f"Error in handle_transcribe: {str(e)}")
            import traceback
            traceback.print_exc()
            self.send_json({'error': str(e)}, 500)
    
    def handle_transcribe_json(self):
        """Transcribe base64 audio (returns JSON)"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            audio_b64 = data.get('audio', '')
            
            if not audio_b64:
                self.send_json({'error': 'Missing audio data'}, 400)
                return
            
            # Remove data URL prefix if present
            if ',' in audio_b64:
                audio_b64 = audio_b64.split(',')[1]
            
            audio_data = base64.b64decode(audio_b64)
            
            # Transcribe
            transcript = self.transcribe_api(audio_data)
            
            self.send_json({
                'text': transcript,
                'language': 'auto',
                'duration': None
            })
            
        except Exception as e:
            print(f"Error in handle_transcribe_json: {str(e)}")
            self.send_json({'error': str(e)}, 500)
    
    def parse_multipart(self, content_length, content_type):
        """Parse multipart form data and extract file content"""
        body = self.rfile.read(content_length)
        
        print(f"Raw body length: {len(body)}")
        print(f"Content-Type: {content_type}")
        
        # Extract boundary from content-type
        boundary = content_type.split('boundary=')[1].split(';')[0].strip('"')
        boundary_bytes = ('--' + boundary).encode()
        
        parts = body.split(boundary_bytes)
        
        for part in parts:
            if b'filename=' in part:
                # Find the end of headers
                header_end = part.find(b'\r\n\r\n')
                if header_end > 0:
                    # Get file data (everything after headers)
                    file_data = part[header_end + 4:]
                    
                    # Remove trailing boundary markers
                    if file_data.endswith(b'\r\n--'):
                        file_data = file_data[:-4]
                    elif file_data.endswith(b'--'):
                        file_data = file_data[:-2]
                    
                    # Extract filename to determine extension
                    filename_match = part.find(b'filename="')
                    if filename_match > 0:
                        filename_start = filename_match + len(b'filename="')
                        filename_end = part.find(b'"', filename_start)
                        if filename_end > filename_start:
                            filename = part[filename_start:filename_end].decode('utf-8')
                            file_ext = filename.split('.')[-1] if '.' in filename else 'webm'
                        else:
                            file_ext = 'webm'
                    else:
                        file_ext = 'webm'
                    
                    # Detect format from content-type if filename doesn't have extension
                    if file_ext == 'webm' and b'Content-Type:' in part:
                        content_type_part = part[header_end:header_end+200].decode('utf-8', errors='ignore')
                        if 'ogg' in content_type_part.lower():
                            file_ext = 'ogg'
                        elif 'opus' in content_type_part.lower():
                            file_ext = 'ogg'  # Opus is usually in OGG container
                    
                    print(f"Extracted file data: {len(file_data)} bytes, ext: {file_ext}")
                    return file_data, file_ext
        
        return None, 'webm'
    
    def transcribe_api(self, audio_data, file_ext='webm'):
        """Transcribe using OpenAI Whisper API"""
        import urllib.request
        
        if not OPENAI_API_KEY:
            raise Exception("OPENAI_API_KEY not set")
        
        print(f"Processing audio: {len(audio_data)} bytes, ext: {file_ext}")
        
        # Create multipart request - send original format directly to OpenAI
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        
        # Map extension to content type
        content_types = {
            'webm': 'audio/webm',
            'ogg': 'audio/ogg',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'mp4': 'audio/mp4',
            'm4a': 'audio/mp4',
            'flac': 'audio/flac',
        }
        content_type = content_types.get(file_ext, 'audio/webm')
        
        # Build body
        body_parts = []
        body_parts.append(f'--{boundary}\r\n'.encode())
        body_parts.append(f'Content-Disposition: form-data; name="file"; filename="audio.{file_ext}"\r\n'.encode())
        body_parts.append(f'Content-Type: {content_type}\r\n\r\n'.encode())
        body_parts.append(audio_data)
        body_parts.append(f'\r\n--{boundary}\r\n'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="model"\r\n\r\n')
        body_parts.append(b'whisper-1\r\n')
        body_parts.append(f'--{boundary}--\r\n'.encode())
        
        body = b''.join(body_parts)
        
        print(f"Sending to OpenAI: {len(audio_data)} bytes, ext: {file_ext}, type: {content_type}")
        
        req = urllib.request.Request(
            'https://api.openai.com/v1/audio/transcriptions',
            data=body,
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': f'multipart/form-data; boundary={boundary}'
            },
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read())
                text = result.get('text', '').strip()
                
                # Detect language from transcribed text
                detected_lang = 'auto'
                if text:
                    try:
                        detected_lang = detect(text)
                        print(f"Detected language: {detected_lang}")
                    except Exception as e:
                        print(f"Language detection failed: {str(e)}")
                        detected_lang = 'auto'
                
                print(f"Transcription result: '{text}'")
                
                return {
                    'text': text,
                    'language': detected_lang
                }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print(f"OpenAI API error: {e.code} - {error_body}")
            raise Exception(f"OpenAI API error: {error_body}")
    
    def send_json(self, data, status=200):
        response = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response)
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

# Supported languages
LANGUAGES = {
    'auto': 'Auto-detect',
    'en': 'English',
    'ta': 'Tamil',
    'ms': 'Malay',
    'zh': 'Chinese (Mandarin)',
    'zh-HK': 'Chinese (Cantonese)',
}

# Default response language for AI
DEFAULT_AI_LANGUAGE = 'English'

if __name__ == '__main__':
    mode = 'LOCAL' if USE_LOCAL_WHISPER else 'API'
    print(f"🎤 STT Server starting on port {PORT} ({mode} mode)")
    print(f"Endpoint: http://localhost:{PORT}/transcribe")
    if not USE_LOCAL_WHISPER and not OPENAI_API_KEY:
        print("⚠️  WARNING: OPENAI_API_KEY not set! Set it or enable USE_LOCAL_WHISPER")
    print()
    
    with socketserver.TCPServer(("", PORT), STTHandler) as httpd:
        httpd.serve_forever()
