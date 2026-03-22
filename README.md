# Smart IoT Cloud-Integrated Attendance System

Welcome to the **Smart IoT Attendance System**, an advanced, edge-to-cloud face-recognition ecosystem designed specifically for Raspberry Pi hardware. This project transforms a standard Python face recognition script into a robust IoT architecture capable of liveness detection, live hardware telemetry, cloud synchronization, and remote bi-directional control.

---

## 🎯 Architecture Overview

The system operates across three tightly integrated layers:

1. **The Edge Device (Raspberry Pi 4 / PC)**: Executes heavy machine learning models, handles the physical camera hardware, processes live facial frames, and monitors its own system health.
2. **The Cloud Nervous System (Firebase & Render API)**: Firebase Realtime Database acts as an instant bridge connecting the Dashboard and the Edge Device. Render hosts the "Cloud Brain", which compiles robust face encoding models asynchronously to prevent the Pi from freezing during large dataset training.
3. **The React Dashboard**: A specialized web frontend that displays comprehensive student UI cards, attendance analytical charts, live Pi hardware stats, and issues remote master commands.

---

## ⚙️ How the Pipeline Works

### 1. Normal Operation (The Master Node)
The core script is `3_main_attendance.py`. When launched, it initializes an LCD display and begins capturing camera frames:
- **Liveness Detection**: It maps 6 landmark points on a detected face's eyes and calculates an Eye Aspect Ratio (EAR). The system requires a physical blink to prevent photo-spoofing (anti-proxy).
- **Telemetry Thread**: A dedicated background daemon constantly checks the Pi's CPU percentage, internal temperature, and RAM usage, streaming this directly to Firebase every 3 seconds.
- **Attendance Syncing**: When a face is matched and a blink is verified, it locally logs the student and immediately pushes an `"Present"` record timestamp to Firebase, displaying success on the physical LCD.

### 2. Remote Enrollment (The Traffic Controller)
Because Edge devices often run without a keyboard or mouse ("headless"), we use a bi-directional traffic interceptor to add new faces safely:
- A user clicks **"Enroll Face"** on the React Dashboard.
- React fires a small JSON payload to `/SystemCommands` on Firebase (`mode: "enroll"`).
- `3_main_attendance.py` stays subscribed to this node. The millisecond the payload arrives, the Master Script triggers an **Enrollment Interceptor**.
- The Master pauses its attendance loop, releases the physical camera explicitly, and spins up `1_capture_faces.py` as a background subprocess.
- `1_capture_faces.py` parses the target student's name directly from the execution arguments silently capturing 20 training pictures automatically.
- Upon completion, the Master script tells Firebase it finished, triggers an API call to Render to download the newly merged AI "Brain" (`encodings.pickle`), and gracefully re-activates the camera hardware to resume attendance.

---

## 📂 Core Files Explained

### Edge Node Files (`/data_set/`)
- `3_main_attendance.py`: The system's Master Node. Handles video loops, liveness limits, threads hardware telemetry, intercepts cloud commands, and drives the I2C LCD screen.
- `1_capture_faces.py`: The headless face capturer. Can be run manually or triggered by the Master Node to gather 20 sequential facial data pictures for training.
- `encodings.pickle`: The local trained AI "Brain" mapping mathematical representations of faces to student names.
- `attendance_log.csv` & `students_db.csv`: Failsafe local memory. If the internet drops, these CSVs ensure data is securely stored offline.

### Dashboard Files (`/dashboard/`)
- `src/StudentProfile.jsx`: A heavily configured React UI component serving dynamic charts, analytical data calculations (monthly/weekly breakdowns), and the logic specifically tied to firing the remote face enrollment triggers to Firebase.
- `src/firebase.js`: Initializes your Realtime Database hookups for the web client.

---

## 🚀 How to Implement & Run

### 1. Pre-Requisites
Ensure you possess your Firebase `serviceAccountKey.json` authentication token and have placed it neatly inside the `/data_set/` folder.

### 2. Edge Device Setup
Navigate to your edge device folder and install the required machine learning and system libraries:
```bash
cd data_set
pip install -r requirements.txt
```
*(Dependencies usually include `opencv-python`, `face_recognition`, `firebase_admin`, `scipy`, `psutil`, `RPLCD`)*

Run the Master node:
```bash
python 3_main_attendance.py
```
*Note: Make sure your webcam is plugged in and `encodings.pickle` has at least one processed user, or it will auto-sync one from Render.*

### 3. Dashboard Web Setup
Open a secondary terminal, navigate to your frontend, install the Node modules, and launch Vite:
```bash
cd dashboard
npm install
npm run dev
```

The system is now fully live! Step in front of the camera, blink to register, and observe your real-time data seamlessly populating on the dashboard.
