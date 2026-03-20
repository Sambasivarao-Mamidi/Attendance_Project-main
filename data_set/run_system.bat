@echo off
title Face Registration System
color 0B

:: Set directory to the data_set folder
cd /d "D:\Projects\Attendance_Project-main\data_set"

:MENU
cls
echo ===================================================
echo     FACE REGISTRATION ^& ENCODING SYSTEM
echo ===================================================
echo 1. Capture a New Face (Step 1)
echo 2. Run Encoding / Update Database (Step 2)
echo 3. Exit
echo ===================================================
set /p choice="Choose an option (1/2/3): "

if "%choice%"=="1" goto CAPTURE
if "%choice%"=="2" goto ENCODE
if "%choice%"=="3" goto EXIT
goto MENU

:CAPTURE
cls
echo --- Running Face Capture ---
"D:\Projects\Attendance_Project-main\.venv\Scripts\python.exe" 1_capture_faces.py

echo.
echo ===================================================
echo [DONE] Capture complete for this student.
echo ===================================================
echo A. Capture ANOTHER student
echo B. Run Encoding now (Finalize Database)
echo M. Back to Main Menu
echo ===================================================
set /p post_cap="Choose action (A/B/M): "

if /I "%post_cap%"=="A" goto CAPTURE
if /I "%post_cap%"=="B" goto ENCODE
if /I "%post_cap%"=="M" goto MENU
goto MENU

:ENCODE
cls
echo --- Running Face Encoding ---
echo Please wait, this may take a minute if you have many students...
"D:\Projects\Attendance_Project-main\.venv\Scripts\python.exe" 2_encode_faces.py

echo.
echo ===================================================
echo [SUCCESS] Encoding complete! 
echo Your 'encodings.pickle' is now updated.
echo ===================================================
pause
goto MENU

:EXIT
exit