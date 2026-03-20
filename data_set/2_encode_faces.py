import face_recognition
import pickle
import os
import cv2
import numpy as np
from PIL import Image  # Added for strict standardization

# --- PATH CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(script_dir, "dataset")

if not os.path.exists(DATASET_DIR):
    print(f"[ERROR] Could not find 'dataset' folder at {DATASET_DIR}")
    exit()

ENCODINGS_FILE = os.path.join(script_dir, "encodings.pickle")
known_encodings = []
known_names = []

print(f"[INFO] Processing images...")

for root, dirs, files in os.walk(DATASET_DIR):
    for file in files:
        if file.lower().endswith((".jpg", ".png", ".jpeg")):
            path = os.path.join(root, file)
            name = os.path.basename(root)

            try:
                # STEP 1: Open with PIL and force convert to RGB
                # This fixes the "8bit" error by stripping hidden profiles
                pil_image = Image.open(path).convert('RGB')
                
                # STEP 2: Convert to a format face_recognition understands
                image_array = np.array(pil_image)
                
                # STEP 3: Detect and Encode
                face_locations = face_recognition.face_locations(image_array, model="hog")
                
                if len(face_locations) > 0:
                    face_encodings = face_recognition.face_encodings(image_array, face_locations)
                    for encoding in face_encodings:
                        known_encodings.append(encoding)
                        known_names.append(name)
                    print(f"[OK] {name}/{file}")
                else:
                    print(f"[SKIP] No face found in: {file}")

            except Exception as e:
                print(f"[ERROR] Failed on {file}: {e}")

print("\n[INFO] Saving encodings...")
data = {"encodings": known_encodings, "names": known_names}
with open(ENCODINGS_FILE, "wb") as f:
    f.write(pickle.dumps(data))

print(f"[SUCCESS] Total unique students: {len(set(known_names))}")