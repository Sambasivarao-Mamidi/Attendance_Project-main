// Firebase configuration for the Attendance Dashboard
// Uses Firebase Realtime Database to fetch live attendance data

import { initializeApp } from 'firebase/app';
import { getDatabase, ref, onValue, get } from 'firebase/database';

// Firebase project config (attendance-system-2ad29)
const firebaseConfig = {
    apiKey: "AIzaSyDummyKeyForRTDB", // RTDB doesn't need a real API key for public reads
    authDomain: "attendance-system-2ad29.firebaseapp.com",
    databaseURL: "https://attendance-system-2ad29-default-rtdb.asia-southeast1.firebasedatabase.app",
    projectId: "attendance-system-2ad29",
    storageBucket: "attendance-system-2ad29.appspot.com",
    messagingSenderId: "000000000000",
    appId: "1:000000000000:web:0000000000000000000000"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const database = getDatabase(app);

export { database, ref, onValue, get };
