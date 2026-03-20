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
from threading import Thread
from queue import Queue
# --- CONFIGURATION FOR RASPBERRY PI 4 ---
# EAR (Eye Aspect Ratio) for Liveness Detection (Blink Detection)
# Standard range: 0.20 - 0.30. Adjust based on camera quality and lighting.
# Typical Open Eye: 0.30 - 0.40
# Typical Closed Eye: 0.15 - 0.20
EYE_AR_THRESH = 0.25  # Threshold below which eye is considered closed
EYE_AR_CONSEC_FRAMES = 1  # FAST: Detect blink on 1st closed frame (adjust to 2 if false positives occur)
ENABLE_LIVENESS = True
DEBUG_EAR = False  # Set to True to print EAR values for calibration
SESSION_DURATION_MINUTES = 15
COOLDOWN_SECONDS = 60

# [PI OPTIMIZATION 1] Set to 2 for FASTER detection
# 1 = processes every frame (very responsive but CPU heavy)
# 2 = processes every 2 frames (recommended for speed + Pi compatibility)
# 3 = processes every 3 frames (most Pi-friendly, slowest detection)
PROCESS_EVERY_N_FRAMES = 2  

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
def init_firebase():
    global ref_attendance, ref_students
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

# Initialize Firebase in background (non-blocking)
firebase_thread = Thread(target=init_firebase, daemon=True)
firebase_thread.start()

# --- BACKGROUND CLOUD SYNC QUEUE & THREAD ---
cloud_sync_queue = Queue(maxsize=100)

def cloud_sync_worker():
    """Background thread worker for non-blocking Firebase uploads"""
    while True:
        try:
            upload_data = cloud_sync_queue.get()
            if upload_data is None:  # Poison pill to stop thread
                break
            
            if ref_attendance:
                try:
                    ref_attendance.push(upload_data)
                    print(f"[FIREBASE] Uploaded: {upload_data['name']}")
                except Exception as e:
                    print(f"[ERROR] Cloud sync failed: {e}")
            
            cloud_sync_queue.task_done()
        except Exception as e:
            print(f"[ERROR] Cloud sync worker error: {e}")

# Start background cloud sync thread
cloud_sync_thread = Thread(target=cloud_sync_worker, daemon=True)
cloud_sync_thread.start()

# --- LOAD DATA ---
if not enc_path: exit("[ERROR] Encodings missing.")
data = pickle.loads(open(enc_path, "rb").read())

if not os.path.exists(log_file):
    with open(log_file, "w") as f: f.write("Name,Roll,Year,Section,Time,Date,Status\n")

# --- SYNC ROSTER TO CLOUD ---
def sync_roster():
    if not ref_students: return
    print("[INFO] Syncing Class Roster to Cloud (Background)...")
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

# Run roster sync in background thread (non-blocking)
roster_sync_thread = Thread(target=sync_roster, daemon=True)
roster_sync_thread.start()

# --- HELPER: EAR (Eye Aspect Ratio) ---
# Computes the eye aspect ratio from 6 landmarks around the eye
# Formula: EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
# Where p1-p6 are the 6 points around the eye (top, top-right, bottom-right, bottom, bottom-left, top-left)
def get_ear(eye):
    """Calculate Eye Aspect Ratio from eye landmarks"""
    A = dist.euclidean(eye[1], eye[5])  # Vertical distance top-right
    B = dist.euclidean(eye[2], eye[4])  # Vertical distance bottom-right
    C = dist.euclidean(eye[0], eye[3])  # Horizontal distance
    return (A + B) / (2.0 * C)

def calibrate_ear_threshold():
    """
    Calibration helper: Run the camera and observe EAR values.
    Adjust EYE_AR_THRESH based on these observations:
    - Sit normally: EAR should be around 0.30+
    - Blink: EAR should drop to 0.18
    - If detects blinks when eyes open: lower threshold (try 0.22)
    - If never detects blinks: raise threshold (try 0.28)
    """
    print(f"[CALIBRATION] Current EAR Threshold: {EYE_AR_THRESH}")
    print(f"[CALIBRATION] Consecutive Frames Required: {EYE_AR_CONSEC_FRAMES}")
    print("[CALIBRATION] Watch the terminal for EAR values below.")
    print("[CALIBRATION] Sit normally (eyes open) - EAR should be 0.30+")
    print("[CALIBRATION] Blink - EAR should drop to 0.18")

# --- MAIN LOOP ---
cap = cv2.VideoCapture(0)

# [PI OPTIMIZATION 2] Force Camera to 640x480
# This prevents the Pi from wasting CPU on HD images before resizing.
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 768)

marked_students = {}
blink_counters = {}
verified_real = {}
last_attendance_time = {}

face_locations = []
face_names = []
face_real_status = []  

frame_count = 0  
session_end = datetime.now() + timedelta(minutes=SESSION_DURATION_MINUTES)

print("\n" + "="*60)
print("[INFO] ✓ Attendance System READY!")
print("[INFO] Loading: Face encodings loaded, Camera initialized")
print("[INFO] Background: Firebase & Roster sync running in background")
print("[INFO] Press 'q' to quit | 'e' to extend session")
print("="*60 + "\n")

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
        
        # Use HOG model for Pi compatibility (much faster than CNN)
        face_locations = face_recognition.face_locations(rgb, model="hog")
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

            # LIVENESS CHECK - Blink Detection for Photo Spoofing Prevention
            is_real = False
            if ENABLE_LIVENESS and name != "Unknown":
                if i < len(landmarks):
                    lm = landmarks[i]
                    left_ear = get_ear(lm["left_eye"])
                    right_ear = get_ear(lm["right_eye"])
                    ear = (left_ear + right_ear) / 2.0
                    
                    if DEBUG_EAR:
                        print(f"[EAR] {name}: L={left_ear:.3f}, R={right_ear:.3f}, Avg={ear:.3f}, Threshold={EYE_AR_THRESH}")
                    
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
                
                # --- COOLDOWN MECHANISM (DEBOUNCING) ---
                if name in last_attendance_time:
                    time_since_last = (now - last_attendance_time[name]).total_seconds()
                    if time_since_last < COOLDOWN_SECONDS:
                        print(f"[SKIP] {name} already marked {time_since_last:.1f}s ago (cooldown: {COOLDOWN_SECONDS}s)")
                        continue
                
                # Mark attendance
                print(f"[MARKED] {name}")
                last_attendance_time[name] = now
                
                with open(log_file, "a") as f:
                    f.write(f"{name},{roll},{yr},{sec},{t_str},{d_str},Present\n")
                
                # Non-blocking: Queue the upload instead of waiting for it
                upload_data = {
                    'name': name, 'roll_no': roll, 'year': yr, 
                    'section': sec, 'time': t_str, 'date': d_str
                }
                try:
                    cloud_sync_queue.put_nowait(upload_data)
                except Exception as e:
                    print(f"[WARNING] Upload queue full, skipping: {e}")

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

# Graceful shutdown: Stop the background sync thread
print("[INFO] Stopping background sync thread...")
cloud_sync_queue.put(None)  # Send poison pill
cloud_sync_thread.join(timeout=5)  # Wait up to 5 seconds
print("[INFO] Shutdown complete.")