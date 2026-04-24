#!/usr/bin/env python3
"""
Voice chat server that serves HTML and proxies API requests
- /api/* → OpenClaw Gateway (port 18789)
- /tts/* → TTS server (port 5001)
- /stt/*, /transcribe → STT server (port 5000)
"""

import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os

PORT = 8080
GATEWAY_URL = "http://localhost:18789"
TTS_URL = "http://localhost:5001"
STT_URL = "http://localhost:5004"

class VoiceChatHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Route STT requests
        if self.path.startswith('/transcribe') or self.path.startswith('/stt'):
            self._proxy_to_stt('GET')
        # Route TTS requests
        elif self.path.startswith('/tts') or self.path.startswith('/voices'):
            self._proxy_to_tts('GET')
        # Serve static files
        elif self.path == '/' or self.path == '/index.html':
            self.path = '/index-modern.html'
            return super().do_GET()
        else:
            return super().do_GET()
    
    def do_POST(self):
        # Route STT requests
        if self.path.startswith('/transcribe') or self.path.startswith('/stt'):
            self._proxy_to_stt('POST')
        # Route TTS requests
        elif self.path.startswith('/tts'):
            self._proxy_to_tts('POST')
        # Proxy other POST requests to Gateway
        else:
            self._proxy_to_gateway('POST')
    
    def do_OPTIONS(self):
        # CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def _proxy_to_stt(self, method):
        self._proxy_request(STT_URL, method)
    
    def _proxy_to_tts(self, method):
        self._proxy_request(TTS_URL, method)
    
    def _proxy_to_gateway(self, method):
        self._proxy_request(GATEWAY_URL, method)
    
    def _proxy_request(self, base_url, method):
        """Generic proxy method"""
        try:
            body = None
            if method == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                print(f"Proxying {method} to {base_url}{self.path}, body size: {content_length}")
                if content_length > 0:
                    body = self.rfile.read(content_length)
            
            url = f"{base_url}{self.path}"
            req = urllib.request.Request(url, data=body, method=method)
            
            # Copy relevant headers
            for header in ['Content-Type', 'Authorization']:
                if header in self.headers:
                    req.add_header(header, self.headers[header])
            
            with urllib.request.urlopen(req, timeout=60) as response:
                response_data = response.read()
                self.send_response(response.status)
                self.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response_data)
                
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

if __name__ == '__main__':
    # Serve files from Roboboy2 directory
    WEB_ROOT = os.path.dirname(os.path.abspath(__file__))
    os.chdir(WEB_ROOT)
    print(f"Serving files from: {WEB_ROOT}")
    
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), VoiceChatHandler) as httpd:
        print(f"🎤 Voice Chat Server running on port {PORT}")
        print(f"Open: http://localhost:{PORT}/")
        print(f"STT:  http://localhost:{PORT}/transcribe → port 5000")
        print(f"TTS:  http://localhost:{PORT}/tts → port 5001")
        print(f"API:  http://localhost:{PORT}/api/* → port 18789")
        httpd.serve_forever()
