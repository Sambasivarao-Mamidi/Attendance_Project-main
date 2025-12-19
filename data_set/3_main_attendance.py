import cv2
import face_recognition
import pickle
import numpy as np
import os
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv
from scipy.spatial import distance as dist

# --- CONFIGURATION FOR RASPBERRY PI 4 ---
EYE_AR_THRESH = 0.25
EYE_AR_CONSEC_FRAMES = 2
ENABLE_LIVENESS = True
SESSION_DURATION_MINUTES = 15

# [PI OPTIMIZATION 1] Set to 3. 
# 2 is too laggy for Pi, 5 misses blinks. 3 is the sweet spot.
PROCESS_EVERY_N_FRAMES = 3  

# --- PATH SETUP ---
load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

def find_file(name):
    for path in [os.path.join(script_dir, name), os.path.join(parent_dir, name)]:
        if os.path.exists(path): return path
    return None

key_path = find_file("serviceAccountKey.json")
enc_path = find_file("encodings.pickle")
log_file = os.path.join(script_dir, "attendance_log.csv")

# --- FIREBASE INIT ---
ref_attendance = None
ref_students = None
if key_path:
    try:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {'databaseURL': os.getenv("FIREBASE_URL")})
        ref_attendance = db.reference('attendance')
        ref_students = db.reference('students')
        print("[INFO] Firebase Connected!")
    except Exception as e:
        print(f"[ERROR] Firebase Connection Failed: {e}")
        ref_attendance = None
else:
    print("[WARNING] serviceAccountKey.json not found. Firebase disabled.")

# --- LOAD DATA ---
if not enc_path: exit("[ERROR] Encodings missing.")
data = pickle.loads(open(enc_path, "rb").read())

if not os.path.exists(log_file):
    with open(log_file, "w") as f: f.write("Name,Roll,Year,Section,Time,Date,Status\n")

# --- SYNC ROSTER TO CLOUD ---
def sync_roster():
    if not ref_students: return
    print("[INFO] Syncing Class Roster to Cloud...")
    unique_students = set(data["names"])
    
    for full_info in unique_students:
        if full_info == "Unknown": continue
        try:
            parts = full_info.split("_")
            if len(parts) >= 4:
                yr, sec, roll, name = parts[0], parts[1], parts[2], parts[3]
                ref_students.child(roll).update({
                    'name': name,
                    'roll_no': roll,
                    'year': yr,
                    'section': sec
                })
        except Exception as e:
            print(f"[ERROR] Sync failed for {full_info}: {e}")
    print("[INFO] Roster Synced Successfully.")

sync_roster()

# --- HELPER: EAR ---
def get_ear(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

# --- MAIN LOOP ---
cap = cv2.VideoCapture(0)

# [PI OPTIMIZATION 2] Force Camera to 640x480
# This prevents the Pi from wasting CPU on HD images before resizing.
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 768)

marked_students = {}
blink_counters = {}
verified_real = {}

face_locations = []
face_names = []
face_real_status = []  

frame_count = 0  
session_end = datetime.now() + timedelta(minutes=SESSION_DURATION_MINUTES)

print("[INFO] Camera Started. IMPORTANT: Click the Video Window before pressing 'q' to quit.")

# --- WINDOW SETUP ---
window_name = "Attendance System"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

while True:
    ret, frame = cap.read()
    if not ret: break

    frame_count += 1
    process_this_frame = (frame_count % PROCESS_EVERY_N_FRAMES == 0)

    now = datetime.now()
    active = (session_end - now).total_seconds() > 0

    # Resize (1/4th scale)
    # Since input is now 640x480, this makes processing image extremely small (160x120) -> Very Fast for Pi
    small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    
    if process_this_frame and active:
        face_names = []
        face_real_status = []
        
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb)
        encs = face_recognition.face_encodings(rgb, face_locations)
        
        landmarks = []
        if ENABLE_LIVENESS: 
            landmarks = face_recognition.face_landmarks(rgb, face_locations)

        for i, (enc, loc) in enumerate(zip(encs, face_locations)):
            dists = face_recognition.face_distance(data["encodings"], enc)
            idx = np.argmin(dists)
            full_info = "Unknown"
            name = "Unknown"

            if dists[idx] < 0.5:
                full_info = data["names"][idx]
                try: name = full_info.split("_")[3]
                except: name = full_info

            face_names.append(name)

            # LIVENESS CHECK
            is_real = False
            if ENABLE_LIVENESS and name != "Unknown":
                if i < len(landmarks):
                    lm = landmarks[i]
                    ear = (get_ear(lm["left_eye"]) + get_ear(lm["right_eye"])) / 2.0
                    
                    if name not in blink_counters: blink_counters[name] = 0
                    if name not in verified_real: verified_real[name] = False

                    if ear < EYE_AR_THRESH: 
                        blink_counters[name] += 1
                    else:
                        if blink_counters[name] >= EYE_AR_CONSEC_FRAMES: 
                            verified_real[name] = True
                        blink_counters[name] = 0
                    
                    if verified_real[name]: is_real = True
            else:
                is_real = True
            
            face_real_status.append(is_real)

            if name != "Unknown" and is_real:
                try: yr, sec, roll = full_info.split("_")[:3]
                except: yr, sec, roll = "-", "-", "-"
                
                t_str = now.strftime("%H:%M:%S")
                d_str = now.strftime("%Y-%m-%d")
                
                print(f"[MARKED] {name}")
                
                with open(log_file, "a") as f:
                    f.write(f"{name},{roll},{yr},{sec},{t_str},{d_str},Present\n")
                
                if ref_attendance:
                    try:
                        ref_attendance.push({
                            'name': name, 'roll_no': roll, 'year': yr, 
                            'section': sec, 'time': t_str, 'date': d_str
                        })
                        print(f"[FIREBASE] Uploaded attendance for {name}")
                    except Exception as e:
                        print(f"[ERROR] Firebase upload failed: {e}")

    # --- DRAWING ---
    for (top, right, bottom, left), name, is_real in zip(face_locations, face_names, face_real_status):
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        if name == "Unknown":
            color = (0, 0, 255) 
            status_text = "Unknown"
        elif is_real:
            color = (0, 255, 0) 
            status_text = "Real"
        else:
            color = (255, 0, 0) # Blue
            status_text = "Blink?"

        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(frame, f"{name} ({status_text})", (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow(window_name, frame)
    
    k = cv2.waitKey(10) & 0xFF
    if k == ord('q'): 
        print("[INFO] Quit pressed. Closing...")
        break
    if k == ord('e'): 
        session_end += timedelta(minutes=10)
        print("[INFO] Time Extended")

cap.release()
cv2.destroyAllWindows()