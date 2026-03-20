import cv2
import os
import face_recognition
import pickle
import numpy as np
import csv
import time  # Added for capture delay

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(script_dir, "dataset")
ENCODINGS_FILE = os.path.join(script_dir, "encodings.pickle")
STUDENTS_DB = os.path.join(script_dir, "students_db.csv")

if not os.path.exists(DATASET_DIR):
    os.makedirs(DATASET_DIR)

print("=== 🎓 NEW STUDENT REGISTRATION (VALIDATION MODE) ===")
print("Please enter details strictly as requested.")

# --- INPUT VALIDATION LOOPS ---

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
    exit()

# 6. --- SECURITY CHECK 2: FACE DUPLICATION (ANTI-PROXY) ---
if os.path.exists(ENCODINGS_FILE):
    print("\n[SECURITY] Scanning for Duplicate Faces... Look at the camera.")
    
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

# 9. --- AUTO-SAVE TO STUDENTS DATABASE ---
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
                writer.writerow(['RollNo', 'Name', 'Section'])
            writer.writerow([roll_no, name, section])
            
        print(f"✅ [SUCCESS] Student added to database:")
        print(f"   RollNo: {roll_no}")
        print(f"   Name: {name}")
        print(f"   Section: {section}")
    
except Exception as e:
    print(f"❌ [ERROR] Failed to save to database: {e}")