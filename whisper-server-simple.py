#!/usr/bin/env python3
"""
Simple HTTP server for local Whisper transcription
"""

import http.server
import socketserver
import json
import subprocess
import tempfile
import os
import uuid
import cgi

PORT = 5000

class TranscribeHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        if self.path == '/transcribe':
            try:
                # Parse multipart form data
                content_type = self.headers.get('Content-Type', '')
                if 'multipart/form-data' not in content_type:
                    self.send_error(400, 'Expected multipart/form-data')
                    return
                
                # Save uploaded file
                temp_dir = tempfile.gettempdir()
                input_path = os.path.join(temp_dir, f"input_{uuid.uuid4()}.webm")
                
                # Read the request body
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                
                # Simple parsing for multipart (extract file content)
                boundary = content_type.split('boundary=')[1].split(';')[0].strip()
                parts = body.split(b'--' + boundary.encode())
                
                file_data = None
                for part in parts:
                    if b'filename=' in part and b'Content-Type:' in part:
                        # Extract file content
                        header_end = part.find(b'\r\n\r\n')
                        if header_end > 0:
                            file_data = part[header_end + 4:].rstrip(b'\r\n')
                            break
                
                if not file_data:
                    self.send_error(400, 'No file found')
                    return
                
                # Save file
                with open(input_path, 'wb') as f:
                    f.write(file_data)
                
                # Convert to wav
                wav_path = input_path.replace('.webm', '.wav')
                convert_cmd = ['ffmpeg', '-i', input_path, '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', wav_path, '-y']
                subprocess.run(convert_cmd, check=True, capture_output=True)
                
                # Run Whisper
                whisper_cmd = ['whisper', wav_path, '--model', 'base', '--language', 'en', '--output_format', 'txt', '--output_dir', temp_dir]
                result = subprocess.run(whisper_cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.send_error(500, f'Whisper failed: {result.stderr}')
                    return
                
                # Read transcription
                txt_file = wav_path.replace('.wav', '.txt')
                with open(txt_file, 'r') as f:
                    transcript = f.read().strip()
                
                # Cleanup
                for f in [input_path, wav_path, txt_file]:
                    if os.path.exists(f):
                        os.remove(f)
                
                # Send response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'text': transcript}).encode())
                
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, 'Not found')
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        else:
            self.send_error(404, 'Not found')
    
    def log_message(self, format, *args):
        # Suppress logs
        pass

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), TranscribeHandler) as httpd:
        print(f"🎤 Whisper Transcription Server running on port {PORT}")
        print(f"Endpoint: http://localhost:{PORT}/transcribe")
        httpd.serve_forever()
