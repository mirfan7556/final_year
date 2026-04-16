# firebase_service.py
import firebase_admin
from firebase_admin import credentials, db
import threading
import time
from typing import List
import numpy as np 
from math import sqrt

# Assuming your models.py is updated as requested
from models import RawSensorReading, ProcessedFeatures 


# --- Configuration ---
# *** IMPORTANT: UPDATE THESE PATHS/URLs ***
SERVICE_ACCOUNT_KEY_PATH = 'sdk.json' 
FIREBASE_DB_URL = 'https://seizure-3837c-default-rtdb.asia-southeast1.firebasedatabase.app/' 
LISTENER_PATH = 'sensor_data/patient_001' # The parent path to listen to (where the 'data_stream' key is)

# --- Global Data Windows ---
# Store the raw readings temporarily for aggregation
RAW_READING_WINDOW: List[RawSensorReading] = [] 
# Store the latest processed feature set for the AI to read (max 1 item)
PROCESSED_DATA_WINDOW: List[ProcessedFeatures] = [] 
WINDOW_SIZE = 5 # Number of readings to aggregate (e.g., 5 seconds)

# --- Feature Engineering Function ---
def calculate_features(raw_readings: List[RawSensorReading]) -> ProcessedFeatures:
    """
    Performs feature engineering (RMS and statistics) on a batch of raw sensor data.
    """
    if not raw_readings:
        raise ValueError("Cannot calculate features on an empty list.")

    accel_rms_list = []
    pulse_list = []
    
    for reading in raw_readings:
        # RMS = sqrt(x^2 + y^2 + z^2)
        rms = sqrt(reading.accel_x**2 + reading.accel_y**2 + reading.accel_z**2)
        accel_rms_list.append(rms)
        pulse_list.append(reading.pulse_raw)

    # Use numpy for robust aggregation
    features = ProcessedFeatures(
        time_window_start=raw_readings[0].timestamp_ms,
        accel_rms_mean=np.mean(accel_rms_list),
        pulse_rate_avg=np.mean(pulse_list),
        pulse_rate_std=np.std(pulse_list) 
    )
    return features

# --- Firebase Listener Function ---
def data_listener(event):
    """
    Callback function that runs every time new data arrives from Firebase.
    It performs feature engineering and updates the global window.
    """
    global RAW_READING_WINDOW
    
    # Event data structure: {'data_stream': {'-Nx...': raw_dict, '-Ny...': raw_dict}}
    if not event.data or event.event_type != 'put':
        return

    # Iterate over the new children (unique push IDs) created by the simulator
    for key, raw_dict in event.data.items():
        if raw_dict and isinstance(raw_dict, dict):
            try:
                # 1. Convert raw dict to Pydantic model
                new_reading = RawSensorReading(**raw_dict)
                RAW_READING_WINDOW.append(new_reading)
                
                # Keep the raw window a reasonable size (e.g., 2x the processing window)
                if len(RAW_READING_WINDOW) > WINDOW_SIZE * 2: 
                     RAW_READING_WINDOW.pop(0) 

                # 2. Check for aggregation trigger
                if len(RAW_READING_WINDOW) >= WINDOW_SIZE:
                    # Only process the latest WINDOW_SIZE readings
                    window_to_process = RAW_READING_WINDOW[-WINDOW_SIZE:]
                    
                    # 3. Perform Feature Engineering
                    processed_features = calculate_features(window_to_process)
                    
                    # 4. Update the global window for the AI to read (keep only the latest)
                    # Clear the window and append the new processed result
                    PROCESSED_DATA_WINDOW.clear() 
                    PROCESSED_DATA_WINDOW.append(processed_features)

                    # Optional: Print to verify flow
                    # print(f"✨ Aggregated Features Ready. RMS Mean: {processed_features.accel_rms_mean:.2f}")

            except Exception as e:
                print(f"Error processing single reading: {e} in {raw_dict}")


# --- Firebase Initialization and Listener Start ---
def start_firebase_listener():
    """
    Initializes Firebase and starts the non-blocking listener thread.
    """
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred, {
                'databaseURL': FIREBASE_DB_URL
            })
            print("✅ Firebase initialized successfully.")
        except Exception as e:
            print(f"❌ Error initializing Firebase: {e}. Check service account path/URL.")
            return

    # Start listening
    ref = db.reference(LISTENER_PATH)
    ref.listen(data_listener) # Runs in a separate thread
    print(f"👂 Firebase Realtime Listener started on path: {LISTENER_PATH}")