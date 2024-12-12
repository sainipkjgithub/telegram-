import requests

NOTION_API_KEY = "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"
Page_Id = "1597280d4cf580a48094c9959f837f09"
MASTER_DATABASE_ID = "15a7280d4cf580ceb31ff04a1a6eede3"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

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
            "User ID": {"title": [{"text": {"content": str(user_id)}}]},
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
            "File Type": {"rich_text": {}},
            "Page ID": {"rich_text": {}}  # Adding Page ID property
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

    # Create a new page in the database
    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=notion_data
    )
    response_data = response.json()

    # Fetch the Page ID from the response and update the page with it
    page_id = response_data.get("id")
    if page_id:
        notion_data["properties"]["Page ID"] = {"rich_text": [{"text": {"content": page_id}}]}
        requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=NOTION_HEADERS,
            json={"properties": {"Page ID": {"rich_text": [{"text": {"content": page_id}}]}}}
        )
