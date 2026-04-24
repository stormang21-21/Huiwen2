#!/usr/bin/env python3
"""
Simple transcription server using local Whisper
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import tempfile
import os
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Transcribe audio using local Whisper"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        # Save uploaded file temporarily
        temp_dir = tempfile.gettempdir()
        input_path = os.path.join(temp_dir, f"whisper_input_{uuid.uuid4()}.webm")
        output_path = os.path.join(temp_dir, f"whisper_output_{uuid.uuid4()}")
        
        file.save(input_path)
        
        # Convert webm to wav (whisper needs wav)
        wav_path = input_path.replace('.webm', '.wav')
        convert_cmd = ['ffmpeg', '-i', input_path, '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', wav_path, '-y']
        subprocess.run(convert_cmd, check=True, capture_output=True)
        
        # Run Whisper
        whisper_cmd = ['whisper', wav_path, '--model', 'base', '--language', 'en', '--output_format', 'txt', '--output_dir', temp_dir]
        result = subprocess.run(whisper_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({'error': 'Whisper failed', 'details': result.stderr}), 500
        
        # Read transcription
        txt_file = wav_path.replace('.wav', '.txt')
        with open(txt_file, 'r') as f:
            transcript = f.read().strip()
        
        # Cleanup
        for f in [input_path, wav_path, txt_file]:
            if os.path.exists(f):
                os.remove(f)
        
        return jsonify({'text': transcript})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("🎤 Whisper Transcription Server starting on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
