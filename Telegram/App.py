# app.py
from flask import Flask, request
from telegram_bot import send_telegram_message, send_typing_status
from paxsenix_api import call_paxsenix_api
from google_sheets import save_user_history_to_google, get_user_history_from_google
from config import TELEGRAM_API, APP_SCRIPT_URL, PAXSENIX_API_URL

app = Flask(__name__)

@app.route("/", methods=["POST"])
def index():
    data = request.json
    user_id = data["message"]["from"]["id"]
    user_message = data["message"]["text"]

    # Google Sheets se user history le rahe hain
    user_history = get_user_history_from_google(user_id, APP_SCRIPT_URL)

    # Agar koi pending message hai toh user ko batayein
    if user_history and user_history[-1].get("pending", False):
        send_telegram_message(user_id, "Please wait, I am still replying to your previous message.", TELEGRAM_API)
        return {"status": "ok"}

    # New message ko history mein add karein
    user_history.append({"role": "user", "content": user_message, "pending": True})

    # Send typing status before processing the request
    send_typing_status(user_id, TELEGRAM_API)

    # Paxsenix API ko call karein response ke liye
    try:
        ai_response = call_paxsenix_api(user_history, PAXSENIX_API_URL)
        user_history.append({"role": "assistant", "content": ai_response["message"], "pending": False})

        # Google Sheets ko update karein
        save_user_history_to_google(user_id, user_history, False, "", APP_SCRIPT_URL)

        # User ko AI response bhejein
        send_telegram_message(user_id, ai_response["message"], TELEGRAM_API)
        return {"status": "ok"}

    except Exception as e:
        send_telegram_message(user_id, f"An error occurred: {str(e)}", TELEGRAM_API)
        save_user_history_to_google(user_id, user_history, False, str(e), APP_SCRIPT_URL)
        return {"status": "error"}

@app.route("/", methods=["GET"])
def get_request():
    return "GET method is not allowed.", 405

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
