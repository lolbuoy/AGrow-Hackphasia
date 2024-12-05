import random
import json
import time
import threading
import paho.mqtt.client as mqtt
from dronekit import connect, VehicleMode, LocationGlobalRelative
from shapely.geometry import Polygon, Point, box
import folium
import numpy as np

# Global variables
vehicle = None
mqtt_client = None
broker_address = "100.109.46.43"  # MQTT broker address
mqtt_port = 1883
mqtt_keepalive = 60
grid_size = 0.0002  # Grid resolution for scan pattern
chunk_size = 0.001  # Chunk size for dividing polygon
publish_interval = 1  # Interval for real-time data publishing
map_location = (12.524, 76.895)  # Center of the map for visualization
polygon_coords = [(76.894, 12.523), (76.896, 12.523), (76.896, 12.525), (76.8904, 12.525)]  # Define your polygon in (lon, lat)


def connect_vehicle(connection_string="127.0.0.1:14551"):
    """Connect to the vehicle."""
    global vehicle
    print("Connecting to vehicle...")
    vehicle = connect(connection_string, wait_ready=True)
    print("Vehicle connected.")


def arm_and_set_mode(mode="GUIDED"):
    """Arm the vehicle and set the specified mode."""
    global vehicle
    while not vehicle.is_armable:
        print("Waiting for vehicle to become armable...")
        time.sleep(1)

    print("Arming the vehicle...")
    vehicle.mode = VehicleMode(mode)
    vehicle.armed = True

    while not vehicle.armed:
        print("Waiting for vehicle to arm...")
        time.sleep(1)
    print("Vehicle armed.")


def goto_location(lat, lon, alt=10):
    """Navigate to a specific GPS location."""
    global vehicle
    target_location = LocationGlobalRelative(lat, lon, alt)
    print(f"Navigating to: {lat}, {lon}")
    vehicle.simple_goto(target_location)

    while True:
        current_location = vehicle.location.global_frame
        dist = get_distance_metres(current_location, target_location)
        print(f"Distance to target: {dist:.2f}m")

        if dist < 1:  # Stop when close enough
            print("Target reached!")
            break
        time.sleep(1)


def get_distance_metres(aLocation1, aLocation2):
    """Returns the ground distance in meters between two LocationGlobal objects."""
    from math import sin, cos, sqrt, atan2, radians

    lat1, lon1 = radians(aLocation1.lat), radians(aLocation1.lon)
    lat2, lon2 = radians(aLocation2.lat), radians(aLocation2.lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    radius_earth = 6371000  # Radius of Earth in meters
    return radius_earth * c


def connect_mqtt():
    """Connect to the MQTT broker."""
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.connect(broker_address, mqtt_port, mqtt_keepalive)
    print(f"Connected to MQTT broker at {broker_address}:{mqtt_port}")


def real_time_publisher():
    """Publish real-time data in a separate thread."""
    global vehicle, mqtt_client
    topic = f"ground/{vehicle._handler.master.mav.srcSystem}/telemetry"
    while True:
        if vehicle:
            data = {
                "latitude": vehicle.location.global_frame.lat,
                "longitude": vehicle.location.global_frame.lon,
                "altitude": vehicle.location.global_frame.alt,
                "heading": vehicle.heading,
                "mode": vehicle.mode.name,
            }
            mqtt_client.publish(topic, json.dumps(data))
            print(f"Real-Time Data Published: {data}")
        time.sleep(publish_interval)


def divide_polygon_into_chunks(polygon, chunk_size):
    """Divide the polygon into equal-sized chunks and assign IDs."""
    min_lon, min_lat, max_lon, max_lat = polygon.bounds
    chunk_polygons = []
    chunk_id = 0

    for lon in np.arange(min_lon, max_lon, chunk_size):
        for lat in np.arange(min_lat, max_lat, chunk_size):
            chunk = box(lon, lat, lon + chunk_size, lat + chunk_size)
            if polygon.intersects(chunk):
                intersection = polygon.intersection(chunk)
                if not intersection.is_empty:
                    chunk_id += 1
                    chunk_polygons.append((chunk_id, intersection))
    return chunk_polygons


def generate_scan_pattern(chunk, grid_size):
    """Generate a systematic scan pattern within a single chunk."""
    min_lon, min_lat, max_lon, max_lat = chunk.bounds
    latitudes = np.arange(min_lat, max_lat, grid_size)
    longitudes = np.arange(min_lon, max_lon, grid_size)

    scan_pattern = []
    reverse = False  # Alternating flag for row direction

    for lat in latitudes:
        row_points = []
        for lon in longitudes:
            point = Point(lon, lat)
            if chunk.contains(point):
                row_points.append((lat, lon))
        if reverse:
            row_points.reverse()
        scan_pattern.extend(row_points)
        reverse = not reverse  # Switch direction for next row

    return scan_pattern



def generate_soil_data(plot_id):
    """Generate simulated soil data."""
    data = {
        "plot_id": plot_id,
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
            "water_holding_capacity": round(random.uniform(20.0, 60.0), 2),  # Percentage
        },
    }
    return data


def publish_scan_data(scan_point, plot_id):
    """Publish scan point and plot ID to MQTT."""
    global mqtt_client
    topic = f"ground/{vehicle._handler.master.mav.srcSystem}/data"
    
    # Generate simulated soil data
    soil_data = generate_soil_data(plot_id)
    
    # Create the message with scan point and soil data
    message = {
        "plot_id": plot_id,
        "scan_point": {"latitude": scan_point[0], "longitude": scan_point[1]},
        "details": soil_data["details"],
    }
    
    # Publish to MQTT
    mqtt_client.publish(topic, json.dumps(message))
    print(f"Published Scan Data: {json.dumps(message, indent=4)}")


def visualize_chunks_and_scan(polygon_coords, chunk_polygons, scan_points):
    """Visualize the chunks, polygon, and scan points on a Folium map."""
    folium_map = folium.Map(location=map_location, zoom_start=17)

    # Add the main polygon
    folium.Polygon(locations=[(lat, lon) for lon, lat in polygon_coords], color='blue', fill=True, fill_opacity=0.3).add_to(folium_map)

    # Add each chunk
    for chunk_id, chunk in chunk_polygons:
        folium.Polygon(
            locations=[(point[1], point[0]) for point in chunk.exterior.coords],  # Use (lat, lon) directly
            color='green',
            weight=2,
            fill=True,
            fill_opacity=0.2,
        ).add_child(folium.Popup(f"Chunk ID: {chunk_id}")).add_to(folium_map)

    # Add scan points
    for lat, lon in scan_points:
        folium.CircleMarker(location=(lat, lon), radius=3, color='red', fill=True).add_to(folium_map)

    folium_map.save("chunks_and_scan.html")
    print("Map saved as 'chunks_and_scan.html'. Open this file to view the map.")


def perform_search():
    """Execute the search pattern."""
    global vehicle, polygon_coords

    # Define the polygon
    polygon = Polygon(polygon_coords)

    # Divide the polygon into chunks
    chunk_polygons = divide_polygon_into_chunks(polygon, chunk_size)
    if not chunk_polygons:
        print("No chunks generated. Check your polygon or chunk size.")
        return

    print(f"Generated {len(chunk_polygons)} chunks.")

    # Generate scan points for all chunks
    scan_points = []
    for chunk_id, chunk in chunk_polygons:
        scan_points.extend(generate_scan_pattern(chunk, grid_size))

    if not scan_points:
        print("No scan points generated. Check grid size or chunks.")
        return

    print(f"Generated {len(scan_points)} scan points.")

    # Visualize chunks and scan points
    visualize_chunks_and_scan(polygon_coords, chunk_polygons, scan_points)

    # Arm and begin scanning
    arm_and_set_mode()

    for scan_point in scan_points:
        # Create a geospatial plot_id
        plot_id = f"PLOT_{round(scan_point[0], 5)}_{round(scan_point[1], 5)}"
        goto_location(scan_point[0], scan_point[1])
        publish_scan_data(scan_point, plot_id)


# Main execution
if __name__ == "__main__":
    # Connect to vehicle
    connect_vehicle()

    # Connect to MQTT broker
    connect_mqtt()

    # Start real-time telemetry publishing
    threading.Thread(target=real_time_publisher, daemon=True).start()

    # Perform the search operation
    perform_search()
