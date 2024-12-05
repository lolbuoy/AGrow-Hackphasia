import math
import json
import paho.mqtt.client as mqtt
from config import CONFIG
from .db import db


def get_mqtt_client_for_publish():
    """Returns a configured MQTT client for publishing messages."""
    client = mqtt.Client()
    # Uncomment if credentials are needed
    # client.username_pw_set(CONFIG.MQTT_USER, CONFIG.MQTT_PASSWORD)
    client.connect(host=CONFIG.MQTT_HOST, port=CONFIG.MQTT_PORT)
    return client


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    # Subscribe to the desired pattern
    client.subscribe("ground/+/data")


def handle_data_message(msg, payload):
    rover_id = msg.topic.split("/")[1]
    plot_id = payload.get("plot_id")
    details = payload.get("details", {})

    key = f"rover_{rover_id}"

    to_update = [{"plot_id": plot_id, "details": details}]

    existing_data = db.get_key(key)
    if existing_data:
        as_list = list(json.loads(existing_data))
        for x in as_list:
            if plot_id != x.get("plot_id"):
                to_update.append(x)

    db.set_key(key, json.dumps(to_update))


def on_message(client, userdata, msg):
    try:
        message_contents = msg.payload.decode()

        print(f"Received message: {msg.topic} -> {message_contents}")

        payload = json.loads(message_contents)
        print("PARSED:")
        print(payload)

        if msg.topic.startswith("ground/") and msg.topic.endswith("/data"):
            handle_data_message(msg, payload)

    except Exception as e:
        print("EXCEPTION ON MESSAGE")
        print(e)
        print(userdata, msg)


def run_mqtt():
    client = mqtt.Client()
    # Uncomment this if you need to use credentials
    # client.username_pw_set(CONFIG.MQTT_USER, CONFIG.MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host=CONFIG.MQTT_HOST, port=CONFIG.MQTT_PORT, keepalive=65535)
    client.loop_forever()
