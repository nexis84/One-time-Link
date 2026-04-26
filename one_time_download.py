#!/usr/bin/env python3
"""
One-Time Download Link Generator
Creates disposable download links that expire after first use.
Uses in-memory storage (tokens lost on restart - acceptable for one-time use).
"""

from flask import Flask, redirect, jsonify, request
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

def generate_token():
    """Generate a new unique token."""
    cleanup_expired_tokens()
    
    # Generate secure random token
    token = secrets.token_urlsafe(16)
    
    # Set expiration (24 hours from now)
    expires_at = datetime.now() + timedelta(hours=24)
    
    tokens[token] = {
        'target_url': TARGET_URL,
        'created_at': datetime.now(),
        'expires_at': expires_at,
        'used': False
    }
    
    return token

@app.route('/generate')
def generate_link():
    """Generate a new one-time download link."""
    token = generate_token()
    # Auto-detect base URL from request
    base_url = request.host_url.rstrip('/')
    download_link = f"{base_url}/d/{token}"
    return jsonify({
        'download_link': download_link,
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
