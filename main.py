import os
import time
import json
import threading
import requests
from flask import Flask, jsonify
from google.cloud import pubsub_v1

app = Flask(__name__)

project_id = "pgc-one-primer-dw"
subscription_id = "bartender-error-notifier-sub"
chat_webhook_url = "https://chat.googleapis.com/v1/spaces/AAQAv2hHlVo/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=26B8Ir5zpHiqhNIYD6wFFa9fk7ruoS-_70aaNsvKyqA"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

# ------------------------------
# Google Chat notification logic
# ------------------------------


def send_to_google_chat(log_entry):
    try:
        param = log_entry.get("httpRequest", {}).get("requestUrl", "N/A")
        param_val = param.rsplit("/", 1)[-1]
        print(param_val)

        final_param = param_val.split("?", 1)[1] if "?" in param_val else "N/A"
        print(final_param)

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


# ------------------------------
# Pub/Sub message processing
# ------------------------------
def callback(message):
    try:
        data = json.loads(message.data.decode("utf-8"))
        http_request = data.get("httpRequest", {})
        status = http_request.get("status")

        if status == 404:
            print("🚨 404 Log Entry Detected!")
            send_to_google_chat(data)
    except Exception as e:
        print(f"⚠️ Error parsing message: {e}")
    finally:
        message.ack()


def start_subscriber():
    print("🚀 Starting Pub/Sub subscriber...")
    subscriber.subscribe(subscription_path, callback=callback)
    while True:
        time.sleep(60)


# ------------------------------
# Flask endpoints for Cloud Run
# ------------------------------
@app.route("/")
def home():
    return jsonify({"status": "running", "message": "Bartender Notifier Service active."})


@app.route("/start", methods=["POST"])
def start_service():
    """Manually start subscriber (optional endpoint)"""
    thread = threading.Thread(target=start_subscriber, daemon=True)
    thread.start()
    return jsonify({"status": "subscriber started"})


# ------------------------------
# Run Flask app
# ------------------------------
if __name__ == "__main__":
    # Start subscriber in background
    threading.Thread(target=start_subscriber, daemon=True).start()
    # app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    app.run(debug=True)
