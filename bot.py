from flask import Flask, request
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = "8169493568:AAHgkbPTtukjYrrQDOk8zFrMN7jubQmuqV8"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "POST":
        data = request.json
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        response_text = f"You said: {text}"
        requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": response_text})
        return {"status": "ok"}
    return "Telegram bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
