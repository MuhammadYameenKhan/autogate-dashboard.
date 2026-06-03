import cv2
import requests
import ssl
import time
from inference_sdk import InferenceHTTPClient

# SSL certificate bypass
ssl._create_default_https_context = ssl._create_unverified_context

# --- CONFIGURATION ---
ROBOFLOW_API_KEY = "L0p9rnM3YsdK54JbuWRY"
PROJECT_ID = "pakistan-license-plate-detection" 
VERSION = "1"
FLASK_API_URL = "http://localhost:5000/api/parking/event"

CLIENT = InferenceHTTPClient(
    # api_url="http://localhost:9001",
    api_url="https://detect.roboflow.com",
    api_key=ROBOFLOW_API_KEY
)

# AI ki memory
last_saved_plate = ""

def process_frame(frame):
    global last_saved_plate
    
    cv2.imwrite("temp_frame.jpg", frame)
    
    try:
        result = CLIENT.infer("temp_frame.jpg", model_id=f"{PROJECT_ID}/{VERSION}")
    except Exception as e:
        return

    predictions = result.get('predictions', [])
    if not predictions:
        return 

    char_predictions = [p for p in predictions if p['class'].lower() != 'plate']
    if not char_predictions:
        return 

    # 2-Line Sorting Logic
    avg_y = sum(p['y'] for p in char_predictions) / len(char_predictions)
    top_line = [p for p in char_predictions if p['y'] < avg_y]
    bottom_line = [p for p in char_predictions if p['y'] >= avg_y]
    
    top_line.sort(key=lambda item: item['x'])
    bottom_line.sort(key=lambda item: item['x'])
    
    sorted_chars = top_line + bottom_line
    plate_text = "".join([p['class'] for p in sorted_chars]).upper()
    plate_text = ''.join(e for e in plate_text if e.isalnum())
    
    avg_conf = round(sum([p['confidence'] for p in char_predictions]) / len(char_predictions), 2)
    
    # --- TERMINAL DEBUGGING (Aapka Idea) ---
    if plate_text and plate_text != last_saved_plate:
        print(f"👀 [Live Scan] AI ne dekha: '{plate_text}' (Conf: {avg_conf})")
    
    # --- FILTERS ---
    if len(plate_text) < 4:
        if plate_text and plate_text != last_saved_plate:
            print("   -> ❌ Rejected: Plate 4 huroof se choti hai (Kachra hai)")
        return
        
    if avg_conf < 0.60:
        if plate_text and plate_text != last_saved_plate:
            print("   -> ❌ Rejected: Confidence 60% se kam hai (Doubtful hai)")
        return

    if plate_text == last_saved_plate:
        return # Same plate ke liye khamosh raho taake spam na ho

    # --- AGAR SAB THEEK HAI TOH PASS KRO ---
    print(f"\n✅ PASSED: Valid Plate Mili -> {plate_text}")
    
    # Memory update
    last_saved_plate = plate_text

    # Send to Database
    if plate_text:
        payload = {"plate_number": plate_text, "event_type": "entry", "gate": "Main_Gate", "confidence": avg_conf}
        try:
            res = requests.post(FLASK_API_URL, json=payload)
            if res.status_code in [200, 201]:
                print(f"💾 DATA SAVED: {plate_text} database mein chali gayi!\n")
        except:
            print("⚠️ Flask backend offline hai.\n")

# --- LIVE CAMERA LOOP ---
print("Camera on ho raha hai... (Automatic Scanning Active! 🚀 Band karne ke liye 'q' dabayen)")
cap = cv2.VideoCapture(0)

last_scan_time = time.time()
scan_interval = 1.0  # 1 second ka waqfa

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera nahi chal raha!")
        break

    cv2.imshow("AutoGate Live Scanner", frame)

    current_time = time.time()
    if current_time - last_scan_time > scan_interval:
        process_frame(frame)
        last_scan_time = current_time 

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): 
        break

cap.release()
cv2.destroyAllWindows()