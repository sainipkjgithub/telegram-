from flask import Flask, request
import requests
import threading

app = Flask(__name__)

# Telegram Bot Token
TELEGRAM_TOKEN = "8169493568:AAHiZ6t3my3vyKSfw00GotWD6vflI2RFqb0"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Google Apps Script API URL
SCRIPT_API_URL = "https://script.google.com/macros/s/AKfycbz74t0Aw9DoINW2R2u2AXwB1m-5YqRzPBWE7VE9zAdCNn8nFtuD_ksj_XlCrJNKKNhybQ/exec"


def send_typing_action(chat_id):
    """
    Sends typing action to Telegram to show typing status.
    """
    requests.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})


def get_user_history(user_id):
    """
    Get user's history from Google Apps Script.
    """
    response = requests.get(f"{SCRIPT_API_URL}?userId={user_id}")
    return response.json()


def save_user_history(user_id, full_name, message_history):
    """
    Save user's updated history to Google Apps Script.
    """
    data = {
        "User ID": user_id,
        "Full Name": full_name,
        "Message History": message_history,
        "Pending Status": "false",
    }
    response = requests.post(SCRIPT_API_URL, json=data, headers={"Content-Type": "application/json"})
    return response.json()


def process_message(chat_id, user_id, user_text=None, message_type="text", extra=None):
    """
    Process user text or image message and call respective APIs.
    """
    threading.Thread(target=send_typing_action, args=(chat_id,)).start()

    # Get user history
    user_history_response = get_user_history(user_id)
    if not user_history_response.get("success"):
        message_history = []
    else:
        message_history = user_history_response["user"]["Message History"]

    # Add new user message to history
    if message_type == "text":
        message_history.append({"role": "user", "content": user_text})
        # Call PaxSenix text API
        response = requests.post(
            "https://api.paxsenix.biz.id/ai/gpt4o",
            json={"messages": message_history},
            headers={"accept": "application/json", "Content-Type": "application/json"},
        )
        assistant_message = response.json().get("message", "I couldn't process your request.")
        message_history.append({"role": "assistant", "content": assistant_message})
    elif message_type == "image":
        caption = extra.get("caption", "Describe This Image")
        image_url = extra["image_url"]
        # Call PaxSenix image API
        response = requests.get(
            f"https://api.paxsenix.biz.id/ai/geminivision?text={caption}&url={image_url}",
            headers={"accept": "application/json"},
        )
        assistant_message = response.json().get("message", "I couldn't process the image.")
        message_history.append({"role": "user", "content": "📷"})
        message_history.append({"role": "assistant", "content": assistant_message})

    # Send response to user
    send_message_to_user(chat_id, assistant_message)

    # Save updated history
    save_user_history(user_id, "Unknown", message_history)


def send_message_to_user(chat_id, message):
    """
    Send message to user via Telegram.
    """
    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": message})


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            user_id = str(chat_id)  # Using chat_id as user_id

            # Handle /start command
            if "text" in data["message"] and data["message"]["text"] == "/start":
                user_history_response = get_user_history(user_id)

                if user_history_response.get("success"):
                    # User exists, clear history
                    save_user_history(user_id, "Unknown", [])
                    response_message = "Your chat history has been cleared!"
                else:
                    # New user, send welcome message
                    response_message = "Welcome to the bot! 😊 How can I assist you today?"
                    save_user_history(user_id, "Unknown", [])

                # Send response to Telegram
                send_message_to_user(chat_id, response_message)
                return {"status": "ok"}

            # Text message
            if "text" in data["message"]:
                user_text = data["message"]["text"]
                process_message(chat_id, user_id, user_text, "text")

            # Photo message
            elif "photo" in data["message"]:
                photo_file_id = data["message"]["photo"][-1]["file_id"]
                file_response = requests.get(f"{TELEGRAM_API}/getFile?file_id={photo_file_id}")
                file_path = file_response.json()["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
                caption = data["message"].get("caption", None)
                process_message(chat_id, user_id, None, "image", extra={"caption": caption, "image_url": file_url})

            # Unsupported media
            else:
                response_message = "Unable to process your request."
                send_message_to_user(chat_id, response_message)

        return {"status": "ok"}
    return "Telegram bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
