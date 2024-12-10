from flask import Flask, request
import requests
import json

app = Flask(__name__)

# Telegram Bot Token
TELEGRAM_TOKEN = "8169493568:AAHiZ6t3my3vyKSfw00GotWD6vflI2RFqb0"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# PaxSenix API URLs
TEXT_API_URL = "https://api.paxsenix.biz.id/ai/gpt4o"
IMAGE_API_URL = "https://api.paxsenix.biz.id/ai/geminivision"

# Google Apps Script API URL to save chat history
SAVE_HISTORY_API_URL = "https://script.google.com/macros/s/AKfycbz74t0Aw9DoINW2R2u2AXwB1m-5YqRzPBWE7VE9zAdCNn8nFtuD_ksj_XlCrJNKKNhybQ/exec"


def send_typing_action(chat_id):
    """
    Sends a single typing action to Telegram.
    """
    requests.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})


def get_user_history(user_id):
    """
    Fetches the user message history from Google Sheets.
    """
    response = requests.get(f"{SAVE_HISTORY_API_URL}?userId={user_id}")
    return response.json()


def save_user_history(user_id, full_name, message_history, pending_status="false"):
    """
    Saves the updated user message history to Google Sheets.
    """
    data = {
        "User ID": user_id,
        "Full Name": full_name,
        "Message History": json.dumps(message_history),
        "Pending Status": pending_status
    }
    response = requests.post(SAVE_HISTORY_API_URL, json=data)
    return response.json()


def process_text_message(chat_id, user_id, user_text):
    """
    Processes a text message from the user.
    """
    # Send typing action
    send_typing_action(chat_id)

    user_history_response = get_user_history(user_id)
    user_history = []

    if user_history_response.get("success"):
        # Append the previous history
        user_history = json.loads(user_history_response["user"]["Message History"])
    else:
        # If no history exists, start a new conversation
        user_history = []

    # Append the user's message to the history
    user_history.append({"role": "user", "content": user_text})

    # Call PaxSenix Text API
    response = requests.post(TEXT_API_URL, headers={
        "accept": "application/json",
        "Content-Type": "application/json"
    }, json={"messages": user_history})

    response_message = response.json().get("message", "Unable to process your request.")
    user_history.append({"role": "assistant", "content": response_message})

    # Send the response back to Telegram
    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_message})

    # Save updated history
    save_user_history(user_id, "Unknown", user_history)


def process_image_message(chat_id, user_id, image_caption, image_url):
    """
    Processes an image message from the user.
    """
    # Send typing action
    send_typing_action(chat_id)

    # Default caption if none is provided
    caption = image_caption if image_caption else "Describe This Image"

    # Call PaxSenix Image API
    response = requests.get(f"{IMAGE_API_URL}?text={caption}&url={image_url}", headers={
        "accept": "application/json"
    })

    response_message = response.json().get("message", "Unable to process the image.")

    # Send the response back to Telegram
    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_message})

    # Append message to history with 📷 icon
    user_history_response = get_user_history(user_id)
    user_history = []

    if user_history_response.get("success"):
        user_history = json.loads(user_history_response["user"]["Message History"])

    user_history.append({"role": "user", "content": "📷"})
    user_history.append({"role": "assistant", "content": response_message})

    # Save updated history
    save_user_history(user_id, "Unknown", user_history)


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json

        if "message" in data:  # Check if it's a message
            chat_id = data["message"]["chat"]["id"]
            user_id = str(chat_id)  # Using chat_id as user_id for simplicity

            # Handle text message
            if "text" in data["message"]:
                user_text = data["message"]["text"]
                process_text_message(chat_id, user_id, user_text)

            # Handle photo message
            elif "photo" in data["message"]:
                photo_file_id = data["message"]["photo"][-1]["file_id"]  # Highest resolution
                file_response = requests.get(f"{TELEGRAM_API}/getFile?file_id={photo_file_id}")
                file_path = file_response.json()["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
                caption = data["message"].get("caption", None)
                process_image_message(chat_id, user_id, caption, file_url)

            # Handle unsupported media
            else:
                response_message = "Unable to process your request."
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_message})

        return {"status": "ok"}
    return "Telegram bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
