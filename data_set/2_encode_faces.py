import cv2
import face_recognition
import pickle
import os

# --- ROBUST PATH CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

# Search for 'dataset' folder
possible_dataset_paths = [
    os.path.join(script_dir, "dataset"),
    os.path.join(parent_dir, "dataset"),
    os.path.join(script_dir, "../dataset")
]

DATASET_DIR = None
for path in possible_dataset_paths:
    if os.path.exists(path):
        DATASET_DIR = path
        break

if DATASET_DIR is None:
    print(f"[ERROR] Could not find 'dataset' folder.")
    print(f"Checked locations: {possible_dataset_paths}")
    exit()

# Set encodings file path (Next to this script)
ENCODINGS_FILE = os.path.join(script_dir, "encodings.pickle")

known_encodings = []
known_names = []

print(f"[INFO] Found dataset at: {DATASET_DIR}")
print("[INFO] Quantifying faces...")

# Loop over the dataset
for root, dirs, files in os.walk(DATASET_DIR):
    for file in files:
        if file.endswith("jpg") or file.endswith("png"):
            path = os.path.join(root, file)
            name = os.path.basename(root) # Extracts "2_A_501_Name"

            image = cv2.imread(path)
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            boxes = face_recognition.face_locations(rgb, model="hog")
            encodings = face_recognition.face_encodings(rgb, boxes)

            for encoding in encodings:
                known_encodings.append(encoding)
                known_names.append(name)

print("[INFO] Serializing encodings...")
data = {"encodings": known_encodings, "names": known_names}

with open(ENCODINGS_FILE, "wb") as f:
    f.write(pickle.dumps(data))

print(f"[SUCCESS] Training complete. Saved to: {ENCODINGS_FILE}")
print(f"[INFO] Total unique students trained: {len(set(known_names))}")