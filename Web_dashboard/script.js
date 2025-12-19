import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getDatabase, ref, onValue, get } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";
import { firebaseConfig } from './config.js';

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

console.log("[DEBUG] Firebase initialized with config:", firebaseConfig);
console.log("[DEBUG] Database URL:", firebaseConfig.databaseURL);

// References
const studentsRef = ref(db, 'students');
const attendanceRef = ref(db, 'attendance');

console.log("[DEBUG] Students ref path: students");
console.log("[DEBUG] Attendance ref path: attendance");

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

// Function to fetch fresh data from Firebase
async function fetchFirebaseData() {
    try {
        // Fetch students
        const studentsSnapshot = await get(studentsRef);
        if (studentsSnapshot.exists()) {
            registeredStudents = studentsSnapshot.val();
            console.log("[INFO] Students fetched:", Object.keys(registeredStudents).length);
        }
        
        // Fetch attendance
        const attendanceSnapshot = await get(attendanceRef);
        if (attendanceSnapshot.exists()) {
            attendanceLogs = Object.values(attendanceSnapshot.val());
            console.log("[INFO] Attendance fetched:", attendanceLogs.length, "records");
        }
        
        refreshDashboard();
    } catch (error) {
        console.error("[ERROR] Failed to fetch data:", error);
    }
}

// Initial load
fetchFirebaseData();

// Re-fetch every 3 seconds
setInterval(fetchFirebaseData, 3000);

// --- 3. CORE LOGIC: MERGE & RENDER ---
function refreshDashboard() {
    console.log("[DEBUG] refreshDashboard called");
    console.log("[DEBUG] Registered Students:", registeredStudents);
    console.log("[DEBUG] Attendance Logs:", attendanceLogs);
    console.log("[DEBUG] Selected Date:", dateSelector.value);
    console.log("[DEBUG] Total attendance records available:", attendanceLogs.length);
    
    tableBody.innerHTML = "";
    
    const selectedDate = dateSelector.value;
    const searchTerm = searchBox.value.toLowerCase();
    
    // Counters
    let stats = { total: 0, secA: 0, secB: 0, absent: 0 };
    let rowCount = 0;
    
    // Filter attendance for today
    const todayRecords = attendanceLogs.filter(log => log.date === selectedDate);
    console.log(`[DEBUG] Records for ${selectedDate}: ${todayRecords.length}`);

    // Display ALL attendance records for the selected date (multiple entries per student allowed)
    const filteredRecords = todayRecords.filter(log => {
        const searchString = (log.name + log.roll_no).toLowerCase();
        return searchString.includes(searchTerm);
    });

    // Sort by time descending (latest first)
    filteredRecords.sort((a, b) => b.time.localeCompare(a.time));

    // Track unique students marked
    const uniqueStudents = new Set();

    filteredRecords.forEach(log => {
        uniqueStudents.add(log.roll_no);

        // Create Row for EACH attendance entry
        const row = document.createElement("tr");
        row.style.backgroundColor = "#ffffff";
        
        const student = registeredStudents[log.roll_no] || {};
        row.innerHTML = `
            <td><b>${log.roll_no}</b></td>
            <td>${log.name}</td>
            <td>${log.year} - ${log.section}</td>
            <td>${log.time}</td>
            <td>${log.date}</td>
            <td>
                <span class="status-badge present">
                    ✅ Present
                </span>
            </td>
        `;
        
        tableBody.appendChild(row);
        rowCount++;
    });

    // Show absent students only if no records for today
    if (todayRecords.length === 0) {
        Object.values(registeredStudents).forEach(student => {
            const searchString = (student.name + student.roll_no).toLowerCase();
            if (!searchString.includes(searchTerm)) return;

            const row = document.createElement("tr");
            row.style.backgroundColor = "#fff0f0";
            
            row.innerHTML = `
                <td><b>${student.roll_no}</b></td>
                <td>${student.name}</td>
                <td>${student.year} - ${student.section}</td>
                <td>--:--</td>
                <td>${selectedDate}</td>
                <td>
                    <span class="status-badge absent">
                        ❌ Absent
                    </span>
                </td>
            `;
            
            tableBody.appendChild(row);
            rowCount++;
        });
    }

    // Update Stats - count unique students only
    stats.total = uniqueStudents.size;
    uniqueStudents.forEach(rollNo => {
        const student = registeredStudents[rollNo];
        if (student) {
            if (student.section === 'A') stats.secA++;
            if (student.section === 'B') stats.secB++;
        }
    });

    console.log("[DEBUG] Total rows rendered:", rowCount);
    console.log("[DEBUG] Stats:", stats);

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

// Force refresh function
function forceRefresh() {
    console.log("[INFO] Manual refresh triggered!");
    refreshDashboard();
}

// Auto-refresh every 5 seconds to catch new attendance
setInterval(() => {
    console.log("[DEBUG] Auto-refresh polling triggered");
    refreshDashboard();
}, 5000);