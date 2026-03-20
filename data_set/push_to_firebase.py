"""
Push attendance_log.csv data to Firebase Realtime Database.

This script reads the local CSV attendance log and uploads all records
to Firebase, organized by date. It can be run anytime to sync local
data to the cloud.

Usage:
    python push_to_firebase.py
"""

import csv
import os
import sys
import time
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, db

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(script_dir, "serviceAccountKey.json")
log_file = os.path.join(script_dir, "attendance_log.csv")
FIREBASE_URL = "https://attendance-system-2ad29-default-rtdb.asia-southeast1.firebasedatabase.app"

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if not os.path.exists(key_path):
        print(f"[ERROR] Service account key not found: {key_path}")
        sys.exit(1)

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': FIREBASE_URL
            })
        print("[✓] Firebase Connected!")
        return True
    except Exception as e:
        print(f"[✗] Firebase init failed: {e}")
        return False

def read_csv_data():
    """Read attendance records from CSV file"""
    if not os.path.exists(log_file):
        print(f"[ERROR] CSV file not found: {log_file}")
        sys.exit(1)

    records = []
    with open(log_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        for row in reader:
            # Skip empty rows
            if not row or len(row) < 7:
                continue
            
            # Skip header row if present
            if row[0].strip().lower() == 'name':
                continue
            
            try:
                record = {
                    'name': row[0].strip(),
                    'rollNo': row[1].strip(),
                    'year': row[2].strip(),
                    'section': row[3].strip(),
                    'time': row[4].strip(),
                    'date': row[5].strip(),
                    'status': row[6].strip()
                }
                records.append(record)
            except (IndexError, ValueError) as e:
                print(f"[WARNING] Skipping malformed row: {row} - {e}")
                continue

    print(f"[✓] Read {len(records)} records from CSV")
    return records

def push_to_firebase(records):
    """Push all attendance records to Firebase Realtime Database"""
    ref = db.reference('/attendance')
    
    # Group records by date for efficient upload
    by_date = {}
    for record in records:
        date = record['date']
        if date not in by_date:
            by_date[date] = {}
        
        # Create unique key: rollNo_date_time
        time_key = record['time'].replace(':', '-')
        record_key = f"{record['rollNo']}_{date}_{time_key}"
        
        by_date[date][record_key] = {
            'name': record['name'],
            'rollNo': record['rollNo'],
            'year': record['year'],
            'section': record['section'],
            'time': record['time'],
            'date': record['date'],
            'status': record['status'],
            'timestamp': datetime.strptime(
                f"{record['date']} {record['time']}", "%Y-%m-%d %H:%M:%S"
            ).timestamp()
        }
    
    # Also push a students list for the dashboard
    students = {}
    for record in records:
        roll = record['rollNo']
        if roll not in students:
            students[roll] = {
                'name': record['name'],
                'rollNo': roll,
                'year': record['year'],
                'section': record['section']
            }

    total_dates = len(by_date)
    total_records = sum(len(v) for v in by_date.values())
    
    print(f"\n[INFO] Uploading {total_records} records across {total_dates} dates...")
    print("-" * 50)
    
    uploaded = 0
    for i, (date, date_records) in enumerate(sorted(by_date.items()), 1):
        try:
            # Upload all records for this date at once (batch)
            ref.child(date).update(date_records)
            uploaded += len(date_records)
            print(f"  [{i}/{total_dates}] {date}: {len(date_records)} records ✓")
        except Exception as e:
            print(f"  [{i}/{total_dates}] {date}: FAILED - {e}")
    
    # Upload students list
    try:
        db.reference('/students').set(students)
        print(f"\n[✓] Students list uploaded ({len(students)} students)")
    except Exception as e:
        print(f"\n[✗] Students list upload failed: {e}")
    
    print("-" * 50)
    print(f"[✓] Upload complete: {uploaded}/{total_records} records pushed to Firebase")
    
    return uploaded

def main():
    print("=" * 50)
    print("  ATTENDANCE DATA → FIREBASE UPLOADER")
    print("=" * 50)
    print()
    
    # Step 1: Initialize Firebase
    print("[1/3] Connecting to Firebase...")
    if not initialize_firebase():
        sys.exit(1)
    
    # Step 2: Read CSV data
    print("\n[2/3] Reading attendance_log.csv...")
    records = read_csv_data()
    
    if not records:
        print("[WARNING] No records found to upload.")
        sys.exit(0)
    
    # Step 3: Push to Firebase
    print("\n[3/3] Pushing data to Firebase...")
    start_time = time.time()
    uploaded = push_to_firebase(records)
    elapsed = time.time() - start_time
    
    print(f"\n{'=' * 50}")
    print(f"  DONE! {uploaded} records uploaded in {elapsed:.1f}s")
    print(f"  Firebase URL: {FIREBASE_URL}")
    print(f"{'=' * 50}")

if __name__ == "__main__":
    main()
