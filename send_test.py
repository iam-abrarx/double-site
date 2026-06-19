import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

print(f"Testing Telegram message delivery...")
print(f"Token: {TOKEN[:10]}...")
print(f"Chat ID: {CHAT_ID}")

url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
payload = {'chat_id': CHAT_ID, 'text': "Test message from OTP server Setup!"}

try:
    resp = requests.post(url, json=payload)
    print(f"Status Code: {resp.status_code}")
    print(f"Response Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
