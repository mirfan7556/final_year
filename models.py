# models.py
from pydantic import BaseModel, Field
from typing import List, Optional

# --- 1. Model for a Single RAW Sensor Reading (Input from ESP32/Simulator) ---
class RawSensorReading(BaseModel):
    """Schema for a single raw data point pushed to RTDB."""
    timestamp_ms: int = Field(description="Millisecond timestamp of the reading.")
    accel_x: float = Field(description="Raw X-axis acceleration.")
    accel_y: float = Field(description="Raw Y-axis acceleration.")
    accel_z: float = Field(description="Raw Z-axis acceleration.")
    pulse_raw: int = Field(description="The patient's raw pulse reading.")


# --- 2. Model for the PROCESSED Features (Used by Gemini) ---
class ProcessedFeatures(BaseModel):
    """Schema for the aggregated and processed features sent to Gemini."""
    time_window_start: int
    accel_rms_mean: float = Field(description="Mean Root Mean Square acceleration over the window.")
    pulse_rate_avg: float = Field(description="Average pulse rate over the window.")
    pulse_rate_std: float = Field(description="Standard Deviation of pulse rate over the window.")
    # Add more features here later (e.g., motion variability, max jerk)


# --- 3. Model for the Structured Gemini Output (Output to Dashboard) ---
class SeizurePrediction(BaseModel):
    """Schema for the final, structured prediction from the Gemini AI."""
    seizure_detected: bool = Field(description="True if the AI predicts a seizure is likely, False otherwise.")
    severity_score: int = Field(description="An integer score from 1 (mild) to 5 (severe). Should be 0 if no seizure is detected.")
    recommendation: str = Field(description="A concise, immediate action recommendation for the caregiver.")

    def to_gemini_schema(self):
        return self.model_json_schema()