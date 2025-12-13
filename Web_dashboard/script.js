import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getDatabase, ref, onValue } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";
import { firebaseConfig } from './config.js';

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

// References
const studentsRef = ref(db, 'students');
const attendanceRef = ref(db, 'attendance');

// State
let registeredStudents = {}; // Map: RollNo -> StudentData
let attendanceLogs = [];     // List of today's logs

// DOM Elements
const tableBody = document.getElementById("attendanceBody");
const dateSelector = document.getElementById("dateSelector");
const searchBox = document.getElementById("searchBox");
const labSelector = document.getElementById("labSelector"); // For filtering by year/section later if needed

// Initialize Date to Today
dateSelector.valueAsDate = new Date();

// --- 1. FETCH ALL REGISTERED STUDENTS ---
onValue(studentsRef, (snapshot) => {
    const data = snapshot.val();
    if (data) {
        registeredStudents = data; // e.g., {'501': {name: 'Samba', ...}}
        refreshDashboard();
    }
});

// --- 2. FETCH ATTENDANCE LOGS ---
onValue(attendanceRef, (snapshot) => {
    const data = snapshot.val();
    attendanceLogs = []; // Reset logs
    if (data) {
        // Convert Firebase object to array
        attendanceLogs = Object.values(data);
    }
    refreshDashboard();
});

// --- 3. CORE LOGIC: MERGE & RENDER ---
function refreshDashboard() {
    tableBody.innerHTML = "";
    
    const selectedDate = dateSelector.value;
    const searchTerm = searchBox.value.toLowerCase();
    
    // Counters
    let stats = { total: 0, secA: 0, secB: 0, absent: 0 };

    // Loop through EVERY registered student (To show Absentees)
    Object.values(registeredStudents).forEach(student => {
        // Check if this student is present today
        const attendanceRecord = attendanceLogs.find(log => 
            log.roll_no === student.roll_no && log.date === selectedDate
        );

        let status = "Absent";
        let timeIn = "--:--";
        let rowClass = "absent-row"; // For CSS styling

        if (attendanceRecord) {
            status = "Present";
            timeIn = attendanceRecord.time;
            rowClass = "present-row";
        }

        // Filter Logic (Search)
        const searchString = (student.name + student.roll_no).toLowerCase();
        if (!searchString.includes(searchTerm)) return;

        // Update Stats
        if (status === "Present") {
            stats.total++;
            if (student.section === 'A') stats.secA++;
            if (student.section === 'B') stats.secB++;
        } else {
            stats.absent++;
        }

        // Create Row
        const row = document.createElement("tr");
        // Add red background for absent, white for present
        row.style.backgroundColor = status === "Absent" ? "#fff0f0" : "#ffffff";
        
        row.innerHTML = `
            <td><b>${student.roll_no}</b></td>
            <td>${student.name}</td>
            <td>${student.year} - ${student.section}</td>
            <td>${timeIn}</td>
            <td>${selectedDate}</td>
            <td>
                <span class="status-badge ${status.toLowerCase()}">
                    ${status === "Present" ? "✅ Present" : "❌ Absent"}
                </span>
            </td>
        `;
        
        // Put Present students at top, Absent at bottom
        if (status === "Present") {
            tableBody.prepend(row);
        } else {
            tableBody.appendChild(row);
        }
    });

    // Update UI Cards
    document.getElementById("totalCount").innerText = stats.total;
    document.getElementById("countA").innerText = stats.secA;
    document.getElementById("countB").innerText = stats.secB;
    
    // Update Empty State
    document.getElementById("emptyState").style.display = 
        Object.keys(registeredStudents).length > 0 ? "none" : "block";
}

// Event Listeners
dateSelector.addEventListener("change", refreshDashboard);
searchBox.addEventListener("input", refreshDashboard);