#!/usr/bin/env python3
"""
One-Time Download Link Generator
Creates disposable download links that expire after first use.
Uses in-memory storage (tokens lost on restart - acceptable for one-time use).
"""

from flask import Flask, redirect, jsonify, request, render_template_string
import secrets
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuration
TARGET_URL = os.getenv('TARGET_URL', 'https://github.com/nexis84/Rusty-Client/releases/download/2.0.45/RustyBot_Setup_v2.0.45.0.exe')

# In-memory storage (tokens lost on restart)
tokens = {}

def cleanup_expired_tokens():
    """Remove expired tokens from memory."""
    now = datetime.now()
    expired_tokens = [token for token, data in tokens.items() if data['expires_at'] < now]
    for token in expired_tokens:
        del tokens[token]

def generate_token(target_url=None):
    """Generate a new unique token."""
    cleanup_expired_tokens()
    
    # Generate secure random token
    token = secrets.token_urlsafe(16)
    
    # Set expiration (24 hours from now)
    expires_at = datetime.now() + timedelta(hours=24)
    
    # Use provided URL or fall back to default TARGET_URL
    url = target_url if target_url else TARGET_URL
    
    tokens[token] = {
        'target_url': url,
        'created_at': datetime.now(),
        'expires_at': expires_at,
        'used': False
    }
    
    return token

@app.route('/')
def index():
    """Web page to generate one-time download links."""
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>One-Time Download Link Generator</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-top: 0;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #555;
        }
        input[type="url"] {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
        }
        button:hover {
            background: #0056b3;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            background: #e8f4ff;
            border-radius: 4px;
            display: none;
        }
        .result a {
            color: #007bff;
            word-break: break-all;
        }
        .note {
            margin-top: 15px;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>One-Time Download Link Generator</h1>
        <p>Enter a URL to create a disposable download link that expires after first use.</p>
        
        <div class="form-group">
            <label for="url">Target URL:</label>
            <input type="url" id="url" placeholder="https://example.com/file.zip" required>
        </div>
        
        <button onclick="generateLink()">Generate One-Time Link</button>
        
        <div class="result" id="result">
            <strong>Your one-time download link:</strong><br>
            <a id="downloadLink" href="#" target="_blank"></a>
            <div class="note">
                <strong>Target:</strong> <span id="targetUrl"></span><br>
                <strong>Expires in:</strong> 24 hours<br>
                <strong>One-time use:</strong> Yes
            </div>
        </div>
    </div>

    <script>
        function generateLink() {
            const url = document.getElementById('url').value;
            if (!url) {
                alert('Please enter a URL');
                return;
            }
            
            fetch('/generate?url=' + encodeURIComponent(url))
                .then(response => response.json())
                .then(data => {
                    document.getElementById('downloadLink').href = data.download_link;
                    document.getElementById('downloadLink').textContent = data.download_link;
                    document.getElementById('targetUrl').textContent = data.target_url;
                    document.getElementById('result').style.display = 'block';
                })
                .catch(error => {
                    alert('Error generating link: ' + error);
                });
        }
    </script>
</body>
</html>
    ''')

@app.route('/generate')
def generate_link():
    """Generate a new one-time download link."""
    # Get URL from query parameter, fall back to default TARGET_URL
    custom_url = request.args.get('url')
    token = generate_token(custom_url)
    # Auto-detect base URL from request
    base_url = request.host_url.rstrip('/')
    download_link = f"{base_url}/d/{token}"
    return jsonify({
        'download_link': download_link,
        'target_url': custom_url if custom_url else TARGET_URL,
        'expires_in': '24 hours',
        'one_time_use': True
    })

@app.route('/d/<token>')
def download(token):
    """Handle the download redirect."""
    cleanup_expired_tokens()
    
    if token not in tokens:
        return jsonify({'error': 'Invalid or expired link'}), 404
    
    token_data = tokens[token]
    
    if token_data['used']:
        return jsonify({'error': 'Link already used'}), 410
    
    # Mark as used
    tokens[token]['used'] = True
    
    # Redirect to actual download
    return redirect(token_data['target_url'])

@app.route('/status/<token>')
def check_status(token):
    """Check if a token is still valid."""
    cleanup_expired_tokens()
    
    if token not in tokens:
        return jsonify({'valid': False, 'reason': 'Not found or expired'})
    
    return jsonify({
        'valid': True,
        'used': tokens[token]['used'],
        'expires_at': tokens[token]['expires_at'].isoformat()
    })

@app.route('/health')
def health():
    """Health check endpoint for Render."""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("One-Time Download Link Server")
    print("=" * 40)
    print(f"Target URL: {TARGET_URL}")
    print(f"Visit http://localhost:{port}/generate to create a link")
    print("=" * 40)
    app.run(host='0.0.0.0', port=port)
