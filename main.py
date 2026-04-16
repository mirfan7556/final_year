# main.py
from fastapi import FastAPI
from typing import List
import time

# --- 1. Import necessary components ---
# Import the data collection service and the shared data window
from firebase_service import start_firebase_listener, PROCESSED_DATA_WINDOW 
# Import the data models for type hinting and FastAPI response_model
from models import ProcessedFeatures, SeizurePrediction 
# Import the core AI analysis function
from ai_service import get_ai_prediction


# --- FastAPI Initialization ---
# Setup the main application instance
app = FastAPI(
    title="Real-Time Seizure Detection Backend",
    description="API for processing sensor data via Gemini and delivering structured predictions."
)

# --- 2. Startup Event: Initialize Firebase Listener ---
@app.on_event("startup")
def startup_event():
    """
    Function to be run when the FastAPI application starts up.
    This initializes the Firebase listener in a non-blocking thread, 
    starting the real-time data ingestion pipeline.
    """
    try:
        start_firebase_listener()
        print("Application startup complete. Firebase Listener is running in the background.")
    except Exception as e:
        print(f"FATAL ERROR during startup: {e}")
        # The app will still run, but the data will not be flowing.

# --- 3. Dashboard Endpoint (PULL Prediction) ---
@app.get("/api/v1/seizure-status", response_model=SeizurePrediction)
async def get_latest_seizure_status():
    """
    ENDPOINT: Fetches the AI's latest structured prediction for the parent dashboard.
    """
    
    # Read the latest processed features from the shared global window
    # PROCESSED_DATA_WINDOW holds the latest ProcessedFeatures object (as a list with max 1 item)
    current_data = PROCESSED_DATA_WINDOW
    
    if not current_data:
        # Return a safe, controlled response if no data has been processed yet
        return SeizurePrediction(
            seizure_detected=False, 
            severity_score=0, 
            recommendation="System initializing. Awaiting first sensor data window from RTDB."
        )

    # Call the Gemini AI service function to get the structured prediction
    prediction_data = get_ai_prediction(current_data)
    
    # Return the result. FastAPI/Pydantic ensures it matches the SeizurePrediction schema.
    return prediction_data

# --- Execution Command ---
# To run this file, use the command in your terminal from the project root:
# uvicorn main:app --reload