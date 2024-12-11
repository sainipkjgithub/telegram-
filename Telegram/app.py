from flask import Flask, request
import requests
import json

app = Flask(__name__)

# Telegram Bot Configuration
TELEGRAM_TOKEN = "7645816977:AAH6kuSygVwuGhPAlvt_4otirHQhxI9wmYw"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Notion API Configuration
NOTION_API_KEY = "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"  # Replace with your Notion API Key
NOTION_DATABASE_ID = "15931e04de46804f8c9cd42d7514e4bd"  # Replace with your Notion Database ID
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Private Channel ID for storing files
PRIVATE_CHANNEL_ID = "-1002308495574"


# Upload file to Telegram channel and save metadata in Notion
def upload_to_channel(file_id, file_name, user_id, action_id):
    # Send file to private channel
    response = requests.post(
        f"{TELEGRAM_API}/sendDocument",
        json={"chat_id": PRIVATE_CHANNEL_ID, "document": file_id, "caption": f"File: {file_name}"}
    )
    message_data = response.json()
    if not message_data.get("ok"):
        return None
    
    message_id = message_data["result"]["message_id"]

    # Save file metadata to Notion
    notion_data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "User ID": {"rich_text": [{"text": {"content": str(user_id)}}]},
            "File Name": {"title": [{"text": {"content": file_name}}]},
            "Message ID": {"number": message_id},
            "File Type": {"rich_text": [{"text": {"content": "document"}}]},
            "Action ID": {"rich_text": [{"text": {"content": action_id}}]}
        }
    }
    notion_response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=notion_data
    )
    return notion_response.status_code == 200


# Fetch files uploaded by a specific user from Notion
def list_files(user_id):
    query = {
        "filter": {
            "property": "User ID",
            "rich_text": {"equals": str(user_id)}
        }
    }
    response = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=NOTION_HEADERS,
        json=query
    )
    data = response.json()
    files = []
    for result in data.get("results", []):
        file_name = result["properties"]["File Name"]["title"][0]["text"]["content"]
        message_id = result["properties"]["Message ID"]["number"]
        files.append({"file_name": file_name, "message_id": message_id})
    return files


# Fetch and send a specific file from the private channel to the user
def fetch_and_send_file(chat_id, message_id):
    response = requests.post(
        f"{TELEGRAM_API}/copyMessage",
        json={"chat_id": chat_id, "from_chat_id": PRIVATE_CHANNEL_ID, "message_id": message_id}
    )
    return response.ok


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json
        chat_id = data["message"]["chat"]["id"]
        if "text" in data["message"]:
            text = data["message"]["text"]

            if text.startswith("/upload"):
                # Inform user to send file
                response_text = "Please send the file you want to upload."
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})
            
            elif text == "/list":
                # List all files for the user
                files = list_files(chat_id)
                if files:
                    response_text = "\n".join([f"{i+1}. {file['file_name']}" for i, file in enumerate(files)])
                else:
                    response_text = "No files found."
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})
            
            elif text.isdigit():
                # Send specific file based on user's choice
                files = list_files(chat_id)
                file_index = int(text) - 1
                if 0 <= file_index < len(files):
                    fetch_and_send_file(chat_id, files[file_index]["message_id"])
                else:
                    response_text = "Invalid file ID."
                    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})
        
        elif "document" in data["message"]:
            # Handle file upload
            file_id = data["message"]["document"]["file_id"]
            file_name = data["message"]["document"]["file_name"]
            action_id = "upload_file"
            if upload_to_channel(file_id, file_name, chat_id, action_id):
                response_text = "File uploaded successfully!"
            else:
                response_text = "Failed to upload file."
            requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

        return {"status": "ok"}
    return "Telegram bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
