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
MASTER_DATABASE_ID = "1597280d4cf580869413f6a1e716db4f"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

PRIVATE_CHANNEL_ID = "-1002308495574"  # Private channel ID

pending_deletions = {}  # Tracks users who initiated account deletion


# Fetch user from master database
def get_user_from_master(user_id):
    query_payload = {
        "filter": {
            "property": "User ID",
            "rich_text": {"equals": str(user_id)}
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
        user_page_id = user_entry["id"]
        database_id = user_entry["properties"]["Database ID"]["rich_text"][0]["text"]["content"]
        return {"database_id": database_id, "page_id": user_page_id}
    return None


# Delete a user's database from Notion
def delete_user_database(database_id):
    delete_url = f"https://api.notion.com/v1/databases/{database_id}"
    response = requests.delete(delete_url, headers=NOTION_HEADERS)
    return response.status_code == 200  # Return True if deletion succeeded


# Delete user record from the master database
def delete_user_from_master(page_id):
    delete_url = f"https://api.notion.com/v1/pages/{page_id}"
    response = requests.delete(delete_url, headers=NOTION_HEADERS)
    return response.status_code == 200  # Return True if deletion succeeded


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            user_message = data["message"]["text"]

            if user_message == "/deleteAccount":
                # Step 1: Send confirmation message
                pending_deletions[chat_id] = True
                response_text = (
                    "Are you sure you want to delete your account?\n"
                    "If yes, please reply with: YES DELETE MY ACCOUNT\n"
                    "**This action cannot be undone.**"
                )
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

            elif user_message == "YES DELETE MY ACCOUNT" and chat_id in pending_deletions:
                # Step 2: Confirm deletion and delete data
                user_data = get_user_from_master(chat_id)
                if user_data:
                    database_id = user_data["database_id"]
                    page_id = user_data["page_id"]

                    # Delete user database
                    db_deleted = delete_user_database(database_id)
                    # Delete from master database
                    master_deleted = delete_user_from_master(page_id)

                    if db_deleted and master_deleted:
                        response_text = "Your account has been successfully deleted."
                    else:
                        response_text = "Failed to delete your account. Please try again later."
                else:
                    response_text = "No account found to delete."

                # Clear pending deletion for the user
                pending_deletions.pop(chat_id, None)
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

            elif user_message == "YES DELETE MY ACCOUNT":
                # Step 3: Handle invalid state (if no pending deletion exists)
                response_text = "You haven't initiated an account deletion request. Send /deleteAccount to start."
                requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})

        return {"status": "ok"}
    return "Telegram bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)