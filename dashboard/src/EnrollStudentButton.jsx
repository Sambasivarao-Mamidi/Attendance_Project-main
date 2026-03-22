import React, { useState, useEffect } from 'react';
import { ref, set, onValue } from 'firebase/database';
// Make sure to export your Firebase database instance from firebase.js as 'database'
import { database } from './firebase'; 

export default function EnrollStudentButton() {
  const [studentName, setStudentName] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // The Trigger: Handle the button click and write to Firebase
  const handleEnroll = async (e) => {
    e.preventDefault();
    console.log("🚨 Step 1: Button was physically clicked!");
    
    if (!studentName.trim()) {
      console.log("⚠️ Student name is empty, ignoring click.");
      return;
    }

    setIsProcessing(true);
    setSuccessMessage('');

    try {
      const commandsRef = ref(database, 'SystemCommands');
      console.log("🚨 Step 2: Attempting to send data to Firebase...");
      
      set(commandsRef, {
        mode: 'enroll',
        target_name: studentName.trim(),
        status: 'pending'
      })
      .then(() => {
        console.log("✅ Step 3: SUCCESS! Firebase received the data.");
      })
      .catch((error) => {
        console.error("❌ Step 3: FIREBASE REJECTED IT. Error details: ", error);
        setIsProcessing(false);
        alert('Failed to trigger IoT device. Check your connection.');
      });
      
    } catch (err) {
      console.error("❌ Step 2: React crashed before it could even talk to Firebase: ", err);
      setIsProcessing(false);
    }
  };

  // The Listener: Listen for the 'completed' status from the hardware
  useEffect(() => {
    // We only actively listen for completion if we are currently processing
    if (!isProcessing) return;

    const statusRef = ref(database, 'SystemCommands/status');
    
    // Set up the Firebase real-time listener
    const unsubscribe = onValue(statusRef, (snapshot) => {
      const status = snapshot.val();
      
      // Hardware has finished processing
      if (status === 'completed') {
        setIsProcessing(false);
        setSuccessMessage('Face Enrolled Successfully!');
        setStudentName(''); // Reset input field

        // Reset success message after 3 seconds
        setTimeout(() => {
          setSuccessMessage('');
        }, 3000);
      }
    });

    // Cleanup: Properly detach the listener to prevent memory leaks
    return () => unsubscribe();
  }, [isProcessing]);

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-xl shadow-md space-y-4">
      <h2 className="text-xl font-bold text-slate-800">Remote Face Enrollment</h2>
      
      <form className="flex flex-col gap-4">
        {/* The UI: Input Field */}
        <div className="flex flex-col gap-1">
          <label htmlFor="studentName" className="text-sm font-medium text-slate-600">
            Student Name
          </label>
          <input
            id="studentName"
            type="text"
            value={studentName}
            onChange={(e) => setStudentName(e.target.value)}
            disabled={isProcessing}
            autoComplete="off"
            placeholder="e.g. John Doe"
            className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-400"
          />
        </div>

        {/* The UI & Loading State: Enroll Button */}
        <button
          type="button"
          onClick={handleEnroll}
          disabled={isProcessing}
          className="relative flex justify-center items-center w-full px-4 py-2 text-white font-medium bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-75 disabled:cursor-not-allowed transition-all"
        >
          {isProcessing ? (
            <>
              {/* Tailwind CSS spinner */}
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing on Device...
            </>
          ) : (
            'Enroll Face'
          )}
        </button>
      </form>

      {/* The Completion: Success Message */}
      {successMessage && (
        <div className="p-3 mt-4 text-sm font-medium text-green-800 bg-green-100 rounded-lg flex items-center gap-2 animate-pulse">
          <svg className="w-5 h-5 text-green-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
          </svg>
          {successMessage}
        </div>
      )}
    </div>
  );
}
