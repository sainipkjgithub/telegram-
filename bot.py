from flask import Flask, request
import requests
import json

app = Flask(__name__)

TELEGRAM_TOKEN = "8169493568:AAHgkbPTtukjYrrQDOk8zFrMN7jubQmuqV8"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
PAXSENIX_API_URL = "https://api.paxsenix.biz.id/ai/gpt4o"
USER_HISTORY_FILE = "user_history.json"  # This is a simple file for storing user history.

# Load user history from file
def load_user_history():
    try:
        with open(USER_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save user history to file
def save_user_history(user_history):
    with open(USER_HISTORY_FILE, 'w') as f:
        json.dump(user_history, f)

# Send Telegram message
def send_telegram_message(user_id, message):
    if len(message) > 4096:
        message = message[:4093] + "..."  # Truncate message if too long

    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    return response.json()

# Handle incoming POST requests from Telegram
@app.route("/", methods=["POST"])
def index():
    data = request.json
    user_id = data["message"]["from"]["id"]
    user_message = data["message"]["text"]

    user_history = load_user_history()

    # Check if user history exists
    if user_id not in user_history:
        user_history[user_id] = []

    # Handle /start command
    if user_message == "/start":
        send_telegram_message(user_id, "Welcome to the bot! 😊 How can I assist you today?")
        user_history[user_id] = []  # Reset user history
        save_user_history(user_history)
        return {"status": "ok"}

    # Check for pending status (You can implement a more sophisticated check here)
    if user_id in user_history and len(user_history[user_id]) > 0 and user_history[user_id][-1].get("pending", False):
        send_telegram_message(user_id, "Please wait, I am still replying to your previous message.")
        return {"status": "ok"}

    # Mark the user message as pending for now (optional)
    user_history[user_id].append({"role": "user", "content": user_message, "pending": True})

    # Call Paxsenix API to get a response
    try:
        ai_response = call_paxsenix_api(user_history[user_id])
        user_history[user_id].append({"role": "assistant", "content": ai_response["message"], "pending": False})
        save_user_history(user_history)  # Update history

        # Send AI response to the user
        send_telegram_message(user_id, ai_response["message"])
        return {"status": "ok"}

    except Exception as e:
        send_telegram_message(user_id, f"An error occurred: {str(e)}")
        return {"status": "error"}

# Call Paxsenix API
def call_paxsenix_api(conversation_history):
    payload = {
        "messages": conversation_history
    }
    response = requests.post(PAXSENIX_API_URL, json=payload)
    response_data = response.json()
    if "message" not in response_data:
        raise Exception("Failed to get a valid response from Paxsenix API")
    return response_data

# Handle GET requests (not allowed)
@app.route("/", methods=["GET"])
def get_request():
    return "GET method is not allowed.", 405

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
