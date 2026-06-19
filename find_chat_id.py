import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN or 'YOUR_' in TOKEN:
    print("Please set your TELEGRAM_BOT_TOKEN in .env first.")
    exit(1)

print("Checking Telegram for recent messages to your bot...")
url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

try:
    resp = requests.get(url).json()
    if not resp.get('ok'):
        print(f"Error from Telegram: {resp.get('description')}")
        exit(1)
    
    results = resp.get('result', [])
    if not results:
        print("\nNo messages found! Please open your bot in Telegram and send it a text message (like 'hello' or '/start'), then run this script again.")
        exit(0)
    
    # Get the latest message
    latest = results[-1]
    message = latest.get('message', {})
    chat = message.get('chat', {})
    chat_id = chat.get('id')
    username = chat.get('username', 'N/A')
    first_name = chat.get('first_name', 'N/A')
    
    print("\n🎉 Found active chat!")
    print(f"User: {first_name} (@{username})")
    print(f"Your Personal Chat ID: {chat_id}")
    print("\nUpdating your .env file with this Chat ID...")
    
    # Read and update .env
    with open('.env', 'r') as f:
        lines = f.readlines()
        
    new_lines = []
    for line in lines:
        if line.startswith('TELEGRAM_CHAT_ID='):
            new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
        else:
            new_lines.append(line)
            
    with open('.env', 'w') as f:
        f.writelines(new_lines)
        
    print("Successfully updated .env! Please restart your Flask server now.")
    
except Exception as e:
    print(f"Failed to connect to Telegram: {e}")
