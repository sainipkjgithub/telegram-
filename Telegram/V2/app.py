from flask import Flask, request
import requests
import json

app = Flask(__name__)

# Telegram Bot Configuration
TELEGRAM_TOKEN = "7645816977:AAH6kuSygVwuGhPAlvt_4otirHQhxI9wmYw"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Notion API Configuration
NOTION_API_KEY = "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"  # Replace with your Notion API Key
Page_Id = "1597280d4cf580a48094c9959f837f09"
MASTER_DATABASE_ID = "1597280d4cf580869413f6a1e716db4f"  # Master Database ID in Notion
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

user_databases = {}  # Dictionary to store User ID to Database ID mapping


# Add user record to Master Database
def add_to_master_database(user_id, user_name, database_id):
    payload = {
        "parent": {"database_id": MASTER_DATABASE_ID},
        "properties": {
            "User ID": {"rich_text": [{"text": {"content": str(user_id)}}]},
            "User Name": {"rich_text": [{"text": {"content": user_name}}]},
            "Database ID": {"rich_text": [{"text": {"content": database_id}}]}
        }
    }
    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=payload
    )
    return response.json()  # Return the response


# Create a new database for a user in Notion
def create_user_database(user_id, user_name):
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
        # Add user to master database
        add_to_master_database(user_id, user_name, database_id)
    return database_id


# Upload file to the user's Notion database
def upload_to_user_database(file_id, file_name, user_id, user_name, action_id):
    # Create a user-specific database if it doesn't exist
    if user_id not in user_databases:
        database_id = create_user_database(user_id, user_name)
        if not database_id:
            return {"error": "Failed to create user-specific database."}
        user_databases[user_id] = database_id

    # Save file metadata to the user's database
    notion_data = {
        "parent": {"database_id": user_databases[user_id]},
        "properties": {
            "Name": {"title": [{"text": {"content": file_name}}]},
            "File Name": {"rich_text": [{"text": {"content": file_name}}]},
            "Message ID": {"number": 12345},  # Example message ID, update dynamically
            "File Type": {"rich_text": [{"text": {"content": "document"}}]}
        }
    }

    notion_response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=notion_data
    )
    return notion_response.json()  # Return the full response from Notion


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json
        chat_id = data["message"]["chat"]["id"]
        user_name = data["message"]["chat"]["username"] or "Unknown"

        if "text" in data["message"]:
            text = data["message"]["text"]

            if text == "/start":
                response_text = "Hello! Use /upload to upload a file and /list to see your uploaded files."
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

            elif text == "/upload":
                response_text = "Please send the file you want to upload."
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

            elif text == "/list":
                # List all files for the user
                if chat_id not in user_databases:
                    response_text = "No files found. Use /upload to start uploading files."
                else:
                    response = requests.post(
                        f"https://api.notion.com/v1/databases/{user_databases[chat_id]}/query",
                        headers=NOTION_HEADERS
                    )
                    data = response.json()
                    files = [
                        result["properties"]["File Name"]["rich_text"][0]["text"]["content"]
                        for result in data.get("results", [])
                    ]
                    response_text = "\n".join([f"{i+1}. {file}" for i, file in enumerate(files)]) or "No files found."
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

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

            action_id = "upload_file"

            notion_response = upload_to_user_database(file_id, file_name, chat_id, user_name, action_id)
            response_text = f"Notion Response:\n{json.dumps(notion_response, indent=2)}"
            requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

        return {"status": "ok"}
    return "Telegram bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
