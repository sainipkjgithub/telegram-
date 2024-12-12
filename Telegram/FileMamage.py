from flask import Flask, request
import requests
import json

app = Flask(__name__)

# Telegram Bot Configuration
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
PRIVATE_CHANNEL_ID = "-100XXXXXXXXXX"  # Replace with your private channel ID

# Notion API Configuration
NOTION_API_KEY = "YOUR_NOTION_API_KEY"
MASTER_DATABASE_ID = "YOUR_MASTER_DATABASE_ID"
PAGE_ID = "YOUR_MASTER_PAGE_ID"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


# Function to create a new database from a given Page ID
def create_database_from_page(page_id, database_title):
    payload = {
        "parent": {"type": "page_id", "page_id": page_id},
        "title": [{"type": "text", "text": {"content": database_title}}],
        "properties": {
            "Name": {"title": {}},
            "Message ID": {"number": {}},
            "Type": {"rich_text": {}},
            "Page ID": {"rich_text": {}},
            "Database ID": {"rich_text": {}}
        }
    }
    response = requests.post(
        "https://api.notion.com/v1/databases",
        headers=NOTION_HEADERS,
        json=payload
    )
    return response.json().get("id")


# Function to create a new page in a database using Database ID
def create_page_in_database(database_id, name, page_type, page_id=None, database_id_for_page=None):
    properties = {
        "Name": {"title": [{"text": {"content": name}}]},
        "Type": {"rich_text": [{"text": {"content": page_type}}]},
    }
    if page_id:
        properties["Page ID"] = {"rich_text": [{"text": {"content": page_id}}]}
    if database_id_for_page:
        properties["Database ID"] = {"rich_text": [{"text": {"content": database_id_for_page}}]}

    payload = {
        "parent": {"database_id": database_id},
        "properties": properties
    }
    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=payload
    )
    return response.json()


# Function to list files and folders in a database
def list_files_and_folders(chat_id, database_id):
    response = requests.post(
        f"https://api.notion.com/v1/databases/{database_id}/query",
        headers=NOTION_HEADERS
    )
    data = response.json()
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
