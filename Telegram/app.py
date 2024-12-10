from flask import Flask, request
import requests

app = Flask(__name__)

# Telegram Bot Token
TELEGRAM_TOKEN = "8169493568:AAHgkbPTtukjYrrQDOk8zFrMN7jubQmuqV8"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# PaxSenix API URLs
TEXT_API_URL = "https://api.paxsenix.biz.id/ai/gpt4o"
IMAGE_API_URL = "https://api.paxsenix.biz.id/ai/geminivision"

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json

        if "message" in data:  # Check if it's a text or image message
            chat_id = data["message"]["chat"]["id"]

            if "text" in data["message"]:  # Text message
                user_text = data["message"]["text"]
                # Call PaxSenix GPT-4o API
                response = requests.post(TEXT_API_URL, headers={
                    "accept": "application/json",
                    "Content-Type": "application/json"
                }, json={"messages": [{"role": "user", "content": user_text}]})
                
                response_text = response.json().get("message", "I couldn't process your request.")
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

            elif "photo" in data["message"]:  # Photo message
                # Check if a caption is provided
                user_caption = data["message"].get("caption", "Please Describe this Image")

                # Get the file ID of the photo
                photo_file_id = data["message"]["photo"][-1]["file_id"]  # Get the highest resolution
                file_response = requests.get(f"{TELEGRAM_API}/getFile?file_id={photo_file_id}")
                file_path = file_response.json()["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

                # Call PaxSenix GeminiVision API
                image_response = requests.get(f"{IMAGE_API_URL}?text={user_caption}&url={file_url}", headers={
                    "accept": "application/json"
                })

                response_text = image_response.json().get("message", "I couldn't process the image.")
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

        return {"status": "ok"}
    return "Telegram bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
