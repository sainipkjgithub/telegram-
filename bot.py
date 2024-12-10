import requests
import json
from flask import Flask, request

# Flask app initialization
app = Flask(__name__)

# Your Telegram Bot token and API
TELEGRAM_TOKEN = "8169493568:AAHgkbPTtukjYrrQDOk8zFrMN7jubQmuqV8"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Google Apps Script URL (replace this with your Web App URL)
APP_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyBUVP4SA8hO4zuI2PkORJaAGWILEpGY229mFYPU_NxgTraSvYnAxI8M4mC2vY2ZskjHg/exec"

# Paxsenix API URL
PAXSENIX_API_URL = "https://api.paxsenix.biz.id/ai/gpt4o"

# Function to send Telegram message
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

# Function to call the Paxsenix API
def call_paxsenix_api(conversation_history):
    payload = {
        "messages": conversation_history
    }
    response = requests.post(PAXSENIX_API_URL, json=payload)
    response_data = response.json()
    if "message" not in response_data:
        raise Exception("Failed to get a valid response from Paxsenix API")
    return response_data

# Function to save user history to Google Sheets
def save_user_history_to_google(user_id, message_history, pending_status, error):
    payload = {
        "user_id": user_id,
        "message_history": json.dumps(message_history),
        "pending_status": pending_status,
        "error": error
    }
    response = requests.post(APP_SCRIPT_URL, json=payload)
    return response.status_code

# Function to retrieve user history from Google Sheets
def get_user_history_from_google(user_id):
    response = requests.get(APP_SCRIPT_URL, params={"user_id": user_id})
    if response.status_code == 200:
        data = response.json()
        return data.get("message_history", [])
    return []

# Route to handle incoming Telegram webhook requests
@app.route("/", methods=["POST"])
def index():
    data = request.json
    user_id = data["message"]["from"]["id"]
    user_message = data["message"]["text"]

    # Get the user's message history from Google Sheets
    user_history = get_user_history_from_google(user_id)

    # Check if there's any pending message
    if user_history and user_history[-1].get("pending", False):
        send_telegram_message(user_id, "Please wait, I am still replying to your previous message.")
        return {"status": "ok"}

    # Add the new message to the history
    user_history.append({"role": "user", "content": user_message, "pending": True})

    # Call Paxsenix API to get a response
    try:
        ai_response = call_paxsenix_api(user_history)
        user_history.append({"role": "assistant", "content": ai_response["message"], "pending": False})

        # Save the updated history to Google Sheets
        save_user_history_to_google(user_id, user_history, False, "")

        # Send the AI response to the user
        send_telegram_message(user_id, ai_response["message"])
        return {"status": "ok"}

    except Exception as e:
        send_telegram_message(user_id, f"An error occurred: {str(e)}")
        save_user_history_to_google(user_id, user_history, False, str(e))
        return {"status": "error"}

# Route for GET request (not allowed)
@app.route("/", methods=["GET"])
def get_request():
    return "GET method is not allowed.", 405

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
