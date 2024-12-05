from flask_cors import CORS
import json
from flask import Flask
from config import CONFIG
from .db import db
from .mqtt import get_mqtt_client_for_publish

app = Flask(__name__)
cors = CORS(app)

mqtt_client = get_mqtt_client_for_publish()


@app.route("/")
def home():
    return "Flask Server is running!"


@app.post("/send/<rover_id>")
def send_rover_data(rover_id):
    redis_key = f"rover_{rover_id}"

    redis_data = db.get_key(redis_key)
    if redis_data:
        data = json.loads(redis_data)

        print("EXISTING DATA:", data)
        print("PUBLISHING DATA TO:", f"ai/crops/{rover_id}/request", json.dumps(data))

        mqtt_client.publish(f"ai/crops/{rover_id}/request", json.dumps(data))

        return "Data found and sent", 200
    else:
        return "Data not found", 500


@app.get("/data/<rover_id>")
def get_rover_data(rover_id):
    redis_key = f"rover_{rover_id}"

    redis_data = db.get_key(redis_key)
    return redis_data


def run_server():
    app.run(host=CONFIG.HOST, port=CONFIG.PORT)
