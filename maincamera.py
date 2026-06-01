import requests
from inference_sdk import InferenceHTTPClient

# --- CONFIGURATION ---
ROBOFLOW_API_KEY = "L0p9rnM3YsdK54JbuWRY"
PROJECT_ID = "pakistan-license-plate-detection" 
VERSION = "1"
FLASK_API_URL = "http://localhost:5000/api/parking/event"

CLIENT = InferenceHTTPClient(
    api_url="http://localhost:9001",
    api_key=ROBOFLOW_API_KEY
)

print("Model Setup Ready! (2-Line Plate Sorting Active 🚀)")

def process_vehicle(image_path):
    print(f"\nProcessing Image: {image_path}")
    
    # 1. Detect everything via Roboflow Local Server
    result = CLIENT.infer(image_path, model_id=f"{PROJECT_ID}/{VERSION}")
    predictions = result.get('predictions', [])
    
    if not predictions:
        print("No license plate detected!")
        return

    # 2. Plate wale box ko nikal do
    char_predictions = [p for p in predictions if p['class'].lower() != 'plate']
    
    if not char_predictions:
        print("Model ne plate toh dekhi, par uske andar ke letters detect nahi kiye!")
        return

    # 3. Asal Jadoo: Top aur Bottom Lines ko alag karna
    # Average Y-axis nikalte hain taake pata chale kaun upar hai aur kaun neechay
    avg_y = sum(p['y'] for p in char_predictions) / len(char_predictions)
    
    # Upar wali line (Letters)
    top_line = [p for p in char_predictions if p['y'] < avg_y]
    # Neechay wali line (Numbers)
    bottom_line = [p for p in char_predictions if p['y'] >= avg_y]
    
    # Dono lines ko alag alag Left-to-Right (X-axis) sort karna
    top_line.sort(key=lambda item: item['x'])
    bottom_line.sort(key=lambda item: item['x'])
    
    # Dono ko jorna (Pehle Upar wali line, phir Neechay wali)
    sorted_chars = top_line + bottom_line
    
    # 4. Saare letters ko jor kar ek string bana lo
    plate_text = "".join([p['class'] for p in sorted_chars]).upper()
    
    # Agar model ne ghalti se '-' ya koi aur nishan detect kiya ho toh usey filter karein
    plate_text = ''.join(e for e in plate_text if e.isalnum())
    
    # Average confidence nikalna
    avg_confidence = sum([p['confidence'] for p in char_predictions]) / len(char_predictions)
    avg_confidence = round(avg_confidence, 2)
    
    print(f"-> Detected Plate Text: {plate_text} (Confidence: {avg_confidence})")

    # 5. Send to Database
    if plate_text:
        payload = {
            "plate_number": plate_text,
            "event_type": "entry", 
            "gate": "Main_Gate",
            "confidence": avg_confidence
        }
        try:
            response = requests.post(FLASK_API_URL, json=payload)
            if response.status_code in [200, 201]:
                print(f"SUCCESS: Plate {plate_text} database mein chali gayi!")
            else:
                print(f"API Error: {response.text}")
        except requests.exceptions.ConnectionError:
            print("ERROR: Flask backend offline hai. Naye terminal tab mein 'python app.py' chalayen.")

if __name__ == "__main__":
    process_vehicle("test_car.jpg")
    