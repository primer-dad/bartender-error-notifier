import os
import json
import requests
from flask import Flask, request, jsonify
from google.cloud import pubsub_v1
import functions_framework

app = Flask(__name__)

project_id = "pgc-one-primer-dw"
subscription_id = "bartender-error-notifier-sub"
chat_webhook_url = "https://chat.googleapis.com/v1/spaces/AAQAv2hHlVo/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=26B8Ir5zpHiqhNIYD6wFFa9fk7ruoS-_70aaNsvKyqA"

# ----------------------------------------------------
# Function to send message to Google Chat
# ----------------------------------------------------
def send_to_google_chat(log_entry):
    try:
        param = log_entry.get("httpRequest", {}).get("requestUrl", "N/A")
        param_val = param.rsplit("/", 1)[-1] if "/" in param else "N/A"
        final_param = param_val.split("?", 1)[1] if "?" in param_val else "N/A"

        text = (
            "🚨 *404 API Log Detected!*\n"
            f"*Service:* {log_entry.get('resource', {}).get('labels', {}).get('service_name', 'unknown')}\n"
            f"*Method:* {log_entry.get('httpRequest', {}).get('requestMethod', 'N/A')}\n"
            f"*URL:* {log_entry.get('httpRequest', {}).get('requestUrl', 'N/A')}\n"
            f"*Parameters:* {final_param}\n"
            f"*Status:* {log_entry.get('httpRequest', {}).get('status', 'N/A')}\n"
            f"*Timestamp:* {log_entry.get('timestamp', 'N/A')}"
        )

        response = requests.post(chat_webhook_url, json={"text": text})
        if response.status_code != 200:
            print(f"⚠️ Failed to send message to Chat: {response.text}")
        else:
            print("✅ Sent 404 log to Google Chat.")
    except Exception as e:
        print(f"⚠️ Error sending message to Chat: {e}")


# ----------------------------------------------------
# Cloud Function (Triggered by Pub/Sub)
# ----------------------------------------------------
@functions_framework.cloud_event
def pubsub_handler(cloud_event):
    """
    Cloud Run entrypoint for Pub/Sub-triggered events.
    """
    try:
        message_data = cloud_event.data.get("message", {}).get("data")
        if not message_data:
            print("⚠️ No data in message.")
            return

        decoded = json.loads(base64.b64decode(message_data).decode("utf-8"))
        http_request = decoded.get("httpRequest", {})
        status = http_request.get("status")

        if status == 404:
            print("🚨 404 Log Entry Detected!")
            send_to_google_chat(decoded)
        else:
            print(f"Ignored non-404 log (status: {status})")

    except Exception as e:
        print(f"⚠️ Error processing Pub/Sub message: {e}")


# ----------------------------------------------------
# Optional Flask endpoints (for health check & debug)
# ----------------------------------------------------
@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "Bartender Notifier is running."})


@app.route("/test", methods=["POST"])
def test_message():
    """
    Local test endpoint — send a fake 404 log to Chat.
    """
    mock_log = {
        "httpRequest": {
            "requestUrl": "https://api.example.com/test?id=123",
            "status": 404,
            "requestMethod": "GET",
        },
        "resource": {"labels": {"service_name": "mock-service"}},
        "timestamp": "2025-10-29T00:00:00Z",
    }
    send_to_google_chat(mock_log)
    return jsonify({"status": "sent"})


# ----------------------------------------------------
# Entry point for local testing
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
