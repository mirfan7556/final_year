# ai_service.py
import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from typing import List # Required for type hinting

# Import models
from models import ProcessedFeatures, SeizurePrediction 

# --- Configuration and Initialization ---
load_dotenv() 

# 1. API Key Handling
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    # Raise error if key isn't found, preventing runtime failure
    raise ValueError("GEMINI_API_KEY not found in environment variables. Check your .env file!")

# Initialize the Gemini Client
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    raise RuntimeError(f"Failed to initialize Gemini Client: {e}")

GEMINI_MODEL = 'gemini-2.5-flash' 


def get_ai_prediction(processed_data_list: List[ProcessedFeatures]) -> dict:
    """
    Analyzes processed sensor data using the Gemini API with structured output.
    
    Args:
        processed_data_list: A list containing the latest ProcessedFeatures object(s).
        
    Returns:
        A dictionary matching the SeizurePrediction schema.
    """
    
    # 1. Prepare data and instruction for the prompt
    # Since the list holds ProcessedFeatures objects, convert them to a JSON string
    data_for_prompt = [d.model_dump() for d in processed_data_list]
    data_string = json.dumps(data_for_prompt, indent=2)

    prompt = f"""
    You are an AI Seizure Detection System. Your task is to analyze processed sensor features from a patient's wearable device over the last few seconds.
    
    The data structure provides:
    - **accel_rms_mean:** The average movement intensity (Root Mean Square) over the window. Normal range is typically 0.1 to 1.5.
    - **pulse_rate_avg:** The average heart rate (BPM).
    - **pulse_rate_std:** The standard deviation of the heart rate (variability). A HIGH STD indicates erratic or rapid changes in heart rate, which is a strong seizure indicator.
    
    **CRITICAL ANALYSIS RULES:**
    
    1.  **SEIZURE LIKELY:** If `accel_rms_mean` is consistently **above 2.5** AND `pulse_rate_std` is **above 5.0**, a seizure is highly probable.
    2.  **MILD WARNING:** If `accel_rms_mean` is between **1.5 and 2.5** AND `pulse_rate_avg` is **above 100**, assign a medium severity.
    3.  **NORMAL/REST:** If `accel_rms_mean` is below 1.5 and `pulse_rate_avg` is below 95, no seizure is detected.
    
    **SEVERITY SCORING (1-5):**
    - **Severity 5 (Emergency):** High RMS mean (>3.5) AND High Pulse STD (>7.0). Recommendation: "Call emergency services now and ensure the area is clear."
    - **Severity 4 (Serious):** High RMS mean (>2.5) AND High Pulse STD (>5.0). Recommendation: "Clear area, check breathing, time the event. Seek immediate help."
    - **Severity 3 (Monitoring):** Medium RMS mean (1.5-2.5) AND elevated Pulse AVG (>100). Recommendation: "Monitor patient closely, check for responsiveness, and prepare medication."
    - **Severity 1-2 (Normal):** All values within normal ranges. Recommendation: "All vitals stable."
    
    **Instructions:**
    1. Apply the analysis rules above to the provided data.
    2. Output your prediction using ONLY the provided JSON schema.
    
    **Processed Features Data:**
    {data_string}
    """
    
    # 2. Configure the structured JSON output using the Pydantic schema
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=SeizurePrediction.to_gemini_schema(SeizurePrediction),
    )
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
        
        # 3. Parse the guaranteed valid JSON string
        return json.loads(response.text)
        
    except Exception as e:
        print(f"❌ Gemini API Error during prediction: {e}")
        # Return a safe, controlled error response on API failure
        return SeizurePrediction(
            seizure_detected=False, 
            severity_score=0, 
            recommendation="System error. Check Gemini API connection."
        ).model_dump()