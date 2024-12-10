# paxsenix_api.py
import requests

def call_paxsenix_api(conversation_history, paxsenix_api_url):
    payload = {
        "messages": conversation_history
    }
    response = requests.post(paxsenix_api_url, json=payload)
    response_data = response.json()
    
    if "message" not in response_data:
        raise Exception("Failed to get a valid response from Panisec API")
    
    return response_data
