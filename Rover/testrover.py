from dronekit import connect, VehicleMode, LocationGlobalRelative
from shapely.geometry import Polygon, Point
import folium
import numpy as np
import time

# Global variables
vehicle = None
scan_pattern = []
polygon_coords = [(12.523, 76.894), (12.523, 76.896), (12.525, 76.896), (12.525, 76.894)]  # Define your polygon here
grid_size = 0.0002  # Adjust grid resolution
map_location = (12.524, 76.895)  # Center of the map for visualization


def connect_vehicle(connection_string="127.0.0.1:14552"):
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


def goto_location(lat, lon, alt=0):
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
        time.sleep(2)


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


def generate_scan_pattern(polygon, grid_size):
    """Generate a scanning grid pattern (zigzag or serpentine) within the polygon."""
    min_lon, min_lat, max_lon, max_lat = polygon.bounds
    latitudes = np.arange(min_lat, max_lat, grid_size)
    longitudes = np.arange(min_lon, max_lon, grid_size)

    grid_points = []
    for lat in latitudes:
        for lon in longitudes:
            point = Point(lon, lat)
            if polygon.contains(point):
                grid_points.append((lat, lon))

    # Create a zigzag scan pattern
    scan_pattern = []
    reverse = False
    for i in range(len(latitudes)):
        row_points = [pt for pt in grid_points if pt[0] == latitudes[i]]
        if reverse:
            row_points.reverse()
        scan_pattern.extend(row_points)
        reverse = not reverse

    return scan_pattern


def visualize_scan_pattern(polygon_coords, scan_pattern):
    """Visualize the polygon and grid on a Folium map."""
    folium_map = folium.Map(location=map_location, zoom_start=17)

    # Add the polygon to the map
    folium.Polygon(locations=polygon_coords, color='blue', fill=True, fill_opacity=0.3).add_to(folium_map)

    # Add the scan pattern points to the map
    for point in scan_pattern:
        folium.CircleMarker(location=point, radius=3, color='red', fill=True).add_to(folium_map)

    # Save the map to an HTML file
    folium_map.save("scan_pattern.html")
    print("Map saved as 'scan_pattern.html'. Open this file to view the map.")


def perform_search():
    """Main function to perform the search within the polygon."""
    global vehicle, scan_pattern, polygon_coords

    # Define the polygon using shapely
    polygon = Polygon([(lon, lat) for lat, lon in polygon_coords])  # Switch lat/lon for shapely compatibility

    # Generate scan pattern
    scan_pattern = generate_scan_pattern(polygon, grid_size)
    print(f"Scan pattern generated with {len(scan_pattern)} points.")

    # Visualize the pattern
    visualize_scan_pattern(polygon_coords, scan_pattern)

    # Start the search
    arm_and_set_mode()
    for lat, lon in scan_pattern:
        goto_location(lat, lon)


if __name__ == "__main__":
    try:
        # Connect to the vehicle
        connect_vehicle()

        # Perform the search
        perform_search()

    finally:
        # Safely close the connection
        if vehicle:
            print("Returning control to the user...")
            vehicle.mode = VehicleMode("HOLD")
            vehicle.close()
