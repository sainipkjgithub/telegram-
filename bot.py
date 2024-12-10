from flask import Flask, request
import telebot
import requests
import json

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = '8169493568:AAHgkbPTtukjYrrQDOk8zFrMN7jubQmuqV8'
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Google App Script URL
APP_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyBUVP4SA8hO4zuI2PkORJaAGWILEpGY229mFYPU_NxgTraSvYnAxI8M4mC2vY2ZskjHg/exec"

# PaxSenix API Details
PAXSENIX_API_URL = "https://api.paxsenix.biz.id/ai/gpt4o"
PAXSENIX_HEADERS = {
    'accept': 'application/json',
    'Content-Type': 'application/json'
}

app = Flask(__name__)

# Telegram Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data(as_text=True))
    bot.process_new_updates([update])
    return "OK", 200

# Fetch history from Google Sheets
def fetch_user_history(user_id):
    params = {
        'action': 'getRow',
        'col': 2,  # Assuming User ID is in column 2
        'value': user_id
    }
    response = requests.get(APP_SCRIPT_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return json.loads(data.get('Massage History', '[]'))  # Default to empty list if no history
    return []

# Save updated history to Google Sheets
def save_user_history(user_id, user_name, history):
    payload = {
        'action': 'setValue',
        'row': 1,  # Replace with logic to find user's row if needed
        'col': 4,  # Assuming history is stored in column 4
        'value': json.dumps(history)  # Convert list to string
    }
    response = requests.post(APP_SCRIPT_URL, data=payload)
    return response.status_code == 200

# Process messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_name = message.chat.first_name + (" " + message.chat.last_name if message.chat.last_name else "")
    user_message = message.text

    # Fetch existing history from Google Sheets
    history = fetch_user_history(user_id)

    # Append the new user message
    history.append({"role": "user", "content": user_message})

    # Prepare API request payload
    payload = {"messages": history}
    response = requests.post(PAXSENIX_API_URL, headers=PAXSENIX_HEADERS, json=payload)

    if response.status_code == 200:
        api_response = response.json()
        bot_reply = api_response.get("message", "Kuch galat ho gaya hai!")

        # Append the assistant's reply to history
        history.append({"role": "assistant", "content": bot_reply})

        # Save updated history to Google Sheets
        save_status = save_user_history(user_id, user_name, history)

        # Send the reply back to the user
        bot.send_message(user_id, bot_reply)
    else:
        bot.send_message(user_id, "API se response nahi mila, kripya baad mein koshish karein.")

if __name__ == '__main__':
    # Set webhook for Telegram
    bot.remove_webhook()
    bot.set_webhook(url='https://YOUR_RENDER_URL/webhook')
    app.run(host='0.0.0.0', port=5000)
