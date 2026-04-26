#!/usr/bin/env python3
"""
One-Time Download Link Generator
Creates disposable download links that expire after first use.
Uses PostgreSQL for persistent storage (Render-compatible).
"""

from flask import Flask, redirect, jsonify
import secrets
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
TARGET_URL = os.getenv('TARGET_URL', 'https://github.com/nexis84/Rusty-Client/releases/download/2.0.45/RustyBot_Setup_v2.0.45.0.exe')

def get_db_connection():
    """Get database connection."""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    # No database available - raise error
    raise RuntimeError("DATABASE_URL not set. Please add a PostgreSQL database.")

def init_db():
    """Initialize database table."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS download_tokens (
            token VARCHAR(32) PRIMARY KEY,
            target_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def cleanup_expired_tokens():
    """Remove expired tokens from database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM download_tokens WHERE expires_at < NOW()")
    conn.commit()
    cur.close()
    conn.close()

def generate_token():
    """Generate a new unique token."""
    cleanup_expired_tokens()
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Generate secure random token
    token = secrets.token_urlsafe(16)
    
    # Set expiration (24 hours from now)
    expires_at = datetime.now() + timedelta(hours=24)
    
    cur.execute(
        "INSERT INTO download_tokens (token, target_url, expires_at) VALUES (%s, %s, %s)",
        (token, TARGET_URL, expires_at)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    return token

@app.route('/generate')
def generate_link():
    """Generate a new one-time download link."""
    token = generate_token()
    # Use environment variable or default to localhost for testing
    base_url = os.getenv('BASE_URL', 'http://localhost:5000')
    download_link = f"{base_url}/d/{token}"
    return jsonify({
        'download_link': download_link,
        'expires_in': '24 hours',
        'one_time_use': True
    })

@app.route('/d/<token>')
def download(token):
    """Handle the download redirect."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute(
        "SELECT * FROM download_tokens WHERE token = %s AND expires_at > NOW()",
        (token,)
    )
    token_data = cur.fetchone()
    
    if not token_data:
        cur.close()
        conn.close()
        return jsonify({'error': 'Invalid or expired link'}), 404
    
    if token_data['used']:
        cur.close()
        conn.close()
        return jsonify({'error': 'Link already used'}), 410
    
    # Mark as used
    cur.execute("UPDATE download_tokens SET used = TRUE WHERE token = %s", (token,))
    conn.commit()
    cur.close()
    conn.close()
    
    # Redirect to actual download
    return redirect(token_data['target_url'])

@app.route('/status/<token>')
def check_status(token):
    """Check if a token is still valid."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute(
        "SELECT used, expires_at FROM download_tokens WHERE token = %s AND expires_at > NOW()",
        (token,)
    )
    token_data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not token_data:
        return jsonify({'valid': False, 'reason': 'Not found or expired'})
    
    return jsonify({
        'valid': True,
        'used': token_data['used'],
        'expires_at': token_data['expires_at'].isoformat()
    })

@app.route('/health')
def health():
    """Health check endpoint for Render."""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Initialize database
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
        print("Running without database (tokens won't persist)")
    
    port = int(os.getenv('PORT', 5000))
    print("One-Time Download Link Server")
    print("=" * 40)
    print(f"Target URL: {TARGET_URL}")
    print(f"Visit http://localhost:{port}/generate to create a link")
    print("=" * 40)
    app.run(host='0.0.0.0', port=port)
