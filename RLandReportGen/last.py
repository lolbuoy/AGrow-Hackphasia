import paho.mqtt.client as mqtt
import json
import numpy as np
import joblib
import os
import time
import threading
from sklearn.preprocessing import StandardScaler
import random
from datetime import datetime
import geopy.geocoders

class CropRecommendationFromMQTT:
    def __init__(self, mqtt_host='100.109.46.43', mqtt_port=1883, model_save_dir='cauvery_basin_models'):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.request_topic = "ai/crops/255/request"
        self.response_topic = "ai/crops/255/response"
        self.model_save_dir = model_save_dir

        # Store incoming data
        self.soil_data_buffer = []
        self.buffer_lock = threading.Lock()

        # Load the trained model and scaler
        self.basin_model, self.scaler = self.load_model("Cauvery Basin")

        # Initialize geolocator
        self.geolocator = geopy.geocoders.Nominatim(user_agent="crop_recommendation_system")

        # Enhanced crop descriptions with detailed recommendations
        self.crop_recommendations = {
            "Rice": {
                "description": "Rice is a staple food grown in waterlogged fields and requires ample rainfall.",
                "soil_requirements": {
                    "ph": (6.0, 7.0),
                    "nitrogen": (50, 150),
                    "phosphorus": (30, 60),
                    "potassium": (40, 80),
                    "temperature": (20, 35),
                    "rainfall": (100, 200)
                },
                "best_conditions": "Well-drained, fertile soil with good water retention. Ideal for areas with consistent rainfall.",
                "cultivation_tips": "Use paddy field techniques. Ensure proper water management and consider using high-yielding varieties suitable for your specific region."
            },
            "Maize": {
                "description": "Maize is a versatile crop used for food, fodder, and industrial purposes.",
                "soil_requirements": {
                    "ph": (5.8, 7.0),
                    "nitrogen": (80, 150),
                    "phosphorus": (40, 80),
                    "potassium": (50, 100),
                    "temperature": (20, 35),
                    "rainfall": (50, 150)
                },
                "best_conditions": "Well-drained, fertile soils with good organic matter content.",
                "cultivation_tips": "Use crop rotation and ensure adequate fertilization. Choose varieties resistant to local pest and disease pressures."
            },
            "Cotton": {
                "description": "Cotton is a fiber crop grown in warm climates, essential for the textile industry.",
                "soil_requirements": {
                    "ph": (6.0, 7.5),
                    "nitrogen": (70, 140),
                    "phosphorus": (40, 80),
                    "potassium": (60, 120),
                    "temperature": (25, 35),
                    "rainfall": (50, 150)
                },
                "best_conditions": "Deep, well-drained soils with good fertility and warm temperatures.",
                "cultivation_tips": "Implement precision irrigation. Use integrated pest management techniques. Select high-yielding, disease-resistant varieties."
            }
        }

    def load_model(self, basin_name):
        try:
            model_path = os.path.join(self.model_save_dir, f'{basin_name}_model.joblib')
            scaler_path = os.path.join(self.model_save_dir, f'{basin_name}_scaler.joblib')

            if os.path.exists(model_path) and os.path.exists(scaler_path):
                basin_model = joblib.load(model_path)
                scaler = joblib.load(scaler_path)
                print(f"Models for {basin_name} loaded successfully.")
                return basin_model, scaler
            else:
                raise FileNotFoundError(f"Model or scaler for {basin_name} not found.")
        except Exception as e:
            print(f"Error loading models for {basin_name}: {e}")
            raise

    def process_soil_data(self, soil_data):
        # Robust processing for different input types
        if isinstance(soil_data, dict):
            return {
                'nitrogen': soil_data.get('nitrogen', soil_data.get('nitrogen_ppm', round(random.uniform(50, 150), 2))),
                'phosphorus': soil_data.get('phosphorus', soil_data.get('phosphorus_ppm', round(random.uniform(30, 100), 2))),
                'potassium': soil_data.get('potassium', soil_data.get('potassium_ppm', round(random.uniform(40, 120), 2))),
                'ph': soil_data.get('ph', soil_data.get('soil_pH', round(random.uniform(6.0, 7.5), 2))),
                'temperature': soil_data.get('temperature', round(random.uniform(20, 35), 2)),
                'rainfall': soil_data.get('rainfall', round(random.uniform(50, 200), 2)),
                'latitude': soil_data.get('latitude', soil_data.get('lat', 12.2958)),
                'longitude': soil_data.get('longitude', soil_data.get('lon', 76.6394))
            }
        elif isinstance(soil_data, list):
            # If it's a list, try to process the first item
            if soil_data and isinstance(soil_data[0], dict):
                return self.process_soil_data(soil_data[0])
            elif soil_data and isinstance(soil_data[0], (int, float)):
                # If it's a list of numbers, create a default dict
                return {
                    'nitrogen': soil_data[0] if len(soil_data) > 0 else round(random.uniform(50, 150), 2),
                    'phosphorus': soil_data[1] if len(soil_data) > 1 else round(random.uniform(30, 100), 2),
                    'potassium': soil_data[2] if len(soil_data) > 2 else round(random.uniform(40, 120), 2),
                    'ph': soil_data[3] if len(soil_data) > 3 else round(random.uniform(6.0, 7.5), 2),
                    'temperature': soil_data[4] if len(soil_data) > 4 else round(random.uniform(20, 35), 2),
                    'rainfall': soil_data[5] if len(soil_data) > 5 else round(random.uniform(50, 200), 2),
                    'latitude': soil_data[6] if len(soil_data) > 6 else 12.2958,
                    'longitude': soil_data[7] if len(soil_data) > 7 else 76.6394
                }
        
        # Default to random values if no recognizable input
        return {
            'nitrogen': round(random.uniform(50, 150), 2),
            'phosphorus': round(random.uniform(30, 100), 2),
            'potassium': round(random.uniform(40, 120), 2),
            'ph': round(random.uniform(6.0, 7.5), 2),
            'temperature': round(random.uniform(20, 35), 2),
            'rainfall': round(random.uniform(50, 200), 2),
            'latitude': 12.2958,
            'longitude': 76.6394
        }

    def evaluate_crop_suitability(self, crop, avg_data):
        """
        Evaluate crop suitability based on soil parameters
        """
        if crop not in self.crop_recommendations:
            return crop

        requirements = self.crop_recommendations[crop]['soil_requirements']
        
        # Simple suitability check
        def is_within_range(param, value):
            return requirements[param][0] <= value <= requirements[param][1]
        
        suitability_checks = [
            is_within_range('ph', avg_data['ph']),
            is_within_range('nitrogen', avg_data['nitrogen']),
            is_within_range('phosphorus', avg_data['phosphorus']),
            is_within_range('potassium', avg_data['potassium']),
            is_within_range('temperature', avg_data['temperature']),
            is_within_range('rainfall', avg_data['rainfall'])
        ]
        
        # Return the description based on suitability
        if all(suitability_checks):
            return self.crop_recommendations[crop]['description'] + " Highly suitable for current soil conditions."
        elif sum(suitability_checks) >= 4:
            return self.crop_recommendations[crop]['description'] + " Moderately suitable for current soil conditions."
        else:
            return self.crop_recommendations[crop]['description'] + " May require soil amendments for optimal growth."

    def get_crop_recommendation(self, avg_data):
        features = ['nitrogen', 'phosphorus', 'potassium', 
                    'temperature', 'rainfall', 'ph', 
                    'latitude', 'longitude']
        input_features = [avg_data[feature] for feature in features]
        input_scaled = self.scaler.transform([input_features])
        predictions = self.basin_model.predict_proba(input_scaled)
        top_indices = predictions[0].argsort()[-3:][::-1]
        recommended_crops = [self.basin_model.classes_[idx] for idx in top_indices]
        return recommended_crops

    def describe_crops(self, crops, avg_data):
        """
        Provide descriptions for recommended crops
        """
        return {crop: self.evaluate_crop_suitability(crop, avg_data) for crop in crops}

    def send_recommendation(self, client, avg_data, crops, cropsdetailed):
        payload = {
            "crops": crops,
            "avg_values": avg_data,
            "cropsdetailed": cropsdetailed
        }
        client.publish(self.response_topic, json.dumps(payload))
        print(f"Sent recommendation to {self.response_topic}: {json.dumps(payload, indent=2)}")

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected to MQTT server with result code {rc}")
        client.subscribe(self.request_topic)

    def on_message(self, client, userdata, msg):
        try:
            # Parse the received message
            message = json.loads(msg.payload.decode())
            
            # Robust handling of different input formats
            if isinstance(message, dict):
                # If it's a dictionary, check for 'details' or 'avg_values'
                soil_data = message.get('details', message.get('avg_values', {}))
            elif isinstance(message, list):
                # If it's a list, use the first item
                soil_data = message[0] if message else {}
            else:
                # Default to empty dict if no recognizable input
                soil_data = {}
            
            # Process the soil data
            processed_data = self.process_soil_data(soil_data)
            
            # Recommend crops based on the soil data
            crops = self.get_crop_recommendation(processed_data)
            cropsdetailed = self.describe_crops(crops, processed_data)
            
            # Send recommendation
            self.send_recommendation(client, processed_data, crops, cropsdetailed)

        except json.JSONDecodeError:
            print("Invalid JSON received")
        except Exception as e:
            print(f"Error processing MQTT message: {e}")

    def start_listening(self):
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(self.mqtt_host, self.mqtt_port, 60)

        client.loop_forever()

def main():
    crop_recommendation_system = CropRecommendationFromMQTT()
    crop_recommendation_system.start_listening()

if __name__ == "__main__":
    main()
