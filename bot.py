from flask import Flask, request
import requests
import json

app = Flask(__name__)

# Telegram API details
TELEGRAM_TOKEN = "8169493568:AAHiZ6t3my3vyKSfw00GotWD6vflI2RFqb0"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Notion API details
NOTION_TOKEN = "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"
DATABASE_ID = "1597280d4cf580869413f6a1e716db4f"
NOTION_API = "https://api.notion.com/v1/pages"
NOTION_SEARCH_API = "https://api.notion.com/v1/databases/{}/query"

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]

        # Fetch previous messages from Notion
        notion_headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

        # Notion query to fetch messages for the current user (using chat_id)
        notion_query = {
            "filter": {
                "property": "Title",
                "rich_text": {
                    "contains": str(chat_id)
                }
            }
        }
        
        notion_response = requests.post(NOTION_SEARCH_API.format(DATABASE_ID), headers=notion_headers, json=notion_query)

        if notion_response.status_code == 200:
            notion_data = notion_response.json()
            history = ""
            # Loop through previous messages and create a history string
            for result in notion_data.get("results", []):
                history += f"You said: {result['properties']['Message']['rich_text'][0]['text']['content']}\n"
            
            # Combine previous history with current message
            response_text = f"Your previous history:\n{history}\nYou said now: {text}"
        else:
            response_text = f"You said now: {text}"
        
        # Send the response back to Telegram
        requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})
        
        # Save current message to Notion
        notion_payload = {
            "parent": { "database_id": DATABASE_ID },
            "properties": {
                "Title": {
                    "title": [
                        {
                            "text": {
                                "content": f"Message from chat: {chat_id}"
                            }
                        }
                    ]
                },
                "Message": {
                    "rich_text": [
                        {
                            "text": {
                                "content": text
                            }
                        }
                    ]
                }
            }
        }
        
        # Post data to Notion
        requests.post(NOTION_API, headers=notion_headers, json=notion_payload)
        
        return {"status": "ok"}

    return "Telegram bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
