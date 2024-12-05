import json
import time
import paho.mqtt.client as mqtt

# MQTT broker configuration
broker_address = "100.109.46.43"  # Replace with your MQTT broker address
mqtt_port = 1883
mqtt_keepalive = 60
rover_id = "255"  # Example ROVER_ID
topic = f"ground/{rover_id}/plan"

# Polygon coordinates as a list of [latitude, longitude] pairs
polygon_coords = [
    [12.523,76.894],
    [12.523, 76.896],
    [12.525, 76.896],
    [12.525, 76.894],
    [12.523, 76.894],
]

# JSON payload containing only the list of coordinates
payload = polygon_coords  # Directly set to the list

# Connect to MQTT broker and publish data
def on_connect(client, userdata, flags, rc):
    """Callback for when the client receives a CONNACK response from the server."""
    if rc == 0:
        print("MQTT client connected successfully.")
    else:
        print(f"MQTT connection failed with return code {rc}")

def publish_polygon_data():
    try:
        # Create an MQTT client
        mqtt_client = mqtt.Client()

        # Assign on_connect callback
        mqtt_client.on_connect = on_connect

        # Connect to the broker
        print(f"Connecting to MQTT broker at {broker_address}:{mqtt_port}...")
        mqtt_client.connect(broker_address, mqtt_port, mqtt_keepalive)

        # Start the MQTT loop in a separate thread
        mqtt_client.loop_start()

        # Publish the polygon data
        payload_json = json.dumps(payload)
        result = mqtt_client.publish(topic, payload_json)
        status = result[0]
        if status == 0:
            print(f"Successfully published polygon data to topic '{topic}':")
            print(payload_json)
        else:
            print(f"Failed to publish message to topic '{topic}'.")

        # Allow time for the message to be sent
        time.sleep(2)

        # Disconnect from the broker
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Disconnected from MQTT broker.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    publish_polygon_data()
