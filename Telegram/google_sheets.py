# google_sheets.py
import requests
import json

def save_user_history_to_google(user_id, message_history, pending_status, error, app_script_url):
    payload = {
        "user_id": user_id,
        "message_history": json.dumps(message_history),
        "pending_status": pending_status,
        "error": error
    }
    response = requests.post(app_script_url, json=payload)
    return response.status_code

def get_user_history_from_google(user_id, app_script_url):
    response = requests.get(app_script_url, params={"user_id": user_id})
    if response.status_code == 200:
        data = response.json()
        return data.get("message_history", [])
    return []
