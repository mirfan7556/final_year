#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <U8g2lib.h>
#include <WiFi.h>
#include <math.h>
#include "FirebaseESP32.h" // Required Firebase Library

// --- PIN DEFINITIONS ---
#define PULSE_PIN 34     
#define BUZZER_PIN 5     

// --- WIFI CONFIGURATION ---
const char* WIFI_SSID = "TechAZsure";      
const char* WIFI_PASSWORD = "TeChAzSuRe786"; 

// --- FIREBASE RTDB CONFIGURATION (CRITICAL) ---
#define RTDB_URL "https://seizure-3837c-default-rtdb.asia-southeast1.firebasedatabase.app/" 
#define RTDB_SECRET "j2N8I2LIiqQLO6JvRLOI7gG4CVSETtKzNMiz2Pso" 
#define USER_ID "TEST_PATIENT_001" // Unique identifier for the live node

const float Accel_Bias_X = 0; 
const float Accel_Bias_Y = 0;
const float Accel_Bias_Z = 0;
const float Gyro_Bias_X = 0;
const float Gyro_Bias_Y = -0.0370;
const float Gyro_Bias_Z = -0.0377;
const int PULSE_BASELINE = 2878;

// --- THRESHOLDS ---
const float MOTION_THRESHOLD = 15.0;     
const int PULSE_DEVIATION = 300;       

// --- MOCK LOCATION ---
const float PATIENT_LAT = 13.0000;
const float PATIENT_LON = 80.2500;

// --- OBJECTS ---
Adafruit_MPU6050 mpu;
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// --- OLED DISPLAY SETUP ---
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE); 

// --- GLOBAL STATE ---
bool seizureDetected = false;
unsigned long lastLogTime = 0;
const long LOG_INTERVAL_MS = 5000; // --- RAPID 5 SECOND UPDATE ---

// Variables to temporarily store current sensor readings for display
float currentAccel = 0.0;
int currentPulse = 0;

// --- FUNCTION PROTOTYPES ---
void setupOLED();
void serialLog(const String& msg);
void simpleBeep(int duration_ms);
void connectWiFi();
void initFirebaseRTDB();
void pushLiveStatus(float total_accel, int pulse_raw, const char* posture, bool is_critical);
void readAndProcessSensors();
void checkSeizure(float total_accel, int pulse_raw);
void updateTime();
void displayNormalStatus();


void setup() {
    Serial.begin(115200);
    randomSeed(analogRead(0)); 
    pinMode(BUZZER_PIN, OUTPUT);
    simpleBeep(100); 

    setupOLED();
    
    serialLog(String("Initializing MPU6050..."));
    if (!mpu.begin()) {
        serialLog(String("ERROR: MPU6050 not found!"));
        while(1) delay(1000);
    }
    
    connectWiFi();
    initFirebaseRTDB();
    updateTime(); // Sync time once
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        connectWiFi();
    }
    
    if(Firebase.ready()){
        readAndProcessSensors();
    } else {
        delay(500);
    }

    if (seizureDetected) {
        // --- CRITICAL ALERT DISPLAY ---
        u8g2.clearBuffer();
        u8g2.setFont(u8g2_font_unifont_t_symbols);
        u8g2.drawStr(0, 30, "!!! SEIZURE ALERT !!!");
        u8g2.drawStr(0, 50, "LIVE UPLOADING...");
        u8g2.sendBuffer();
        simpleBeep(50);
        delay(500); 
    } else {
        // --- NORMAL STATUS DISPLAY ---
        displayNormalStatus();
        delay(100); // Small delay to prevent display flicker
    }
}

// =========================================================================
//                  CORE LOGIC FUNCTIONS
// =========================================================================

void readAndProcessSensors() {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    // --- 1. Apply Calibration and Noise ---
    float noise_offset = ((float)random(0, 100) / 100.0) - 0.5;

    float accel_x = a.acceleration.x - Accel_Bias_X + noise_offset;
    float accel_y = a.acceleration.y - Accel_Bias_Y + noise_offset;
    float accel_z = a.acceleration.z - Accel_Bias_Z + noise_offset;

    float total_accel_mag = sqrt(pow(accel_x, 2) + pow(accel_y, 2) + pow(accel_z, 2));
    int pulse_raw = analogRead(PULSE_PIN) + random(-5, 5); 

    // Store latest values globally for OLED display
    currentAccel = total_accel_mag;
    currentPulse = pulse_raw;

    // Run the core detection logic
    checkSeizure(total_accel_mag, pulse_raw);
    
    // --- 5s Data Logging (Live Status Overwrite) ---
    if (millis() - lastLogTime >= LOG_INTERVAL_MS) {
        
        const char* seizure_posture = "Normal/Resting";
        bool is_critical = false;
        
        if (seizureDetected) {
            seizure_posture = "Tonic-Clonic (Convulsions)";
            is_critical = true;
        }

        // Push data to the LIVE STATUS REGISTER
        pushLiveStatus(total_accel_mag, pulse_raw, seizure_posture, is_critical);
        
        lastLogTime = millis();
        // Reset alert status after a log entry is created (doctor can see the history)
        // seizureDetected is typically kept true during the seizure for continuous alert until conditions stabilize.
        // For rapid testing, we keep it true until the next seizure check cycle or a manual reset.
    }
}

void checkSeizure(float total_accel, int pulse_raw) {
    bool motion_seizure = (total_accel > MOTION_THRESHOLD + random(-2, 1)); 
    bool pulse_anomaly = (abs(pulse_raw - PULSE_BASELINE) > PULSE_DEVIATION);

    if (motion_seizure && pulse_anomaly && !seizureDetected) {
        serialLog(String("!!! CRITICAL ALERT: SEIZURE DETECTED !!!"));
        seizureDetected = true;
        simpleBeep(2000); 
    } else if (!motion_seizure && seizureDetected && (abs(pulse_raw - PULSE_BASELINE) < PULSE_DEVIATION / 2)) {
         // Auto-reset alert if conditions stabilize significantly (out of seizure phase)
         seizureDetected = false;
         serialLog(String("ALERT RESET: Patient appears stable."));
    }
}


// =========================================================================
//                  OLED DISPLAY FUNCTIONS
// =========================================================================

void displayNormalStatus() {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB08_tr);
    
    u8g2.drawStr(0, 10, "STATUS: NORMAL");
    
    // Display Sensor Data
    String accelStr = "Accel: " + String(currentAccel, 2) + " m/s";
    String pulseStr = "Pulse: " + String(currentPulse);
    String baseStr = "Base: " + String(PULSE_BASELINE);

    u8g2.drawStr(0, 30, accelStr.c_str());
    u8g2.drawStr(0, 45, pulseStr.c_str());
    u8g2.drawStr(0, 60, baseStr.c_str());
    
    u8g2.sendBuffer();
}

void setupOLED() {
    u8g2.begin();
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB08_tr);
    u8g2.drawStr(0, 10, "AI Fits-Care System");
    u8g2.sendBuffer();
}


// =========================================================================
//                  WIFI & FIREBASE LIVE PUSH FUNCTIONS
// =========================================================================

void initFirebaseRTDB() {
    config.database_url = RTDB_URL;
    config.signer.tokens.legacy_token = RTDB_SECRET;
    Firebase.begin(&config, &auth);
    Firebase.reconnectWiFi(true);
    serialLog(String("Firebase Initialized. Ready: ") + (Firebase.ready() ? "YES" : "NO"));
}

/**
 * Pushes LIVE sensor data to a single path: /live_status/{USER_ID}
 * This overwrites the previous data every 5 seconds.
 */
void pushLiveStatus(float total_accel, int pulse_raw, const char* posture, bool is_critical) {
    if (!Firebase.ready()) return;

    // Path: /live_status/TEST_PATIENT_001
    String path = "/live_status/" + String(USER_ID);
    
    // Get current time string for log
    time_t now = time(NULL);
    struct tm *tm = localtime(&now);
    char timeStr[64];
    strftime(timeStr, 64, "%Y-%m-%d %H:%M:%S", tm);
    
    // Build JSON
    FirebaseJson json;
    
    json.set("UserID", USER_ID);
    json.set("Last_Updated", timeStr);
    json.set("Timestamp_Epoch_ms", time(NULL) * 1000);
    
    // Calibrated Sensor Data
    json.set("Calibrated_Data/Posture", posture);
    json.set("Calibrated_Data/Total_Accel_Mag", total_accel);
    json.set("Calibrated_Data/Pulse_Raw_Analog", pulse_raw);
    
    // Location & Status (Criticality)
    json.set("Current_Status/Is_Critical", is_critical);
    json.set("Current_Location/latitude", PATIENT_LAT);
    json.set("Current_Location/longitude", PATIENT_LON);
    
    // Use setJSON to overwrite the old node instantly
    if (Firebase.setJSON(fbdo, path, json)) {
        serialLog(String("LIVE STATUS updated successfully: ") + path);
    } else {
        serialLog(String("LIVE STATUS ERROR: ") + fbdo.errorReason());
    }
}


// =========================================================================
//                  UTILITY FUNCTIONS
// =========================================================================

void connectWiFi() {
    serialLog(String("Connecting to WiFi: ") + String(WIFI_SSID));
    u8g2.drawStr(0, 50, "Connecting WiFi...");
    u8g2.sendBuffer();

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int timeout = 0;
    
    while (WiFi.status() != WL_CONNECTED && timeout < 20) {
        delay(500);
        serialLog(String("."));
        timeout++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        serialLog(String("\nWiFi Connected! IP: ") + WiFi.localIP().toString());
        u8g2.drawStr(0, 50, "WiFi CONNECTED!");
        u8g2.sendBuffer();
    } else {
        serialLog(String("\nWiFi Connection Failed! Retrying..."));
        u8g2.drawStr(0, 50, "WiFi FAILED!");
        u8g2.sendBuffer();
    }
}

void simpleBeep(int duration_ms) {
    tone(BUZZER_PIN, 1000, duration_ms);
    delay(duration_ms);
    noTone(BUZZER_PIN);
}

void serialLog(const String& msg) {
    Serial.println(msg);
}

void updateTime() {
    // Configures the time once at startup
    configTime(3600 * 5.5, 0, "pool.ntp.org"); 
}