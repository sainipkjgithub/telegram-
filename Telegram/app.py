from flask import Flask, request
import requests
import json

app = Flask(__name__)

# Telegram Bot Configuration
TELEGRAM_TOKEN = "7645816977:AAH6kuSygVwuGhPAlvt_4otirHQhxI9wmYw"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
PRIVATE_CHANNEL_ID = "-1002308495574"  # Replace with your private channel ID

# Notion API Configuration
NOTION_API_KEY = "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"
MASTER_DATABASE_ID = "15a7280d4cf580ceb31ff04a1a6eede3"
PAGE_ID = "1597280d4cf580a48094c9959f837f09"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


# Function to list files and folders in a database
def list_files_and_folders(chat_id, database_id):
    response = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=NOTION_HEADERS
    )
    data = response.json()

    # Send the raw Notion response back to the user
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": f"Notion API Response:\n{json.dumps(data, indent=2)}"
    })

    files = []
    folders = []

    for result in data.get("results", []):
        name = result["properties"]["Name"]["title"][0]["text"]["content"]
        file_type = result["properties"]["Type"]["rich_text"][0]["text"]["content"]
        page_id = result["properties"]["Page ID"]["rich_text"][0]["text"]["content"]

        if file_type == "Folder":
            folders.append({"name": name, "callback_data": page_id})
        elif file_type == "File":
            files.append({"name": name, "callback_data": result["properties"]["Message ID"]["number"]})

    # Creating Inline Keyboard
    inline_keyboard = [
        [{"text": folder["name"], "callback_data": folder["callback_data"]}] for folder in folders
    ] + [
        [{"text": file["name"], "callback_data": str(file["callback_data"])}] for file in files
    ]

    # Adding Extra Buttons
    inline_keyboard.append([{"text": "➕ Add New File", "callback_data": "add_file"}])
    inline_keyboard.append([{"text": "➕ Add New Folder", "callback_data": "add_folder"}])
    if database_id != MASTER_DATABASE_ID:
        inline_keyboard.append([{"text": "🔙 Back", "callback_data": "go_back"}])

    # Sending List
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": "Your Files and Folders:",
        "reply_markup": {"inline_keyboard": inline_keyboard}
    })


# Function to upload a file to the user's database
def upload_file_to_database(file_name, message_id, chat_id, database_id):
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": file_name}}]},
            "Type": {"rich_text": [{"text": {"content": "File"}}]},
            "Message ID": {"number": message_id}
        }
    }
    requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=payload)


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]

            if "text" in data["message"]:
                text = data["message"]["text"]

                if text == "/start":
                    list_files_and_folders(chat_id, MASTER_DATABASE_ID)

                elif text == "/done":
                    list_files_and_folders(chat_id, MASTER_DATABASE_ID)

                else:
                    requests.post(f"{TELEGRAM_API}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": "No valid Command."
                    })

            elif "document" in data["message"]:
                file_id = data["message"]["document"]["file_id"]
                file_name = data["message"]["document"]["file_name"]

                forward_response = requests.post(f"{TELEGRAM_API}/forwardMessage", json={
                    "chat_id": PRIVATE_CHANNEL_ID,
                    "from_chat_id": chat_id,
                    "message_id": data["message"]["message_id"]
                })
                message_id = forward_response.json()["result"]["message_id"]

                upload_file_to_database(file_name, message_id, chat_id, MASTER_DATABASE_ID)

                requests.post(f"{TELEGRAM_API}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "File uploaded successfully! Use /done to view your files."
                })

        elif "callback_query" in data:
            callback_data = data["callback_query"]["data"]
            chat_id = data["callback_query"]["from"]["id"]

            if callback_data == "add_file":
                requests.post(f"{TELEGRAM_API}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "Please upload a file. When done, use /done."
                })

            elif callback_data == "add_folder":
                requests.post(f"{TELEGRAM_API}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "Please send the folder name."
                })

            elif callback_data == "go_back":
                list_files_and_folders(chat_id, MASTER_DATABASE_ID)

            else:
                requests.post(f"{TELEGRAM_API}/copyMessage", json={
                    "chat_id": chat_id,
                    "from_chat_id": PRIVATE_CHANNEL_ID,
                    "message_id": int(callback_data)
                })

        return {"status": "ok"}
    return "Telegram bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
