import requests
import random
import time
from datetime import datetime, timedelta

# Aapke Flask Server ka URL
FLASK_API_URL = "http://localhost:5000/api/parking/event"

# --- DUMMY DATA LISTS ---
PREFIXES = ['LEF', 'LEC', 'LAA', 'RIZ', 'ICT', 'SND', 'BAL', 'MN', 'AJA']
NAMES = ['Ali', 'Ayesha', 'Usman', 'Fatima', 'Bilal', 'Zainab', 'Hassan', 'Khadija', 'Omer', 'Maryam', 'Hamza', 'Iqra', 'Kamran', 'Sana', 'Tariq']
DEPARTMENTS = ['IT', 'Student', 'Administrator']

def seed_via_api(num_cars=35):
    print("🚀 API Seeding shuru ho rahi hai... 35 gariyan parking ki taraf aa rahi hain!\n")
    
    success_count = 0
    current_time = datetime.now()
    
    for i in range(num_cars):
        # Random data generate karna
        plate = f"{random.choice(PREFIXES)}{random.randint(1000, 9999)}"
        confidence = round(random.uniform(0.70, 0.99), 2)
        owner_name = random.choice(NAMES)
        department = random.choice(DEPARTMENTS)
        
        # Time logic: Har iteration par 1 ghanta peeche jana
        # (e.g., 1st car = abhi, 2nd car = 1 hour ago, 3rd car = 2 hours ago)
        entry_time = current_time - timedelta(hours=i)
        
        # Naya payload jisme Owner, Department aur Time bhi shamil hai
        payload = {
            "plate_number": plate,
            "event_type": "entry", 
            "gate": "Main_Gate",
            "confidence": confidence,
            "owner": owner_name,
            "department": department,
            "timestamp": entry_time.isoformat() # Time ko string format mein bhejna
        }
        
        try:
            # API ko request bhejein
            response = requests.post(FLASK_API_URL, json=payload)
            
            if response.status_code in [200, 201]:
                time_str = entry_time.strftime("%I:%M %p") # e.g., 02:30 PM
                print(f"✅ Bheji Gayi: {plate} | {owner_name} ({department}) | Time: {time_str}")
                success_count += 1
            else:
                print(f"❌ Error for {plate}: API ne reject kar diya ({response.text})")
                
        except requests.exceptions.ConnectionError:
            print("\n🛑 ERROR: Flask backend offline hai!")
            print("💡 Hint: Dusre terminal tab mein 'python app.py' chala kar server on karein.")
            return 
            
        time.sleep(0.1)

    print(f"\n🎉 KAMYABI: {success_count} gariyan successfully AutoGate se guzar kar DB mein save ho gayin!")

if __name__ == "__main__":
    seed_via_api(35)