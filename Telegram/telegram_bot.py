# telegram_bot.py
import requests

def send_telegram_message(user_id, message, telegram_api_url):
    if len(message) > 4096:
        message = message[:4093] + "..."  # Truncate message if too long
    
    url = f"{telegram_api_url}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    return response.json()
