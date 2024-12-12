from flask import Flask, request
import requests
import json

app = Flask(__name__)

# Telegram Bot Configuration
TELEGRAM_TOKEN = "7645816977:AAH6kuSygVwuGhPAlvt_4otirHQhxI9wmYw"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Notion API Configuration
NOTION_API_KEY = "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"
Page_Id = "1597280d4cf580a48094c9959f837f09"
MASTER_DATABASE_ID = "15a7280d4cf580ceb31ff04a1a6eede3"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

PRIVATE_CHANNEL_ID = "-1002308495574"  # Private channel ID


# Fetch user from master database
def get_user_from_master(user_id):
    query_payload = {
        "filter": {
            "property": "User ID",
            "title": {"equals": str(user_id)}
        }
    }
    response = requests.post(
        f"https://api.notion.com/v1/databases/{MASTER_DATABASE_ID}/query",
        headers=NOTION_HEADERS,
        json=query_payload
    )
    data = response.json()
    if data.get("results"):
        user_entry = data["results"][0]
        database_id = user_entry["properties"]["Database ID"]["rich_text"][0]["text"]["content"]
        return database_id
    return None


# Add user record to master database
def add_to_master_database(user_id, full_name, database_id):
    payload = {
        "parent": {"database_id": MASTER_DATABASE_ID},
        "properties": {
            "User ID": {"title": {}},
            "Full Name": {"rich_text": [{"text": {"content": full_name}}]},
            "Database ID": {"rich_text": [{"text": {"content": database_id}}]}
        }
    }
    requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=payload
    )


# Create a new database for a user in Notion
def create_user_database(user_id, full_name):
    title = f"User ID - {user_id}"
    payload = {
        "parent": {"type": "page_id", "page_id": Page_Id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": {
            "Name": {"title": {}},
            "File Name": {"rich_text": {}},
            "Message ID": {"number": {}},
            "File Type": {"rich_text": {}}
        }
    }
    response = requests.post(
        "https://api.notion.com/v1/databases",
        headers=NOTION_HEADERS,
        json=payload
    )
    data = response.json()
    database_id = data.get("id")

    if database_id:
        add_to_master_database(user_id, full_name, database_id)
    return database_id


# Upload file to the user's Notion database
def upload_to_user_database(file_name, user_id, full_name, message_id):
    # Check if the user exists and get the database ID
    database_id = get_user_from_master(user_id)

    # If user doesn't exist, create a new database
    if not database_id:
        database_id = create_user_database(user_id, full_name)

    # Save file metadata to the user's database
    notion_data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": file_name}}]},
            "File Name": {"rich_text": [{"text": {"content": file_name}}]},
            "Message ID": {"number": message_id},
            "File Type": {"rich_text": [{"text": {"content": "document"}}]}
        }
    }

    requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=notion_data
    )


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
                    else:
                        response = requests.post(
                            f"https://api.notion.com/v1/databases/{database_id}/query",
                            headers=NOTION_HEADERS
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
