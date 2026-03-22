import sys
import cv2
import os
import face_recognition
import pickle
import numpy as np
import csv
import time  # Added for capture delay
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# --- LCD DISPLAY SETUP ---
LCD_ENABLED = True
LCD_I2C_ADDRESS = 0x27
LCD_COLS = 16
LCD_ROWS = 2

try:
    from RPLCD.i2c import CharLCD
    lcd = CharLCD('PCF8574', LCD_I2C_ADDRESS, cols=LCD_COLS, rows=LCD_ROWS)
    lcd.clear()
except Exception as e:
    lcd = None
    LCD_ENABLED = False

def lcd_display(line1="", line2=""):
    if not LCD_ENABLED or lcd is None: return
    try:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string(line1[:LCD_COLS].center(LCD_COLS))
        lcd.cursor_pos = (1, 0)
        lcd.write_string(line2[:LCD_COLS].center(LCD_COLS))
    except: pass

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(script_dir, "dataset")
ENCODINGS_FILE = os.path.join(script_dir, "encodings.pickle")
STUDENTS_DB = os.path.join(script_dir, "students_db.csv")

if not os.path.exists(DATASET_DIR):
    os.makedirs(DATASET_DIR)

# --- INITIALIZE ENVIRONMENT AND FIREBASE ---
load_dotenv(os.path.join(script_dir, '.env'))

FIREBASE_URL = os.environ.get("FIREBASE_URL")
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(os.path.join(script_dir, "serviceAccountKey.json"))
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
        print("[INFO] Firebase Initialized successfully in capture script.")
    except Exception as e:
        print(f"[WARNING] Firebase init failed in capture: {e}")

# --- INITIALIZE CLOUDINARY ---
try:
    cloudinary.config(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key=os.environ.get("CLOUDINARY_API_KEY"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
        secure=True
    )
    print("[INFO] Cloudinary Configurations Loaded.")
except Exception as e:
    print(f"[WARNING] Cloudinary init failed: {e}")

print("=== 🎓 NEW STUDENT REGISTRATION (VALIDATION MODE) ===")
print("Please enter details strictly as requested.")
lcd_display("NEW STUDENT", "Enter details")

# --- INPUT VALIDATION LOOPS ---

# If the master script hands us a name, use it. Otherwise, use keyboard input.
if len(sys.argv) > 1:
    raw_arg = sys.argv[1]
    if "_" in raw_arg:
        parts = raw_arg.split("_")
        if len(parts) >= 4:
            year = parts[0]
            section = parts[1]
            roll_no = parts[2]
            name = "_".join(parts[3:]).upper()
        else:
            year = "0"
            section = "X"
            roll_no = "UNKNOWN"
            name = raw_arg.upper()
    else:
        year = "0"
        section = "X"
        roll_no = "UNKNOWN"
        name = raw_arg.upper()
    student_phone = "0000000000"
    parent_phone = "0000000000"
    print(f"[AUTO-MODE] Enrolling from Dashboard: {name} (Roll: {roll_no})")
else:
    # 1. Year Validation (1-4 only)
    while True:
        year = input("Enter Year (1, 2, 3, 4): ").strip()
        if year in ['1', '2', '3', '4']:
            break
        print("❌ Invalid Year. Please enter a number between 1 and 4.")

    # 2. Section Validation (A or B only)
    while True:
        section = input("Enter Section (A/B): ").strip().upper()
        if section in ['A', 'B']:
            break
        print("❌ Invalid Section. Only 'A' or 'B' allowed.")

    # 3. Roll Number Validation (10 chars, must have numbers)
    while True:
        roll_no = input("Enter Roll No (e.g., 22NR1A0462): ").strip().upper()
    
        if len(roll_no) != 10:
            print(f"❌ Invalid Length. Roll No must be exactly 10 characters (You entered {len(roll_no)}).")
            continue
        
        if not roll_no.isalnum():
            print("❌ Invalid Format. Roll No should only contain Letters and Numbers.")
            continue
        
        if not any(char.isdigit() for char in roll_no):
            print("❌ Error: Roll No must contain numbers. Did you type a Name by mistake?")
            continue
        
        break

    # 4. Name Validation (Letters only, no numbers)
    while True:
        name = input("Enter Name: ").strip().upper() 
    
        if len(name) < 3:
            print("❌ Name too short.")
            continue
        
        if any(char.isdigit() for char in name):
            print("❌ Error: Name cannot contain numbers. Did you type Roll No by mistake?")
            continue
        
        if not all(x.isalpha() or x.isspace() for x in name):
            print("❌ Error: Name should only contain letters.")
            continue
        
        break

    # 4.5 Student Phone Validation
    while True:
        student_phone = input("Enter Student Phone (10 digits): ").strip()
        if len(student_phone) == 10 and student_phone.isdigit():
            break
        print("❌ Invalid Phone Number. Must be exactly 10 digits.")

    # 4.6 Parent Phone Validation 
    while True:
        parent_phone = input("Enter Parent Phone (10 digits): ").strip()
        if len(parent_phone) == 10 and parent_phone.isdigit():
            break
        print("❌ Invalid Phone Number. Must be exactly 10 digits.")

    
# Construct folder name
folder_name = f"{year}_{section}_{roll_no}_{name}"
student_path = os.path.join(DATASET_DIR, folder_name)

print(f"\n✅ Data Verified: {folder_name}")

# 5. --- SECURITY CHECK 1: ROLL NUMBER CONFLICT ---
conflict = False
existing_owner = ""
for folder in os.listdir(DATASET_DIR):
    if os.path.isdir(os.path.join(DATASET_DIR, folder)):
        try:
            parts = folder.split("_")
            if len(parts) >= 4:
                if parts[2] == roll_no and folder != folder_name:
                    conflict = True
                    existing_owner = folder
                    break
        except: continue

if conflict:
    print(f"\n[ERROR] Roll Number {roll_no} is ALREADY REGISTERED to:")
    print(f"   -> {existing_owner}")
    print("Registration ABORTED to prevent duplicate IDs.")
    lcd_display("ID CONFLICT!", "Aborted.")
    time.sleep(3)
    lcd_display("", "")
    exit()

# 6. --- SECURITY CHECK 2: FACE DUPLICATION (ANTI-PROXY) ---
if os.path.exists(ENCODINGS_FILE):
    print("\n[SECURITY] Scanning for Duplicate Faces... Look at the camera.")
    lcd_display("SECURITY SCAN", "Look at camera")
    
    try:
        data = pickle.loads(open(ENCODINGS_FILE, "rb").read())
        cam = cv2.VideoCapture(0)
        
        # --- WINDOW SETUP FOR SECURITY SCAN ---
        scan_window = "Security Scan"
        cv2.namedWindow(scan_window, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(scan_window, cv2.WND_PROP_TOPMOST, 1)

        if cam.isOpened():
            ret, frame = cam.read()
            cam.release()
            cv2.destroyWindow(scan_window)
            
            if ret:
                small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                boxes = face_recognition.face_locations(rgb)
                
                if len(boxes) > 0:
                    enc = face_recognition.face_encodings(rgb, boxes)[0]
                    dists = face_recognition.face_distance(data["encodings"], enc)
                    
                    if len(dists) > 0:
                        min_dist = np.min(dists)
                        if min_dist < 0.4:
                            match_idx = np.argmin(dists)
                            existing_person = data["names"][match_idx]
                            
                            print("\n" + "!"*60)
                            print(f"[SECURITY ALERT] DUPLICATE FACE DETECTED!")
                            lcd_display("DUPLICATE FACE", "Aborted.")
                            time.sleep(3)
                            lcd_display("", "")
                            print(f"This person is ALREADY registered as: {existing_person}")
                            print(f"Similarity Match: {min_dist:.2f}")
                            print("You cannot register the same person with a different name.")
                            print("!"*60)
                            exit()
                else:
                    print("[WARNING] No face detected. Ensure good lighting.")
    except Exception as e:
        print(f"[WARNING] Security scan skipped: {e}")

# 7. Proceed to Registration
if not os.path.exists(student_path):
    os.makedirs(student_path)
    print(f"\n[INFO] Creating Profile for: {name}")
else:
    print(f"\n[INFO] Student exists. Adding more training photos.")

# 8. --- IMPROVED CAMERA CAPTURE ---
cam = cv2.VideoCapture(0)
detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
count = 0
last_capture_time = 0

print("[INFO] Capturing 20 images... Please move your head slightly.")
lcd_display("CAPTURING...", "Move head slowly")

# --- WINDOW SETUP FOR REGISTRATION ---
window_name = 'Registering Student'
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

while True:
    ret, frame = cam.read()
    if not ret: break
    
    # Create a copy for displaying the green box
    display_frame = frame.copy()
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Strict face detection to avoid background noise
    faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=7, minSize=(100, 100))

    for (x, y, w, h) in faces:
        # Draw rectangle only on the display frame
        cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        current_time = time.time()
        
        # 0.3-second delay between captures
        if current_time - last_capture_time > 0.3:
            count += 1
            # Save the FULL, clean frame without the green box drawn on it
            cv2.imwrite(os.path.join(student_path, f"{name}_{count}.jpg"), frame)
            last_capture_time = current_time
            
        cv2.putText(display_frame, f"Captured: {count}/20", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        break  # Process only one face to avoid capturing multiple people at once

    cv2.imshow(window_name, display_frame)
    if count >= 20 or cv2.waitKey(1) == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
print(f"[SUCCESS] Registration Completed for {name} (Roll: {roll_no})")
lcd_display("SUCCESS!", name[:LCD_COLS])
time.sleep(3)
lcd_display("SYSTEM READY", "")

# 9. --- CLOUDINARY UPLOAD BATCH ---
if count > 0:
    print("\n[INFO] Uploading 20 images to Cloudinary. Please wait...")
    lcd_display("UPLOADING...", "To Cloudinary")
    
    training_urls = []
    public_ids = []
    
    try:
        for i in range(1, count + 1):
            img_path = os.path.join(student_path, f"{name}_{i}.jpg")
            if os.path.exists(img_path):
                resp = cloudinary.uploader.upload(img_path, folder=f"attendance_system/{roll_no}")
                training_urls.append(resp['secure_url'])
                public_ids.append(resp['public_id'])
                print(f"  -> Uploaded {i}/{count}")
        
        if training_urls:
            print("[SUCCESS] All images uploaded! Saving URLs to Firebase...")
            db.reference(f'Students/{roll_no}').update({
                'name': name,
                'year': year,
                'section': section,
                'training_images': training_urls,
                'cloudinary_public_ids': public_ids
            })
            print(f"[SUCCESS] URLs pushed to Firebase under Students/{roll_no}")
            lcd_display("CLOUD SYNC", "Complete!")
            time.sleep(2)
    except Exception as e:
        print(f"❌ [ERROR] Cloudinary Upload Failed: {e}")

# 10. --- AUTO-SAVE TO STUDENTS DATABASE ---
print(f"\n[INFO] Adding student to database...")
try:
    student_exists = False
    if os.path.exists(STUDENTS_DB):
        with open(STUDENTS_DB, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Handle empty CSVs without headers properly
            if reader.fieldnames:
                for row in reader:
                    if row.get('RollNo', '').strip() == roll_no:
                        student_exists = True
                        print(f"[INFO] Student {roll_no} already in database. Skipping...")
                        break
    
    if not student_exists:
        # If file doesn't exist, we should write headers first
        write_headers = not os.path.exists(STUDENTS_DB)
        with open(STUDENTS_DB, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if write_headers:
                writer.writerow(['RollNo', 'Name', 'Section', 'StudentPhone', 'ParentPhone'])
            writer.writerow([roll_no, name, section, student_phone, parent_phone])
            
        print(f"✅ [SUCCESS] Student added to database:")
        print(f"   RollNo: {roll_no}")
        print(f"   Name: {name}")
        print(f"   Section: {section}")
        print(f"   Student Phone: {student_phone}")
        print(f"   Parent Phone: {parent_phone}")
    
except Exception as e:
    print(f"❌ [ERROR] Failed to save to database: {e}")