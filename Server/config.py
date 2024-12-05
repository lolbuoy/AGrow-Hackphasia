import dotenv
import os
import json

dotenv.load_dotenv()


class CONFIG:
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = int(os.getenv("REDIS_PORT"))
    REDIS_DB = int(os.getenv("REDIS_DB"))
    REDIS_USERNAME = os.getenv("REDIS_USERNAME")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

    MQTT_HOST = os.getenv("MQTT_HOST")
    MQTT_PORT = 1883
    MQTT_USER = os.getenv("MQTT_USER", None)
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", None)

    HOST = os.getenv("HOST")
    PORT = int(os.getenv("PORT", 8827))

    # ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

    # GRIDLINES_TOKEN = os.getenv("GRIDLINES_TOKEN")

    # TRAINING_SAVE = os.getenv("TRAINING_SAVE")
    # ALL_SAVE = os.getenv("ALL_SAVE")

    # ROBOFLOW_KEY = os.getenv("ROBOFLOW_KEY")

    # LLAMA_TOKEN = os.getenv("LLAMA_TOKEN")

    # if not ADMIN_TOKEN or not LLAMA_TOKEN:
    #     raise RuntimeError("ADMIN_TOKEN/LLAMA_TOKEN NOT SET!")
