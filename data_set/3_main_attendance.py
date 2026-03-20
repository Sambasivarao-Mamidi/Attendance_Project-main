import cv2
import face_recognition
import pickle
import numpy as np
import os
import time
import threading
import csv
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, db
from scipy.spatial import distance as dist
from threading import Thread
from queue import Queue

# --- LCD DISPLAY SETUP ---
LCD_ENABLED = True
LCD_POWER_SAVE = False  # Set True to disable backlight (saves ~20mA)
LCD_I2C_ADDRESS = 0x27
LCD_COLS = 16
LCD_ROWS = 2

# Global flag to prevent LCD messages from overlapping
is_busy_displaying = False

try:
    from RPLCD.i2c import CharLCD
    lcd = CharLCD('PCF8574', LCD_I2C_ADDRESS, cols=LCD_COLS, rows=LCD_ROWS)
    lcd.clear()
    if LCD_POWER_SAVE:
        lcd.backlight_enabled = False  # Disable backlight to save power
        print("[INFO] LCD Display Connected (Power-Save Mode: Backlight OFF)")
    else:
        print("[INFO] LCD Display Connected!")
except Exception as e:
    lcd = None
    LCD_ENABLED = False
    print(f"[WARNING] LCD not available: {e}")

# --- CONFIGURATION (Pi 4 4GB Optimized) ---
EYE_AR_THRESH = 0.32  # Raised from 0.25 - prevents false blink detection
EYE_AR_CONSEC_FRAMES = 3  # Require 3 consecutive frames for valid blink (slower blink)
EYE_AR_MIN_FRAMES = 2  # Minimum frames eyes must be closed (prevents rapid blinks)
ENABLE_LIVENESS = True
PROCESS_EVERY_N_FRAMES = 2  # Pi 4 can handle every 2nd frame
COOLDOWN_SECONDS = 7200  # 2 hours = 7200 seconds

# --- Pi 4 SPECIFIC OPTIMIZATIONS ---
FACE_SCALE_FACTOR = 0.3  # Slightly larger for better accuracy on Pi 4
USE_THREADING = True  # Pi 4 has 4 cores - utilize them

# --- PATH SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
enc_path = os.path.join(script_dir, "encodings.pickle")
key_path = os.path.join(script_dir, "serviceAccountKey.json")
log_file = os.path.join(script_dir, "attendance_log.csv")

# --- FIREBASE URL (hardcoded for Pi deployment) ---
FIREBASE_URL = "https://attendance-system-2ad29-default-rtdb.asia-southeast1.firebasedatabase.app"

# --- FIREBASE INITIALIZATION ---
if not os.path.exists(enc_path): exit("[ERROR] Encodings missing.")
data = pickle.loads(open(enc_path, "rb").read())

# Initialize Firebase
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_URL
        })
    print("[INFO] Firebase Connected!")
except Exception as e:
    print(f"[WARNING] Firebase init failed: {e}")

# --- ATTENDANCE LOGGING FUNCTIONS ---
def write_to_csv(name, roll_no, year, section):
    """Write attendance record to local CSV file"""
    try:
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")
        
        # Ensure file exists with header
        file_exists = os.path.exists(log_file)
        
        with open(log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Name', 'RollNo', 'Year', 'Section', 'Time', 'Date', 'Status'])
            writer.writerow([name, roll_no, year, section, time_str, date_str, 'Present'])
        
        print(f"[CSV] Saved: {name} at {time_str}")
        return True
    except Exception as e:
        print(f"[ERROR] CSV write failed: {e}")
        return False

def sync_to_firebase(name, roll_no, year, section):
    """Sync attendance record to Firebase Realtime Database"""
    try:
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")
        
        # Create unique key for this attendance record
        record_key = f"{roll_no}_{date_str}_{time_str.replace(':', '-')}"
        
        ref = db.reference(f'/attendance/{date_str}')
        ref.child(record_key).set({
            'name': name,
            'rollNo': roll_no,
            'year': year,
            'section': section,
            'time': time_str,
            'date': date_str,
            'status': 'Present',
            'timestamp': now.timestamp()
        })
        
        print(f"[FIREBASE] Synced: {name}")
        return True
    except Exception as e:
        print(f"[ERROR] Firebase sync failed: {e}")
        return False

def mark_attendance(full_info):
    """Parse student info and save attendance to CSV + Firebase"""
    try:
        # Parse folder name format: Year_Section_RollNo_Name
        parts = full_info.split("_")
        if len(parts) >= 4:
            year = parts[0]
            section = parts[1]
            roll_no = parts[2]
            name = parts[3]
        else:
            # Fallback if format is different
            name = full_info
            roll_no = "UNKNOWN"
            year = "0"
            section = "X"
        
        # Write to CSV (local backup)
        write_to_csv(name, roll_no, year, section)
        
        # Sync to Firebase (cloud)
        sync_to_firebase(name, roll_no, year, section)
        
        return name
    except Exception as e:
        print(f"[ERROR] mark_attendance failed: {e}")
        return full_info

# --- IMPROVED LCD FUNCTIONS ---

def lcd_display(line1="", line2=""):
    if not LCD_ENABLED or lcd is None: return
    try:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string(line1[:LCD_COLS].center(LCD_COLS))
        lcd.cursor_pos = (1, 0)
        lcd.write_string(line2[:LCD_COLS].center(LCD_COLS))
    except: pass

def scroll_name_logic(name):
    """Scrolls name on row 1 if it's too long - SLOWER scrolling"""
    if len(name) <= LCD_COLS:
        lcd.cursor_pos = (1, 0)
        lcd.write_string(name.center(LCD_COLS))
        time.sleep(4)  # Hold for 4 seconds for short names
    else:
        # Marquee effect: Slide name across screen (SLOWER)
        display_text = "  " + name + "   "  # Add padding for smooth start
        start_time = time.time()
        while time.time() - start_time < 6:  # Scroll for 6 seconds total
            for i in range(len(display_text)):
                if time.time() - start_time >= 6: break
                lcd.cursor_pos = (1, 0)
                lcd.write_string(display_text[i:i+LCD_COLS].ljust(LCD_COLS))
                time.sleep(0.5)  # Slower scroll speed (was 0.3)

def lcd_show_marked_threaded(name):
    """Background task: Marked -> Display Name -> System Ready"""
    def task():
        global is_busy_displaying, lcd_state, lcd_state_name
        is_busy_displaying = True
        
        # Step 1: Marked message (hold longer)
        lcd_display("ATTENDANCE", "MARKED!")
        time.sleep(2.5)  # Increased from 1.5s
        
        # Step 2: Show/Scroll Name
        if LCD_ENABLED and lcd:
            lcd.clear()
            lcd.cursor_pos = (0, 0)
            lcd.write_string("NAME:".center(LCD_COLS))
            scroll_name_logic(name)
        
        # Step 3: Reset to ready state
        lcd_display("SYSTEM READY", "Show your face")
        lcd_state = "ready"
        lcd_state_name = ""
        is_busy_displaying = False

    threading.Thread(target=task, daemon=True).start()

def lcd_show_cooldown_threaded(name, remaining_mins):
    """Show cooldown message when student already marked"""
    def task():
        global is_busy_displaying, lcd_state
        is_busy_displaying = True
        
        lcd_display("ALREADY MARKED", name[:LCD_COLS])
        time.sleep(2)
        
        # Show remaining time
        if remaining_mins >= 60:
            hrs = remaining_mins // 60
            mins = remaining_mins % 60
            lcd_display("WAIT TIME:", f"{hrs}h {mins}m left")
        else:
            lcd_display("WAIT TIME:", f"{remaining_mins}m left")
        time.sleep(2.5)
        
        lcd_display("SYSTEM READY", "Show your face")
        lcd_state = "ready"
        is_busy_displaying = False
    
    threading.Thread(target=task, daemon=True).start()

def lcd_show_blink_slowly():
    """Show blink slowly message"""
    def task():
        global is_busy_displaying, lcd_state
        is_busy_displaying = True
        
        lcd_display("BLINK SLOWLY", "Hold 1 second")
        time.sleep(2.5)
        
        lcd_display("SYSTEM READY", "Show your face")
        lcd_state = "ready"
        is_busy_displaying = False
    
    threading.Thread(target=task, daemon=True).start()

def lcd_show_error(error_msg):
    """Show error message on LCD"""
    def task():
        global is_busy_displaying, lcd_state
        is_busy_displaying = True
        
        lcd_display("ERROR", error_msg[:LCD_COLS])
        time.sleep(3)
        
        lcd_display("SYSTEM READY", "Show your face")
        lcd_state = "ready"
        is_busy_displaying = False
    
    threading.Thread(target=task, daemon=True).start()

# --- EYE ASPECT RATIO FUNCTION ---
def eye_aspect_ratio(eye_points):
    """Calculate EAR from 6 landmark points"""
    # Vertical distances
    A = dist.euclidean(eye_points[1], eye_points[5])
    B = dist.euclidean(eye_points[2], eye_points[4])
    # Horizontal distance
    C = dist.euclidean(eye_points[0], eye_points[3])
    # EAR formula
    ear = (A + B) / (2.0 * C)
    return ear

# --- MAIN ENGINE (Pi 4 Optimized) ---
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)  # Cap FPS for stability
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer lag

# --- WINDOW SETUP (MEDIUM SIZE) ---
window_name = "Attendance System"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(window_name, 800, 600) 

last_attendance_time = {}
blink_counters = {}  # Track consecutive low-EAR frames per person
blink_detected = {}  # Track if person has blinked (proven real)
fast_blink_warned = {}  # Track if we warned about fast blink
frame_count = 0
camera_error_shown = False

# LCD State Tracking
lcd_state = "ready"  # States: "ready", "blink_prompt", "marking"
lcd_state_name = ""  # Track which person triggered the state
last_lcd_message_time = time.time()  # Debounce LCD updates
LCD_MESSAGE_HOLD_TIME = 2.0  # Minimum seconds to display a message before reset

lcd_display("SYSTEM READY", "Show your face")

while True:
    ret, frame = cap.read()
    if not ret:
        if not camera_error_shown and not is_busy_displaying:
            lcd_show_error("Camera Failed")
            camera_error_shown = True
            print("[ERROR] Camera read failed")
        continue  # Keep trying instead of breaking

    frame_count += 1
    face_found_this_frame = False  # Track if we found a recognized face
    
    if frame_count % PROCESS_EVERY_N_FRAMES == 0:
        # Resize using Pi 4 optimized scale factor
        small = cv2.resize(frame, (0, 0), fx=FACE_SCALE_FACTOR, fy=FACE_SCALE_FACTOR)
        
        # Ensure the image is valid for face_recognition (must be 8-bit RGB)
        if small is None or small.size == 0:
            continue
        if small.dtype != np.uint8:
            small = small.astype(np.uint8)
        # Handle BGRA (4-channel) frames from some Windows cameras
        if len(small.shape) == 2:
            # Grayscale - convert to BGR first
            small = cv2.cvtColor(small, cv2.COLOR_GRAY2BGR)
        elif small.shape[2] == 4:
            # BGRA - drop the alpha channel
            small = cv2.cvtColor(small, cv2.COLOR_BGRA2BGR)
        
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb, model="hog")
        encs = face_recognition.face_encodings(rgb, face_locations)
        landmarks = face_recognition.face_landmarks(rgb, face_locations)

        for i, (enc, loc) in enumerate(zip(encs, face_locations)):
            dists = face_recognition.face_distance(data["encodings"], enc)
            idx = np.argmin(dists)
            
            if dists[idx] < 0.5:
                full_info = data["names"][idx]
                name = full_info.split("_")[3] if "_" in full_info else full_info
                face_found_this_frame = True
                
                # --- LIVENESS DETECTION (EAR-based blink) ---
                is_real = False
                if ENABLE_LIVENESS and i < len(landmarks):
                    lm = landmarks[i]
                    if 'left_eye' in lm and 'right_eye' in lm:
                        left_eye = lm['left_eye']
                        right_eye = lm['right_eye']
                        
                        # Calculate EAR for both eyes
                        left_ear = eye_aspect_ratio(left_eye)
                        right_ear = eye_aspect_ratio(right_eye)
                        avg_ear = (left_ear + right_ear) / 2.0
                        
                        # Initialize counters if needed
                        if name not in blink_counters:
                            blink_counters[name] = 0
                            blink_detected[name] = False
                            fast_blink_warned[name] = False
                        
                        # Check if eyes are closed (EAR below threshold)
                        if avg_ear < EYE_AR_THRESH:
                            blink_counters[name] += 1
                        else:
                            # Check blink duration
                            if blink_counters[name] >= EYE_AR_CONSEC_FRAMES:
                                # Valid slow blink detected
                                blink_detected[name] = True
                                fast_blink_warned[name] = False
                                print(f"[LIVENESS] Valid blink detected for {name} (EAR: {avg_ear:.2f}, frames: {blink_counters[name]})")
                            elif blink_counters[name] > 0 and blink_counters[name] < EYE_AR_MIN_FRAMES:
                                # Too fast blink - warn user
                                if not fast_blink_warned.get(name, False) and not is_busy_displaying:
                                    lcd_show_blink_slowly()
                                    fast_blink_warned[name] = True
                                    print(f"[LIVENESS] Fast blink detected for {name}, need slower blink")
                            blink_counters[name] = 0
                        
                        is_real = blink_detected.get(name, False)
                        
                        # Show "Now Blink!" prompt when face detected but not yet blinked
                        if not is_real and not is_busy_displaying and lcd_state == "ready":
                            lcd_display("FACE DETECTED", "Blink Slowly!")
                            lcd_state = "blink_prompt"
                            lcd_state_name = name
                            last_lcd_message_time = time.time()  # Track when message was shown
                            print(f"[LCD] Prompting {name} to blink slowly")
                else:
                    is_real = True  # Skip liveness if disabled

                # MARK ATTENDANCE
                if is_real and not is_busy_displaying:
                    now = datetime.now()
                    
                    # Check cooldown
                    if name in last_attendance_time:
                        elapsed = (now - last_attendance_time[name]).total_seconds()
                        if elapsed < COOLDOWN_SECONDS:
                            # Still in cooldown - show remaining time
                            remaining_mins = int((COOLDOWN_SECONDS - elapsed) / 60)
                            lcd_show_cooldown_threaded(name, remaining_mins)
                            lcd_state = "cooldown"
                            blink_detected[name] = False  # Reset blink
                            fast_blink_warned[name] = False
                            print(f"[COOLDOWN] {name} already marked, {remaining_mins}m remaining")
                            continue
                    
                    # Mark attendance
                    last_attendance_time[name] = now
                    blink_detected[name] = False  # Reset for next time
                    fast_blink_warned[name] = False
                    lcd_state = "marking"
                    
                    # Save to CSV and Firebase
                    display_name = mark_attendance(full_info)
                    print(f"[SUCCESS] Marked {display_name}")
                    lcd_show_marked_threaded(display_name)
        
        # If no face found this frame and we were prompting for blink, go back to ready
        # Only reset if the message has been displayed long enough (prevents flicker)
        time_since_message = time.time() - last_lcd_message_time
        if not face_found_this_frame and lcd_state == "blink_prompt" and not is_busy_displaying and time_since_message > LCD_MESSAGE_HOLD_TIME:
            lcd_display("SYSTEM READY", "Show your face")
            lcd_state = "ready"
            lcd_state_name = ""

    cv2.imshow(window_name, frame)
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):  # Shutdown
        if LCD_ENABLED and lcd:
            lcd.clear()
            lcd.cursor_pos = (0, 0)
            lcd.write_string("SHUTTING DOWN...".center(LCD_COLS))
            lcd.cursor_pos = (1, 0)
            lcd.write_string("Please wait".center(LCD_COLS))
            time.sleep(2)
        break
    
    elif key == ord('r'):  # Reboot
        if LCD_ENABLED and lcd:
            lcd.clear()
            lcd.cursor_pos = (0, 0)
            lcd.write_string("REBOOTING...".center(LCD_COLS))
            lcd.cursor_pos = (1, 0)
            lcd.write_string("Please wait".center(LCD_COLS))
            time.sleep(2)
        # Release resources before reboot
        cap.release()
        cv2.destroyAllWindows()
        if LCD_ENABLED and lcd:
            lcd.clear()
            lcd.cursor_pos = (0, 0)
            lcd.write_string("SYSTEM READY".center(LCD_COLS))
            lcd.cursor_pos = (1, 0)
            lcd.write_string("Show your face".center(LCD_COLS))
        # Reset tracking variables for fresh start
        last_attendance_time.clear()
        blink_counters.clear()
        blink_detected.clear()
        fast_blink_warned.clear()
        lcd_state = "ready"
        frame_count = 0
        # Re-initialize camera
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, 600)
        continue

cap.release()
cv2.destroyAllWindows()
if LCD_ENABLED and lcd:
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string("GOODBYE!".center(LCD_COLS))
    time.sleep(1)
    lcd.clear()
    if not LCD_POWER_SAVE:
        lcd.backlight_enabled = False  # Turn off when exiting