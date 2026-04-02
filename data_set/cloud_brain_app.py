from flask import Flask, send_file, jsonify
import firebase_admin
from firebase_admin import credentials, db
import face_recognition
import numpy as np
from PIL import Image
import urllib.request
import io
import pickle
import os

app = Flask(__name__)

# --- Initialize Firebase ---
# This looks for the JSON file in the same folder during Render deployment
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://attendance-system-2ad29-default-rtdb.asia-southeast1.firebasedatabase.app'
})

@app.route('/', methods=['GET'])
def health_check():
    return "Cloud Brain API is Online!", 200

@app.route('/sync_brain', methods=['GET'])
def sync_brain():
    """Scans Firebase for new images, encodes them, and returns the combined pickle file."""
    try:
        students_data = db.reference('Students').get()
        
        known_encodings = []
        known_names = []
        
        if students_data:
            for student_id, data in students_data.items():
                
                # FIX: Use real year/section from Firebase (set by capture script)
                # instead of hardcoded "0" and "X"
                year = str(data.get('year', '0'))
                section = str(data.get('section', 'X'))
                
                # FIX: Keep spaces in names to match the Pi's folder naming convention
                # The Pi's encoding script uses os.path.basename(root) which preserves spaces
                student_name = data.get('name', 'Unknown')
                
                # Format: Year_Section_RollNo_Name  (must match Pi's folder format exactly)
                formatted_name = f"{year}_{section}_{student_id}_{student_name}"
                
                # SCENARIO 1: Needs Training (Has images, no encoding)
                if 'training_images' in data and 'encoding' not in data:
                    print(f"Training new student: {student_name}")
                    temp_encodings = []
                    
                    for url in data['training_images']:
                        if url:
                            try:
                                # Download from Cloudinary
                                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                                resp = urllib.request.urlopen(req)
                                img_bytes = resp.read()
                                
                                # Apply your PIL RGB fix to prevent 8-bit errors
                                pil_image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
                                image_array = np.array(pil_image)
                                
                                # Detect and Encode
                                face_locations = face_recognition.face_locations(image_array, model="hog")
                                if len(face_locations) > 0:
                                    encodings = face_recognition.face_encodings(image_array, face_locations)
                                    temp_encodings.append(encodings[0])
                            except Exception as e:
                                print(f"Skipping image due to error: {e}")
                    
                    # Save master encoding to Firebase
                    if len(temp_encodings) > 0:
                        master_encoding = np.mean(temp_encodings, axis=0).tolist()
                        db.reference(f'Students/{student_id}').update({'encoding': master_encoding})
                        
                        known_encodings.append(np.array(master_encoding))
                        known_names.append(formatted_name)
                
                # SCENARIO 2: Already Trained (Just grab the existing math)
                elif 'encoding' in data:
                    known_encodings.append(np.array(data['encoding']))
                    known_names.append(formatted_name)

        # Build the final combined Pickle file in memory
        data_dict = {"encodings": known_encodings, "names": known_names}
        pickle_binary = pickle.dumps(data_dict)
        
        print(f"[CLOUD BRAIN] Returning {len(known_names)} faces: {known_names}")
        
        # Send it directly back to the Pi
        return send_file(
            io.BytesIO(pickle_binary),
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name='encodings.pickle'
        )
        
    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Render requires binding to 0.0.0.0 and dynamically assigning the port
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
