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
        return {"error": "Failed to forward file to Telegram channel."}
    
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
    return notion_response.json()  # Return the full response from Notion


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
        
        elif "document" in data["message"]:
            # Handle file upload
            file_id = data["message"]["document"]["file_id"]
            file_name = data["message"]["document"]["file_name"]
            action_id = "upload_file"

            # Upload file to Notion and get the response
            notion_response = upload_to_channel(file_id, file_name, chat_id, action_id)

            # Send the Notion response back to the user
            response_text = f"Notion Response:\n{json.dumps(notion_response, indent=2)}"
            requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

        return {"status": "ok"}
    return "Telegram bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
