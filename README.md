# 🎓 Smart IoT Cloud-Integrated Attendance System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/React-Vite-61DAFB.svg?logo=react)](https://reactjs.org/)
[![Firebase](https://img.shields.io/badge/Firebase-Realtime%20Database-FFCA28.svg?logo=firebase)](https://firebase.google.com/)

---

## 📖 Abstract
Welcome to the **Smart IoT Attendance System**, an enterprise-grade, edge-to-cloud facial recognition ecosystem explicitly engineered for IoT hardware like the Raspberry Pi. Moving beyond traditional attendance methods, this project bridges advanced localized machine learning, real-time cloud synchronization, bidirectional remote hardware control, and live streaming IoT telemetry into one cohesive platform.

This document serves as the comprehensive technical foundation, detailing everything from high-level architecture down to the individual thread and socket levels, perfect for project documentation, formal presentations, and developer onboarding.

---

## ✨ Comprehensive Feature Matrix

### 📍 Edge Computing (Raspberry Pi / PC Node)
- **High-Speed Facial Recognition:** Utilizes powerful libraries (Dlib & OpenCV) to accurately map distances between 128 unique facial landmarks in milliseconds.
- **Liveness Detection (Anti-Spoofing):** Deeply integrates an Eye Aspect Ratio (EAR) algorithm targeting 6 specific ocular landmarks. The system demands a physical, human eye blink to log attendance, mathematically eliminating proxy attacks via photographs or mobile screens.
- **Hardware Telemetry Streaming:** A continuous background daemon polls the Pi's CPU load, internal thermal temperature, and RAM consumption, streaming it live directly to the cloud.
- **Peripheral Integration:** Fully supports local hardware outputs, specifically driving an I2C 16x2 LCD Panel to provide instant, physical visual feedback to the student scanning their face.
- **Offline Data Failsafe:** Operates reliably even when the internet completely drops. All attendance logs are perpetually synced to a local `attendance_log.csv` and pushed securely to the cloud once the connection is restored.

### 📍 The Attendance Brain (Cloud AI Training)
- **Asynchronous Processing:** Neural network compilation is famously resource-heavy. Forcing the Pi to train models locally freezes the live camera feed. Instead, image data is securely transmitted to a remote environment (The Brain).
- **Centralized Model Generation:** A Python server hosted on Render processes these raw captured images into a dense mathematical array (`encodings.pickle`). 
- **Scalable Distribution:** Multiple edge hardware nodes across an entire campus or building can seamlessly download the exact same, freshly trained AI model simultaneously, meaning a student enrolled at "Gate A" is instantly recognized at "Gate B".

### 📍 The Command Dashboard (React App)
- **Real-Time Data Streams:** Instantly displays new attendance records appearing physically at the Edge Node without requiring page refreshes, powered by bi-directional WebSocket connections via Firebase.
- **Remote IoT Control (Bi-directional):** Administrators can single-click "Enroll Face" from the web browser. The dashboard transmits a command payload that explicitly intercepts the Pi's active processes, securely forcing it into enrollment mode from thousands of miles away.
- **Analytical Reporting:** Computes complex historical data, showcasing global class attendance rates, individual profiles, and detailed weekly/monthly metrics.
- **Live Device Monitoring:** An interactive widget visually displays the live stream of the Pi's hardware telemetry (CPU/RAM/Temp), acting as a DevOps health monitor for deployed headless hardware.

---

## 🎯 Deep-Dive System Architecture

The ecosystem operates efficiently across a tightly integrated 4-tier pipeline:

1. **Tier 1: The Edge Device (Hardware Sentry)**: 
   - *Role:* The physical outpost.
   - *Flow:* Manages the camera module hardware, runs local face matching algorithms securely on the edge using a pre-downloaded `.pickle` ML model, verifies physical liveness via eye aspect ratios, and broadcasts its internal diagnostic telemetry.

2. **Tier 2: The Cloud Nervous System (Firebase Realtime Database)**:
   - *Role:* The ultra-low latency transaction bridge.
   - *Flow:* Connects the physical edge device, the web dashboard, and the backend cloud server. It handles JSON state synchronization rapidly, manages remote command dispatch queues, and structures real-time database endpoints.

3. **Tier 3: The Attendance Brain (Render Remote ML Engine)**:
   - *Role:* The heavy-lifting compiler.
   - *Flow:* Awoken only when a new student needs to be enrolled. It compiles novel facial encodings from raw images asynchronously natively in the cloud, protecting the edge device from CPU limits, thermal throttling, or dropping live video frames. 

4. **Tier 4: The React Dashboard (Admin Portal)**:
   - *Role:* The human-readable abstraction layer.
   - *Flow:* A responsive, Vite-powered single-page application. Features extensive state-managed student profiles, data visualizations, and the UI hooks needed to remotely manipulate the physical edge hardware.

---

## ⚙️ How the Complex Pipeline Works (Step-by-Step)

### Scenario A: Normal Daily Operation (The Master Node)
The core edge script (`3_main_attendance.py`) runs perpetually on the edge device as a multi-threaded supervisor.
1. **Initialization:** Upon system boot, it activates the camera sensor, clears the I2C LCD display, and begins polling the internal telemetry systems.
2. **Detection & Liveness:** Faces are boxed using `HOG` (Histogram of Oriented Gradients). Once a bounding box is established, it maps the eye coordinates specifically, calculating the EAR. The loop intentionally halts attendance approval until an EAR drop (a physical blink) is mathematically proven.
3. **Identification & Cloud Push:** Upon blink verification, the encoding is checked against the local knowledge base. The system explicitly prevents double-logging (via enforced time-outs), appends the record locally to a CSV matrix, and instantly fires a timestamped `"Present"` node into Firebase.
4. **Physical Feedback:** The I2C connected LCD securely lights up emitting a "Success" message coupled with the recognized student's name, while parent alert integrations (like WhatsApp) can be triggered from the backend.

### Scenario B: Remote Enrollment (The Traffic Controller)
Managing IoT edge devices is best done without plugging in external mice or keyboards ("headless operation"). We engineered a robust bi-directional interceptor for adding new system users:
1. **Trigger:** An administrator clicks **"Enroll Face"** on the React web node.
2. **Payload Dispatch:** The web app crafts and transmits a JSON action payload to the Firebase `/SystemCommands` node (e.g., `mode: "enroll"`, `studentId: "105"`).
3. **Interception:** The Master Script (`3_main_attendance.py`), constantly listening to the Firebase command node, receives the payload in milliseconds.
4. **Hardware Hand-off:** It safely pauses the live attendance scanning loop, explicitly releases the hardware camera module (`cv2.VideoCapture.release()`), and executes `1_capture_faces.py` as an entirely independent background subprocess.
5. **Data Gathering:** `1_capture_faces.py` quietly gathers 20 training pictures directly utilizing the hardware camera under the newly provided student ID. 
6. **Cloud Training:** Once complete, the edge updates Firebase. The **Attendance Brain** on Render picks up the batched images, constructs a new neural network model mapping, and updates the central `.pickle` registry.
7. **Resumption:** The Master Script downloads this updated AI model, seamlessly re-engages the camera process, and gracefully resumes live student monitoring. 

---

## 🛠 File & Directory Map Definition

### Edge Node Base Directory (`/data_set/`)
- `3_main_attendance.py`: The system's Master Node. Handles video loops, liveness limits, threads hardware telemetry, intercepts cloud commands, and drives the I2C LCD screen.
- `1_capture_faces.py`: The headless face capturer. Gatherer of the 20 sequential facial training pictures.
- `2_encode_faces.py`: The manual local encoder (legacy/backup to the Cloud Attendance Brain).
- `push_to_firebase.py`: A dedicated script defining the explicit data structures injected into the Cloud Nervous system.
- `encodings.pickle`: The local trained AI Knowledge base ("The Brain").
- `attendance_log.csv` & `students_db.csv`: The local offline resilient spreadsheet-based fallbacks.
- `.env`: Contains hyper-local secrets for the Pi hardware.

### Admin Dashboard Base Directory (`/dashboard/`)
- `src/App.jsx`: The foundational React router and core layout encapsulator.
- `src/EnrollStudentButton.jsx`: Handles the UI and complex REST/Firebase logic for triggering remote device enrollment complete with real-time UI loading and success states.
- `src/StudentProfile.jsx`: Advanced UI components serving algorithmic charts and logic specifically designed for historical representation.
- `src/HardwareTelemetry.jsx`: Acts as the visual receiver widget for the Edge Node's live CPU/RAM streaming.
- `src/firebase.js`: Configures the initialization and auth logic specifically for the public-facing React interactions.

---

## 🚀 Environment Setup & Initial Installation

### 1. The Cloud Pre-Requisites
Ensure you possess your Firebase `serviceAccountKey.json` authentication token and have securely placed it inside the `/data_set/` folder.
> ⚠️ **SECURITY WARNING:** `serviceAccountKey.json` gives full admin IAM access to your Firebase backend. **NEVER** commit or upload this file to GitHub or any public space. It is explicitly included in `.gitignore` by default to prevent catastrophic security breaches.

### 2. Edge Device Startup (Raspberry Pi/PC)
Access your hardware terminal and install the critical Machine Learning arrays:
```bash
cd data_set
pip install -r requirements.txt
```
*(Dependencies explicitly include: `opencv-python`, `face_recognition`, `firebase_admin`, `dlib`, `scipy`, `psutil`, `RPLCD`)*

Initialize the Master edge daemon:
```bash
python 3_main_attendance.py
```
*(System execution requires an active webcam payload and at least 1 verified user inside `encodings.pickle`.)*

### 3. Dashboard Web Application Startup
Open an independent terminal specifically for the React administration dashboard, mapping node dependencies:
```bash
cd dashboard
npm install
npm run dev
```
Navigate to the provided `localhost` pipeline specifically spawned by Vite to interact dynamically with your Edge Device and Cloud Nervous System.

---

## 🛡 Security Protocols (Firebase)

Because the React frontend interacts dynamically via public configuration (`firebase.js`), the architecture strictly necessitates customized Firebase Security Rules. You must ensure that only authorized, authenticated application layers can write configuration edits or delete historical attendance nodes, ultimately securing against malicious injection.

---
*The ecosystem is now fully integrated. Step confidently into the camera frame, physically blink, and witness exactly how your hardware, cloud architecture, and edge machine learning harmonize in real-time.*

---

## 📐 Algorithms

This section documents the core algorithms implemented in the Smart IoT Attendance System, suitable for formal academic documentation.

---

### Algorithm 1: Face Detection Using HOG (Histogram of Oriented Gradients)

**Used in:** `3_main_attendance.py`, `1_capture_faces.py`, `2_encode_faces.py`

**Purpose:** Locates the bounding box of human faces within a video frame before recognition is applied.

```
Algorithm: HOG-Based Face Detection
Input  : Video frame (RGB image)
Output : List of face bounding box coordinates [(top, right, bottom, left), ...]

Step 1: Capture raw frame from camera (640×480 @ 30 FPS)
Step 2: Scale down frame by factor 0.3 (Pi-optimized) to reduce computation
Step 3: Convert scaled frame from BGR color space to RGB
Step 4: Apply face_recognition.face_locations(frame, model="hog")
        a. Compute HOG descriptor — gradient magnitudes and orientations
           across 8×8 pixel cells in the image
        b. Group cells into 16×16 blocks and normalize contrast
        c. Pass HOG feature vector to a pre-trained Linear SVM classifier
        d. Apply sliding window at multiple scales (image pyramid)
        e. Apply Non-Maximum Suppression (NMS) to remove overlapping detections
Step 5: Return list of detected face bounding boxes
Step 6: Scale bounding box coordinates back to original frame dimensions
        (divide by scale factor 0.3)
Step 7: Draw rectangle overlays on original frame for visual display
```

**Complexity:** O(W × H) per frame where W = width, H = height after scaling.

---

### Algorithm 2: Face Recognition Using 128-Dimensional Encoding

**Used in:** `3_main_attendance.py`, `2_encode_faces.py`

**Purpose:** Identifies a detected face by comparing its mathematical encoding against a pre-trained knowledge base (`.pickle` file).

```
Algorithm: Deep Metric Learning Face Recognition
Input  : RGB face image patch, known_encodings[], known_names[]
Output : Recognized person's name or "Unknown"

--- ENCODING PHASE (2_encode_faces.py) ---
Step 1: Load training images from /dataset/<Year_Section_Roll_Name>/ folders
Step 2: For each image:
        a. Open image with PIL and force convert to RGB (removes EXIF artifacts)
        b. Convert to NumPy array
        c. Detect face locations using HOG (Algorithm 1)
        d. Pass detected face region through a pre-trained ResNet-34 deep
           neural network (dlib's face_recognition_model_v1)
        e. Extract a 128-dimensional floating-point feature vector (encoding)
           that uniquely represents the face geometry
        f. Append (encoding, name) pair to known_encodings, known_names lists
Step 3: Serialize encodings to encodings.pickle using Python pickle module

--- RECOGNITION PHASE (3_main_attendance.py) ---
Step 4: Load encodings.pickle into memory on startup
Step 5: Sync with Cloud Brain API (Render) — merge cloud + local encodings
        a. Cloud encodings overwrite local entries of the same person
Step 6: For each detected face in live frame:
        a. Compute 128-D encoding of the detected face region
        b. Calculate Euclidean distance between query encoding and every
           known encoding:
              distance = sqrt( sum((enc_i - known_enc_j)^2) )
        c. Find minimum distance index: idx = argmin(distances)
        d. If min_distance < 0.5 threshold → Identity confirmed
           Else → Label as "Unknown"
Step 7: Return full_info = known_names[idx] (format: Year_Section_Roll_Name)
```

**Threshold:** Distance < 0.5 indicates a match (tuned for accuracy vs. false positive balance).

---

### Algorithm 3: Eye Aspect Ratio (EAR) Liveness Detection

**Used in:** `3_main_attendance.py`

**Purpose:** Prevents proxy attacks (photos, videos, printed faces) by mathematically verifying a real physical eye blink before logging attendance.

```
Algorithm: EAR Anti-Spoofing Liveness Verification
Input  : 68-point facial landmark coordinates for recognized face
Output : Boolean is_real (True = confirmed live person, False = potential spoof)

Constants:
  EYE_AR_THRESH       = 0.32  (EAR value below which eye is "closed")
  EYE_AR_CONSEC_FRAMES = 3   (minimum consecutive closed frames for valid blink)
  EYE_AR_MIN_FRAMES    = 2   (minimum frames to avoid false rapid blinks)

Step 1: Extract 6 landmark points for each eye from dlib's 68-point detector:
        Left Eye  → landmarks[42:48]
        Right Eye → landmarks[36:42]

Step 2: For each eye, compute Eye Aspect Ratio:
        Let P1-P6 be the 6 eye landmark coordinates:
          A = ||P2 - P6||  (vertical distance, upper-inner to lower-inner)
          B = ||P3 - P5||  (vertical distance, upper-outer to lower-outer)
          C = ||P1 - P4||  (horizontal distance, corner to corner)

          EAR = (A + B) / (2.0 × C)

        Note: EAR ≈ 0.3 when eye is open, EAR ≈ 0.0 when eye is closed

Step 3: Compute average EAR:
        avg_EAR = (left_EAR + right_EAR) / 2.0

Step 4: Per-frame state machine for person:
        IF avg_EAR < EYE_AR_THRESH:
            blink_counter[name] += 1       ← eye is closing
        ELSE:
            IF blink_counter[name] >= EYE_AR_CONSEC_FRAMES:
                blink_detected[name] = True ← valid slow blink confirmed
            ELSE IF blink_counter[name] > 0 AND < EYE_AR_MIN_FRAMES:
                Warn user: "Blink Slowly"   ← blink too fast, rejected
            blink_counter[name] = 0         ← reset counter on eye open

Step 5: is_real = blink_detected[name]
Step 6: If is_real == True → proceed to attendance marking
        Reset blink_detected[name] = False for next session
```

**Security note:** Static images have a fixed EAR value that never drops below threshold — making this algorithm mathematically immune to photograph-based proxy attendance.

---

### Algorithm 4: Attendance Logging with Duplicate Prevention

**Used in:** `3_main_attendance.py`

**Purpose:** Marks attendance exactly once per student per session, saving to both local CSV and Firebase cloud with a 2-hour cooldown enforced.

```
Algorithm: Deduplication-Safe Attendance Marking
Input  : full_info (Year_Section_Roll_Name string), is_real (Boolean)
Output : Attendance record written to CSV + Firebase

Constants:
  COOLDOWN_SECONDS = 7200  (2 hours between permitted marks)

Step 1: Parse full_info string by "_" delimiter:
        year = parts[0], section = parts[1],
        roll_no = parts[2], name = parts[3]

Step 2: Check cooldown map:
        IF name IN last_attendance_time:
            elapsed = (now - last_attendance_time[name]).total_seconds()
            IF elapsed < COOLDOWN_SECONDS:
                remaining = COOLDOWN_SECONDS - elapsed
                Display cooldown message on LCD
                RETURN (skip logging)

Step 3: Record timestamp:
        timestamp = datetime.now()
        time_str = HH:MM:SS
        date_str = YYYY-MM-DD
        record_key = f"{roll_no}_{date_str}_{time_str}"

Step 4: Write to local CSV (offline failsafe):
        - File: attendance_log.csv
        - Columns: [Name, RollNo, Year, Section, Time, Date, Status]
        - Append row: [name, roll_no, year, section, time_str, date_str, "Present"]

Step 5: Push to Firebase Realtime Database (cloud sync):
        - Path: /attendance/{date_str}/{record_key}
        - Payload: { name, rollNo, year, section, time, date,
                     status: "Present", timestamp: Unix epoch }

Step 6: Update last_attendance_time[name] = now
Step 7: Trigger LCD animation: "ATTENDANCE MARKED → Name → SYSTEM READY"
Step 8: Reset blink state for person
```

---

### Algorithm 5: Remote Enrollment Pipeline

**Used in:** `3_main_attendance.py`, `1_capture_faces.py`

**Purpose:** Allows administrators to enroll a new student from the web dashboard without physical access to the edge device, using a bidirectional Firebase command channel.

```
Algorithm: Headless IoT Remote Enrollment
Input  : Admin clicks "Enroll Face" on React Dashboard
Output : New student registered in encodings.pickle and Firebase

--- DASHBOARD SIDE ---
Step 1: Admin fills enrollment form (Year, Section, RollNo, Name)
Step 2: Dashboard writes command payload to Firebase /SystemCommands:
        { mode: "enroll", status: "pending",
          target_name: "Year_Section_RollNo_Name" }

--- EDGE DEVICE SIDE (3_main_attendance.py) ---
Step 3: Firebase listener (system_command_handler) detects payload change
Step 4: Set system_mode = "enroll", capture target_name
Step 5: Safely release camera: cap.release() + cv2.destroyAllWindows()
Step 6: Launch capture subprocess:
        subprocess.run([python, "1_capture_faces.py", target_name])

--- FACE CAPTURE (1_capture_faces.py) ---
Step 7: Parse target_name to extract Year, Section, RollNo, Name
Step 8: Security Check 1 — Roll Number Conflict:
        Scan /dataset/ folders for matching RollNo
        IF conflict found → ABORT enrollment
Step 9: Security Check 2 — Duplicate Face Detection:
        Compute encoding of camera frame
        Compare against all known_encodings
        IF min_distance < 0.4 → ABORT (face already registered)
Step 10: Capture 20 training images:
         WHILE count < 20:
             Read frame from camera
             Detect face using Haar Cascade (scaleFactor=1.2,
             minNeighbors=7, minSize=100×100)
             IF face detected AND time since last capture > 0.3s:
                 Save clean frame (without overlay) to
                 /dataset/{folder_name}/{name}_{count}.jpg
                 count += 1
Step 11: Upload all 20 images to Cloudinary CDN:
         For each image → cloudinary.uploader.upload()
         Store secure_url[] and public_id[] in Firebase /Students/{roll_no}
Step 12: Save student record to students_db.csv

--- CLOUD BRAIN (Render API) ---
Step 13: Edge signals completion → Main script calls sync_brain_from_api()
Step 14: Render downloads images from Cloudinary, runs 2_encode_faces.py logic
         Generates updated encodings.pickle with new 128-D encoding
Step 15: Edge downloads new encodings.pickle, merges with local data

--- CLEANUP & RESUME ---
Step 16: Auto-delete raw images from Cloudinary (privacy protection)
Step 17: Update Firebase /SystemCommands: { mode: "attendance", status: "completed" }
Step 18: Re-initialize camera + resume live attendance loop
```

---

### Algorithm 6: Hardware Telemetry Streaming

**Used in:** `3_main_attendance.py`

**Purpose:** Continuously monitors and streams Raspberry Pi hardware health metrics to Firebase for live dashboard display.

```
Algorithm: Concurrent IoT Telemetry Daemon
Input  : System hardware sensors (CPU, RAM, Temperature)
Output : Real-time metrics pushed to Firebase every 3 seconds

Note: Runs in a separate daemon thread — does not block the camera loop.

Step 1: Record startup_time = time.time()
Step 2: LOOP FOREVER:
        a. cpu_usage  = psutil.cpu_percent(interval=1)  ← 1-sec CPU sample
        b. ram        = psutil.virtual_memory()
           ram_pct    = ram.percent
           ram_used   = ram.used / 1024³ (GB)
           ram_total  = ram.total / 1024³ (GB)
        c. temp = read /sys/class/thermal/thermal_zone0/temp / 1000.0
           (Fallback: psutil.sensors_temperatures() for non-Pi systems)
        d. uptime_secs = time.time() - startup_time
           Format: "{days}d {hours}h {mins}m"
        e. Push to Firebase /SystemHealth/Pi4:
           { cpu_temp, cpu_usage, ram_usage, ram_used_gb,
             ram_total_gb, uptime, status: "Online", timestamp }
        f. sleep(3 seconds)
        g. On exception: sleep(5 seconds) and retry
```

