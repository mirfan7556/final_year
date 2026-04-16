# simulator.py
import firebase_admin
from firebase_admin import credentials, db
import time
import random

# --- Configuration (MUST MATCH firebase_service.py) ---
SERVICE_ACCOUNT_KEY_PATH = 'sdk.json'
FIREBASE_DB_URL = 'https://seizure-3837c-default-rtdb.asia-southeast1.firebasedatabase.app/'
# Target path for the raw data stream (we will push new data to a specific 'data_stream' key)
RAW_DATA_PATH = 'sensor_data/patient_001/data_stream' 

def initialize_firebase():
    """Initializes the Firebase Admin SDK for the simulator."""
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
        print("✅ Simulator: Firebase initialized.")

def generate_sensor_data(is_seizure=False):
    """Generates random data, simulating normal or seizure activity."""
    timestamp = int(time.time() * 1000)
    
    if is_seizure:
        # Simulate high-intensity, rhythmic motion and elevated heart rate
        accel_base = random.uniform(2.0, 5.0)
        pulse = random.randint(110, 140)
    else:
        # Simulate normal activity or resting
        accel_base = random.uniform(0.1, 0.5)
        pulse = random.randint(65, 95)

    data = {
        "timestamp_ms": timestamp,
        # Add a small random jitter to make it look real
        "accel_x": accel_base + random.uniform(-0.1, 0.1),
        "accel_y": accel_base + random.uniform(-0.1, 0.1),
        "accel_z": accel_base + random.uniform(-0.1, -0.1),
        "pulse_raw": pulse
    }
    return data

def run_simulator():
    """Pushes data to RTDB in real-time intervals."""
    initialize_firebase()
    ref = db.reference(RAW_DATA_PATH)
    
    print("\n--- Starting Data Simulator ---")
    print("Sending normal data for 10 seconds, then a seizure event for 10 seconds.")
    
    # 1. Normal Data Phase
    for i in range(10):
        data = generate_sensor_data(is_seizure=False)
        # Push to the database using a unique ID (like the timestamp)
        ref.push(data) 
        print(f"[{i+1}/20] Pushed Normal Data: RMS avg ~0.3, Pulse: {data['pulse_raw']}")
        time.sleep(1) # Simulate 1 reading per second
        
    print("\n🚨🚨🚨 SIMULATING SEIZURE EVENT STARTING 🚨🚨🚨")

    # 2. Seizure Data Phase
    for i in range(10, 20):
        data = generate_sensor_data(is_seizure=True)
        ref.push(data)
        print(f"[{i+1}/20] Pushed SEIZURE Data: RMS avg ~3.5, Pulse: {data['pulse_raw']}")
        time.sleep(1) # Simulate 1 reading per second

    print("\n--- Simulator Finished. ---")


if __name__ == '__main__':
    # You will run this file in a separate terminal: `python simulator.py`
    run_simulator()