from flask import Flask, request
import requests
from notion import upload_to_user_database, get_user_from_master, create_user_database

app = Flask(__name__)

# Telegram Bot Configuration
TELEGRAM_TOKEN = "7645816977:AAH6kuSygVwuGhPAlvt_4otirHQhxI9wmYw"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

PRIVATE_CHANNEL_ID = "-1002308495574"  # Private channel ID

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            full_name = data["message"]["chat"].get("first_name", "") + " " + data["message"]["chat"].get("last_name", "")

            if "text" in data["message"]:
                text = data["message"]["text"]

                if text == "/start":
                    response_text = "Hello! Use /upload to upload a file and /list to see your uploaded files."
                    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

                elif text == "/upload":
                    response_text = "Please send the file you want to upload."
                    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

                elif text == "/list":
                    database_id = get_user_from_master(chat_id)
                    if not database_id:
                        response_text = "No files found. Use /upload to start uploading files."
                        requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})
                    else:
                        response = requests.post(
                            f"https://api.notion.com/v1/databases/{database_id}/query",
                            headers={"Authorization": "Bearer YOUR_NOTION_API_KEY"}
                        )
                        data = response.json()
                        files = [
                            {
                                "name": result["properties"]["File Name"]["rich_text"][0]["text"]["content"],
                                "msg_id": result["properties"]["Message ID"]["number"]
                            }
                            for result in data.get("results", [])
                        ]
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": file["name"], "callback_data": str(file["msg_id"])}] for file in files
                            ]
                        }
                        response_text = "Select a file to download:"
                        requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text, "reply_markup": keyboard})

            elif "document" in data["message"] or "photo" in data["message"] or "video" in data["message"]:
                if "document" in data["message"]:
                    file_id = data["message"]["document"]["file_id"]
                    file_name = data["message"]["document"]["file_name"]
                elif "photo" in data["message"]:
                    file_id = data["message"]["photo"][-1]["file_id"]
                    file_name = "photo.jpg"
                elif "video" in data["message"]:
                    file_id = data["message"]["video"]["file_id"]
                    file_name = "video.mp4"

                forward_response = requests.post(f"{TELEGRAM_API}/forwardMessage", json={
                    "chat_id": PRIVATE_CHANNEL_ID,
                    "from_chat_id": chat_id,
                    "message_id": data["message"]["message_id"]
                })

                forward_data = forward_response.json()
                message_id = forward_data["result"]["message_id"]

                upload_to_user_database(file_name, chat_id, full_name, message_id)
                response_text = "File uploaded successfully!"
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

        elif "callback_query" in data:
            callback_data = data["callback_query"]["data"]
            chat_id = data["callback_query"]["from"]["id"]

            requests.post(f"{TELEGRAM_API}/copyMessage", json={
                "chat_id": chat_id,
                "from_chat_id": PRIVATE_CHANNEL_ID,
                "message_id": int(callback_data)
            })

        return {"status": "ok"}
    return "Telegram bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
