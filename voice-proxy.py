#!/usr/bin/env python3
"""
Proxy server that serves static files AND proxies API requests to OpenClaw Gateway
"""

import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os

PORT = 8080
GATEWAY_URL = "http://localhost:18789"
WEB_ROOT = "/root/.openclaw/workspace"

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_ROOT, **kwargs)
    
    def do_GET(self):
        # Proxy API requests to OpenClaw Gateway
        if self.path.startswith('/v1/'):
            self._proxy_to_gateway('GET')
        else:
            # Serve static files
            super().do_GET()
    
    def do_POST(self):
        # Proxy API requests to OpenClaw Gateway
        if self.path.startswith('/v1/'):
            self._proxy_to_gateway('POST')
        else:
            self.send_error(501, 'POST only supported for /v1/* endpoints')
    
    def do_OPTIONS(self):
        # CORS preflight
        if self.path.startswith('/v1/'):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
        else:
            super().do_OPTIONS()
    
    def _proxy_to_gateway(self, method):
        try:
            # Read request body for POST
            body = None
            if method == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    body = self.rfile.read(content_length)
            
            # Build gateway URL
            gateway_url = f"{GATEWAY_URL}{self.path}"
            
            # Create request
            req = urllib.request.Request(gateway_url, data=body, method=method)
            
            # Copy headers
            for header in ['Authorization', 'Content-Type']:
                if header in self.headers:
                    req.add_header(header, self.headers[header])
            
            # Make request to gateway
            with urllib.request.urlopen(req, timeout=60) as response:
                response_body = response.read()
                
                # Send response back to client
                self.send_response(response.status)
                self.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response_body)
                
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
    print(f"🎤 Voice Chat Proxy Server")
    print(f"Serving files from: {WEB_ROOT}")
    print(f"Proxying API to: {GATEWAY_URL}")
    print(f"URL: http://localhost:{PORT}/")
    print(f"Voice Chat: http://localhost:{PORT}/voice-chat-v3.html")
    print()
    
    with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
        httpd.serve_forever()
