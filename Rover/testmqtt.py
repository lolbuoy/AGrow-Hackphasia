from dronekit import connect
import paho.mqtt.client as mqtt
import random
import time
import json  # To structure the data as JSON

# Global variables
vehicle = None
mqtt_client = None
broker_address = "100.109.46.43"  # Change this to your MQTT broker's address
mqtt_port = 1883
mqtt_keepalive = 60
publish_interval = 5  # Interval to publish data in seconds


def connect_vehicle(connection_string="127.0.0.1:14551"):
    """Connect to the vehicle."""
    global vehicle
    print("Connecting to vehicle...")
    vehicle = connect(connection_string, wait_ready=True)
    print("Vehicle connected.")
    print(f"MAVLink System ID: {vehicle._handler.master.mav.srcSystem}")


def connect_mqtt():
    """Connect to the MQTT broker."""
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.connect(broker_address, mqtt_port, mqtt_keepalive)
    print(f"Connected to MQTT broker at {broker_address}:{mqtt_port}")


def generate_soil_data():
    """Generate dummy soil data."""
    data = {

        "details": {
            "lat": vehicle.location.global_frame.lat,
            "lon": vehicle.location.global_frame.lon,
            "soil_pH": round(random.uniform(4.5, 8.5), 2),
            "texture": random.choice(["Sandy", "Loamy", "Clay"]),
            "organic_content": round(random.uniform(0.5, 5.0), 2),  # Percentage
            "moisture_content": round(random.uniform(5.0, 35.0), 2),  # Percentage
            "bulk_density": round(random.uniform(1.1, 1.6), 2),  # g/cm^3
            "nitrogen_ppm": random.randint(10, 100),  # ppm
            "potassium_ppm": random.randint(50, 200),  # ppm
            "phosphorus_ppm": random.randint(10, 60),  # ppm
            "cation_exchange_capacity": round(random.uniform(5.0, 40.0), 2),  # meq/100g
            "electrical_conductivity": round(random.uniform(0.1, 1.5), 2),  # dS/m
            "soil_colour": random.choice(["Brown", "Dark Brown", "Reddish", "Black"]),
            "porosity": round(random.uniform(30.0, 50.0), 2),  # Percentage
            "water_holding_capacity": round(random.uniform(20.0, 60.0), 2),  # Percentage,
        },
    }
    return data


def publish_soil_data():
    """Publish soil data to MQTT topic."""
    global vehicle, mqtt_client
    rover_id = vehicle._handler.master.mav.srcSystem  # ThisMAV.sysid
    topic = f"ground/{rover_id}/data"

    while True:
        # Generate soil data
        soil_data = generate_soil_data()
        json_payload = json.dumps(soil_data)  # Convert data to JSON string

        print(f"Publishing to topic '{topic}': {json_payload}")

        # Publish to MQTT topic
        mqtt_client.publish(topic, json_payload)
        time.sleep(publish_interval)


if __name__ == "__main__":
    try:
        # Connect to the vehicle and MQTT broker
        connect_vehicle()
        connect_mqtt()

        # Start publishing soil data
        publish_soil_data()

    finally:
        if vehicle:
            vehicle.close()
            print("Vehicle connection closed.")
        if mqtt_client:
            mqtt_client.disconnect()
            print("MQTT connection closed.")
