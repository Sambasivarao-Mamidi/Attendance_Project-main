import cv2
import os
import face_recognition
import pickle
import numpy as np
import re # For checking name format

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(script_dir, "dataset")
ENCODINGS_FILE = os.path.join(script_dir, "encodings.pickle")

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
    
    # Rule 1: Must be exactly 10 characters
    if len(roll_no) != 10:
        print(f"❌ Invalid Length. Roll No must be exactly 10 characters (You entered {len(roll_no)}).")
        continue
        
    # Rule 2: Must be alphanumeric (letters + numbers)
    if not roll_no.isalnum():
        print("❌ Invalid Format. Roll No should only contain Letters and Numbers.")
        continue
        
    # Rule 3: Must contain at least one digit (Prevents typing Name here)
    if not any(char.isdigit() for char in roll_no):
        print("❌ Error: Roll No must contain numbers. Did you type a Name by mistake?")
        continue
        
    break

# 4. Name Validation (Letters only, no numbers)
while True:
    # Changed .title() to .upper() for consistent casing
    name = input("Enter Name: ").strip().upper() 
    
    # Rule 1: Check length
    if len(name) < 3:
        print("❌ Name too short.")
        continue
        
    # Rule 2: No numbers allowed in name
    if any(char.isdigit() for char in name):
        print("❌ Error: Name cannot contain numbers. Did you type Roll No by mistake?")
        continue
        
    # Rule 3: Allow alphabets and spaces only
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
                # Check if Roll No matches but Folder Name is different
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
        if cam.isOpened():
            ret, frame = cam.read()
            cam.release()
            
            if ret:
                # Resize for speed
                small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                boxes = face_recognition.face_locations(rgb)
                
                if len(boxes) > 0:
                    enc = face_recognition.face_encodings(rgb, boxes)[0]
                    dists = face_recognition.face_distance(data["encodings"], enc)
                    
                    if len(dists) > 0:
                        min_dist = np.min(dists)
                        # Strict check: If face similarity < 0.4, it's the same person
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

# 8. Start Camera
cam = cv2.VideoCapture(0)
detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
count = 0

print("[INFO] Capturing 20 images... Please move your head slightly.")

while True:
    ret, frame = cam.read()
    if not ret: break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        count += 1
        cv2.imwrite(f"{student_path}/{name}_{count}.jpg", frame[y:y+h, x:x+w])
        cv2.putText(frame, f"Captured: {count}/20", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow('Registering Student', frame)
    if count >= 20 or cv2.waitKey(1) == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()
print(f"[SUCCESS] Registration Completed for {name} (Roll: {roll_no})")