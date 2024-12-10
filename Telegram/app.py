from flask import Flask, request
import requests
import threading
import json

app = Flask(__name__)

# Telegram Bot Token
TELEGRAM_TOKEN = "8169493568:AAHgkbPTtukjYrrQDOk8zFrMN7jubQmuqV8"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# PaxSenix API URLs
TEXT_API_URL = "https://api.paxsenix.biz.id/ai/gpt4o"
IMAGE_API_URL = "https://api.paxsenix.biz.id/ai/geminivision"

# Google Apps Script API URL to save chat history
SAVE_HISTORY_API_URL = "https://script.google.com/macros/s/AKfycbz74t0Aw9DoINW2R2u2AXwB1m-5YqRzPBWE7VE9zAdCNn8nFtuD_ksj_XlCrJNKKNhybQ/exec"

def send_typing_action(chat_id):
    """
    Sends typing action to Telegram to show typing status.
    """
    requests.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})

def get_user_history(user_id):
    """
    Fetches the user message history from Google Sheets.
    """
    response = requests.get(f"{SAVE_HISTORY_API_URL}?userId={user_id}")
    history_data = response.json()
    return history_data.get("user", {}).get("Message History", []), history_data.get("success", False)

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

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json

        if "message" in data:  # Check if it's a message
            chat_id = data["message"]["chat"]["id"]
            user_id = str(chat_id)  # Using chat_id as user_id for simplicity

            # Start typing status in a separate thread
            threading.Thread(target=send_typing_action, args=(chat_id,)).start()

            # Check if user exists or not
            user_history, user_exists = get_user_history(user_id)

            # Handle text message
            if "text" in data["message"]:
                user_text = data["message"]["text"]

                if not user_exists:  # If user is new
                    # Initialize an empty history if user is new
                    user_history = [{"role": "user", "content": user_text}]
                else:
                    # Add the user message to history
                    user_history.append({"role": "user", "content": user_text})

                # Call PaxSenix GPT-4o API
                response = requests.post(TEXT_API_URL, headers={
                    "accept": "application/json",
                    "Content-Type": "application/json"
                }, json={"messages": user_history})

                response_text = response.json().get("message", "I couldn't process your request.")

                # Add PaxSenix's reply to history
                user_history.append({"role": "assistant", "content": response_text})

                # Send the response back to Telegram
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

                # Save updated history
                save_user_history(user_id, "Unknown", user_history)

            # Handle photo message
            elif "photo" in data["message"]:
                user_caption = data["message"].get("caption", "Please Describe this Image")

                # Send image to the PaxSenix GeminiVision API directly without history
                photo_file_id = data["message"]["photo"][-1]["file_id"]  # Highest resolution
                file_response = requests.get(f"{TELEGRAM_API}/getFile?file_id={photo_file_id}")
                file_path = file_response.json()["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

                # Call PaxSenix GeminiVision API
                image_response = requests.get(f"{IMAGE_API_URL}?text={user_caption}&url={file_url}", headers={
                    "accept": "application/json"
                })

                response_text = image_response.json().get("message", "I couldn't process the image.")

                # Add the image icon to history
                user_history.append({"role": "user", "content": "📷"})

                # Add PaxSenix's reply to history
                user_history.append({"role": "assistant", "content": response_text})

                # Send the response back to Telegram
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

                # Save updated history
                save_user_history(user_id, "Unknown", user_history)

            # Handle unsupported media
            else:
                response_text = "I am unable to process your request."
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

        return {"status": "ok"}
    return "Telegram bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
