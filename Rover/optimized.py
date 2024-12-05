import random
import json
import time
import threading
import paho.mqtt.client as mqtt
from dronekit import connect, VehicleMode, LocationGlobalRelative
from shapely.geometry import Polygon, Point, box
from shapely.validation import explain_validity
import folium
import numpy as np
from math import sin, cos, sqrt, atan2, radians

# Global variables
vehicle = None
mqtt_client = None
broker_address = "100.109.46.43"  # MQTT broker address
mqtt_port = 1883
mqtt_keepalive = 60
grid_size = 0.0002  # Grid resolution for scan pattern
chunk_size = 0.001  # Chunk size for dividing polygon
publish_interval = 1  # Interval for real-time data publishing (in seconds)
map_location = (12.524, 76.895)  # Center of the map for visualization
polygon_coords = None  # To be received via MQTT
polygon_received_event = threading.Event()  # Event to signal polygon reception

# Mandya District Specific Soil Types
SOIL_TYPES = [
    "Red Sandy Loam",
    "Laterite",
    "Coastal Alluvium"
]

SOIL_COLORS = {
    "Red Sandy Loam": ["Reddish Brown", "Light Red", "Terra Cotta"],
    "Laterite": ["Rusty Red", "Brown Red", "Dark Red"],
    "Coastal Alluvium": ["Dark Brown", "Brown", "Light Brown"]
}

# Search state tracking
search_status = {
    "status": "unknown",
    "latlng": None,
    "waypoints": []
}
def validate_polygon(coords):
    """
    Validate and potentially fix polygon coordinates
    """
    try:
        # Ensure coordinates are unique and create a valid closed polygon
        unique_coords = []
        for coord in coords:
            if not unique_coords or coord != unique_coords[-1]:
                unique_coords.append(coord)
        
        # Ensure at least 3 unique coordinates for a valid polygon
        if len(unique_coords) < 3:
            print("Error: Polygon must have at least 3 unique coordinates")
            return None
        
        # Optionally, close the polygon if not already closed
        if unique_coords[0] != unique_coords[-1]:
            unique_coords.append(unique_coords[0])
        
        polygon = Polygon(unique_coords)
        
        # Check polygon validity
        if not polygon.is_valid:
            print("Invalid polygon detected!")
            print("Validity explanation:", explain_validity(polygon))
            
            # Attempt to buffer the polygon to fix minor topological issues
            polygon = polygon.buffer(0)
            
            if polygon.is_valid:
                print("Polygon fixed using buffer method")
                return polygon
            else:
                print("Could not automatically fix the polygon")
                return None
        
        return polygon
    
    except Exception as e:
        print(f"Error creating polygon: {e}")
        return None

def print_polygon_details(coords):
    """Print detailed information about polygon coordinates"""
    print("Total coordinates:", len(coords))
    print("First few coordinates:", coords[:5])
    print("Coordinate range:")
    lons = [lon for lon, _ in coords]
    lats = [lat for _, lat in coords]
    print("  Longitude range:", min(lons), "-", max(lons))
    print("  Latitude range:", min(lats), "-", max(lats))

def connect_vehicle(connection_string="127.0.0.1:14551"):
    """Connect to the vehicle."""
    global vehicle
    print("Connecting to vehicle...")
    vehicle = connect(connection_string, wait_ready=True)
    print("Vehicle connected.")

def arm_and_set_mode(mode="GUIDED"):
    """Arm the vehicle and set the specified mode."""
    global vehicle, search_status
    search_status["status"] = "started"
    
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
    global vehicle, search_status
    target_location = LocationGlobalRelative(lat, lon, alt)
    print(f"Navigating to: {lat}, {lon}")
    vehicle.simple_goto(target_location)

    # Update current location in search status
    search_status["latlng"] = [lat, lon]

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
    lat1, lon1 = radians(aLocation1.lat), radians(aLocation1.lon)
    lat2, lon2 = radians(aLocation2.lat), radians(aLocation2.lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    radius_earth = 6371000  # Radius of Earth in meters
    return radius_earth * c

def connect_mqtt():
    """Connect to the MQTT broker and set up callbacks."""
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(broker_address, mqtt_port, mqtt_keepalive)
    print(f"Connected to MQTT broker at {broker_address}:{mqtt_port}")

def on_connect(client, userdata, flags, rc):
    """Callback for when the client receives a CONNACK response from the server."""
    if rc == 0:
        print("MQTT connection established.")
        subscribe_to_plan_topic()
    else:
        print(f"Failed to connect to MQTT broker, return code {rc}")

def on_message(client, userdata, msg):
    """Callback for when a PUBLISH message is received from the server."""
    global polygon_coords, search_status
    try:
        # Decode and parse the incoming JSON payload
        payload = json.loads(msg.payload.decode())

        # Update the global polygon coordinates
        if isinstance(payload, list) and len(payload) > 2:  # Ensure the payload is a valid list
            # Convert coordinates to (lon, lat) format
            polygon_coords = [(point[1], point[0]) for point in payload]
            
            # Print polygon details for debugging
            print_polygon_details(polygon_coords)
            
            # Validate polygon
            polygon = validate_polygon(polygon_coords)
            
            if polygon is not None:
                polygon_received_event.set()  # Signal that polygon is received
            else:
                print("Invalid polygon received. Waiting for valid coordinates.")
        else:
            print("Invalid payload format. Expected a list of [lat, lon] pairs.")
    except Exception as e:
        print(f"Error processing incoming message: {e}")

def subscribe_to_plan_topic():
    """Subscribe to the polygon plan topic."""
    global mqtt_client
    try:
        rover_id = vehicle._handler.master.mav.srcSystem  # Dynamically get ROVER_ID
    except AttributeError:
        # Fallback if ROVER_ID is not available yet
        rover_id = "UNKNOWN"
    topic = f"ground/{rover_id}/plan"
    mqtt_client.subscribe(topic)
    print(f"Subscribed to topic: {topic}")

def real_time_publisher():
    """Publish real-time telemetry data in a separate thread."""
    global vehicle, mqtt_client, search_status
    try:
        rover_id = vehicle._handler.master.mav.srcSystem
    except AttributeError:
        rover_id = "UNKNOWN"
    topic = f"ground/{rover_id}/telemetry"
    while True:
        if vehicle:
            # Prepare telemetry packet with current search status
            data = {
                "status": search_status["status"],
                "latlng": search_status["latlng"],
                "waypoints": search_status["waypoints"]
            }
            mqtt_client.publish(topic, json.dumps(data))
            print(f"Real-Time Search Status Published: {data}")
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
                try:
                    intersection = polygon.intersection(chunk)
                    if not intersection.is_empty:
                        chunk_id += 1
                        chunk_polygons.append((chunk_id, intersection))
                except Exception as e:
                    print(f"Error during chunk intersection: {e}")
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
                row_points.append([lat, lon])
        if reverse:
            row_points.reverse()
        scan_pattern.extend(row_points)
        reverse = not reverse  # Switch direction for next row

    return scan_pattern

def generate_soil_data(plot_id):
    """Generate simulated soil data for Mandya District."""
    # Select soil type with weighted probability
    soil_type = random.choices(
        SOIL_TYPES, 
        weights=[0.6, 0.2, 0.2]  # Red Sandy Loam is most common
    )[0]

    # Adjust soil parameters based on soil type
    ph_ranges = {
        "Red Sandy Loam": (6.5, 7.2),
        "Laterite": (5.5, 6.8),
        "Coastal Alluvium": (7.0, 8.0)
    }

    # Nutrient level ranges based on Mandya district characteristics
    nutrients = {
        "Red Sandy Loam": {
            "nitrogen_range": (20, 80),
            "phosphorus_range": (20, 60),
            "potassium_range": (100, 200)
        },
        "Laterite": {
            "nitrogen_range": (10, 50),
            "phosphorus_range": (10, 40),
            "potassium_range": (50, 150)
        },
        "Coastal Alluvium": {
            "nitrogen_range": (40, 100),
            "phosphorus_range": (30, 70),
            "potassium_range": (150, 250)
        }
    }

    data = {
        "plot_id": plot_id,
        "details": {
            "lat": vehicle.location.global_frame.lat,
            "lon": vehicle.location.global_frame.lon,
            "soil_type": soil_type,
            "soil_pH": round(random.uniform(*ph_ranges[soil_type]), 2),
            "soil_colour": random.choice(SOIL_COLORS[soil_type]),
            "texture": {
                "Red Sandy Loam": "Sandy Loam",
                "Laterite": "Loamy Clay",
                "Coastal Alluvium": "Fine Loam"
            }[soil_type],
            
            # Adjusted ranges based on Mandya district description
            "organic_content": round(random.uniform(1.0, 3.5), 2),
            "moisture_content": round(random.uniform(15.0, 35.0), 2),
            "bulk_density": round(random.uniform(1.2, 1.5), 2),
            
            # Dynamic nutrient ranges
            "nitrogen_ppm": random.randint(*nutrients[soil_type]["nitrogen_range"]),
            "phosphorus_ppm": random.randint(*nutrients[soil_type]["phosphorus_range"]),
            "potassium_ppm": random.randint(*nutrients[soil_type]["potassium_range"]),
            
            "cation_exchange_capacity": round(random.uniform(10.0, 30.0), 2),
            "electrical_conductivity": round(random.uniform(0.2, 1.2), 2),
            "porosity": round(random.uniform(35.0, 50.0), 2),
            "water_holding_capacity": round(random.uniform(25.0, 45.0), 2),
            "irrigation_suitability": "Cauvery River Belt"
        },
    }
    return data

def publish_scan_data(scan_point, plot_id):
    """Publish scan point and plot ID to MQTT."""
    global mqtt_client
    try:
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
    except Exception as e:
        print(f"Error publishing scan data: {e}")

def visualize_chunks_and_scan(polygon_coords, chunk_polygons, scan_points):
    """Visualize the chunks, polygon, and scan points on a Folium map."""
    folium_map = folium.Map(location=map_location, zoom_start=17)

    # Add the main polygon
    folium.Polygon(locations=[(lat, lon) for lon, lat in polygon_coords], color='blue', fill=True, fill_opacity=0.3).add_to(folium_map)

    # Add each chunk
    for chunk_id, chunk in chunk_polygons:
        folium.Polygon(
            locations=[(point[1], point[0]) for point in chunk.exterior.coords],
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
    global vehicle, polygon_coords, search_status

    # Wait for polygon coordinates
    print("Waiting for polygon coordinates to be received via MQTT...")
    polygon_received_event.wait()
    print("Polygon coordinates received. Starting search...")

    # Define the polygon with validation
    try:
        polygon = validate_polygon(polygon_coords)
        if polygon is None:
            print("Invalid polygon. Cannot proceed with search.")
            search_status["status"] = "error"
            return

    except Exception as e:
        print(f"Error creating polygon: {e}")
        search_status["status"] = "error"
        return

    # Divide the polygon into chunks
    chunk_polygons = divide_polygon_into_chunks(polygon, chunk_size)
    if not chunk_polygons:
        print("No chunks generated. Check your polygon or chunk size.")
        search_status["status"] = "error"
        return

    print(f"Generated {len(chunk_polygons)} chunks.")

    # Generate scan points for all chunks
    scan_points = []
    for chunk_id, chunk in chunk_polygons:
        scan_points.extend(generate_scan_pattern(chunk, grid_size))

    if not scan_points:
        print("No scan points generated. Check grid size or chunks.")
        search_status["status"] = "error"
        return

    print(f"Generated {len(scan_points)} scan points.")

    # Update search status with waypoints
    search_status["waypoints"] = scan_points

    # Visualize chunks and scan points
    visualize_chunks_and_scan(polygon_coords, chunk_polygons, scan_points)

    # Arm and begin scanning
    arm_and_set_mode()

    for scan_point in scan_points:
        try:
            # Create a geospatial plot_id
            plot_id = f"PLOT_{round(scan_point[0],5)}_{round(scan_point[1], 5)}"
            print(f"Moving to scan point: {scan_point} with plot_id: {plot_id}")
            goto_location(scan_point[0], scan_point[1])
            publish_scan_data(scan_point, plot_id)
        except Exception as e:
            print(f"Error during scanning at point {scan_point}: {e}")

    # Mark search as completed
    search_status["status"] = "completed"

# Main execution
if __name__ == "__main__":
    try:
        # Connect to vehicle
        connect_vehicle()

        # Connect to MQTT broker
        connect_mqtt()

        # Start real-time telemetry publishing in a separate thread
        telemetry_thread = threading.Thread(target=real_time_publisher, daemon=True)
        telemetry_thread.start()

        # Start the MQTT loop in a separate thread
        mqtt_loop_thread = threading.Thread(target=mqtt_client.loop_forever, daemon=True)
        mqtt_loop_thread.start()

        # Perform the search operation
        perform_search()

    except KeyboardInterrupt:
        print("Interrupted by user.")
        search_status["status"] = "error"

    finally:
        if vehicle:
            print("Returning control to the user...")
            vehicle.mode = VehicleMode("HOLD")
            vehicle.close()
        if mqtt_client:
            mqtt_client.disconnect()
            print("MQTT connection closed.")