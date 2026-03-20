#!/usr/bin/env python3
"""
Smart Attendance System - Hardware Test Suite
Test all components before deployment
"""

import sys
import os

def test_imports():
    """Test all required imports"""
    print("=" * 60)
    print("📦 TESTING IMPORTS")
    print("=" * 60)
    
    tests = [
        ("Flask", "flask"),
        ("OpenCV", "cv2"),
        ("NumPy", "numpy"),
        ("Face Recognition", "face_recognition"),
        ("Pickle", "pickle"),
    ]
    
    all_passed = True
    for name, module in tests:
        try:
            __import__(module)
            print(f"✓ {name:20} OK")
        except ImportError as e:
            print(f"✗ {name:20} FAILED: {e}")
            all_passed = False
    
    return all_passed

def test_optional_imports():
    """Test optional imports"""
    print("\n" + "=" * 60)
    print("📦 TESTING OPTIONAL IMPORTS")
    print("=" * 60)
    
    optional = [
        ("RPi.GPIO", "RPi.GPIO"),
        ("rpi_lcd", "rpi_lcd"),
    ]
    
    for name, module in optional:
        try:
            __import__(module)
            print(f"✓ {name:20} OK")
        except ImportError:
            print(f"- {name:20} NOT INSTALLED (optional)")

def test_database_files():
    """Check if required database files exist"""
    print("\n" + "=" * 60)
    print("📁 CHECKING DATABASE FILES")
    print("=" * 60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    files = {
        "Encodings": os.path.join(script_dir, "data_set", "encodings.pickle"),
        "Students DB": os.path.join(script_dir, "data_set", "students_db.csv"),
        "Dataset Dir": os.path.join(script_dir, "data_set", "dataset"),
    }
    
    all_exist = True
    for name, path in files.items():
        if os.path.exists(path):
            print(f"✓ {name:20} FOUND at {path}")
        else:
            print(f"✗ {name:20} MISSING at {path}")
            all_exist = False
    
    return all_exist

def test_camera():
    """Test camera connectivity"""
    print("\n" + "=" * 60)
    print("📹 TESTING CAMERA")
    print("=" * 60)
    
    try:
        import cv2
        camera = cv2.VideoCapture(0)
        if camera.isOpened():
            ret, frame = camera.read()
            camera.release()
            if ret:
                print(f"✓ Camera          OK")
                print(f"  Frame shape: {frame.shape}")
                return True
            else:
                print(f"✗ Camera          FAILED (no frame captured)")
                camera.release()
                return False
        else:
            print(f"✗ Camera          NOT FOUND")
            return False
    except Exception as e:
        print(f"✗ Camera          ERROR: {e}")
        return False

def test_gpio():
    """Test GPIO for buzzer"""
    print("\n" + "=" * 60)
    print("⚡ TESTING GPIO")
    print("=" * 60)
    
    try:
        import RPi.GPIO as GPIO  # type: ignore
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.OUT)
        GPIO.output(17, GPIO.LOW)
        GPIO.cleanup()
        print("✓ GPIO 17         OK (Buzzer ready)")
        return True
    except ImportError:
        print("- GPIO            NOT INSTALLED (simulation mode)")
        return None
    except Exception as e:
        print(f"✗ GPIO            ERROR: {e}")
        return False

def test_lcd():
    """Test LCD display"""
    print("\n" + "=" * 60)
    print("📺 TESTING LCD DISPLAY")
    print("=" * 60)
    
    try:
        import smbus  # type: ignore
        bus = smbus.SMBus(1)
        
        try:
            # Try common I2C addresses
            addresses = [0x27, 0x3f, 0x20, 0x21]
            found = False
            for addr in addresses:
                try:
                    bus.read_byte(addr)
                    print(f"✓ LCD Display     OK at address 0x{addr:02x}")
                    found = True
                    break
                except:
                    pass
            
            if not found:
                print("✗ LCD Display     NOT FOUND (check I2C connections)")
                return False
            return True
        except Exception as e:
            print(f"✗ LCD Display     ERROR: {e}")
            return False
    except ImportError:
        print("- LCD Display     I2C library not installed (optional)")
        return None
    except Exception as e:
        print(f"✗ LCD Display     ERROR: {e}")
        return False

def test_face_recognition():
    """Test face recognition with sample image"""
    print("\n" + "=" * 60)
    print("🎭 TESTING FACE RECOGNITION")
    print("=" * 60)
    
    try:
        import face_recognition
        import cv2
        import numpy as np
        
        # Create a dummy image
        dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Test face detection (should find 0 faces)
        locations = face_recognition.face_locations(dummy_image, model="hog")
        print(f"✓ HOG Model       OK (found {len(locations)} faces in dummy image)")
        
        # Test with real camera frame
        camera = cv2.VideoCapture(0)
        if camera.isOpened():
            ret, frame = camera.read()
            if ret:
                small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                locations = face_recognition.face_locations(rgb, model="hog")
                camera.release()
                print(f"✓ Face Detection  OK (found {len(locations)} faces in live frame)")
                return True
            camera.release()
        
        return True
    except Exception as e:
        print(f"✗ Face Recognition ERROR: {e}")
        return False

def test_configuration():
    """Test configuration file"""
    print("\n" + "=" * 60)
    print("⚙️  TESTING CONFIGURATION")
    print("=" * 60)
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, script_dir)
        import config
        
        print(f"✓ Configuration   OK")
        print(f"  FRAME_SCALE: {config.FRAME_SCALE}")
        print(f"  PROCESS_EVERY_N_FRAMES: {config.PROCESS_EVERY_N_FRAMES}")
        print(f"  MODEL_TYPE: {config.MODEL_TYPE}")
        print(f"  BUZZER_PIN: {config.BUZZER_PIN}")
        return True
    except Exception as e:
        print(f"✗ Configuration   ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  SMART ATTENDANCE SYSTEM - HARDWARE TEST SUITE  ".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝\n")
    
    results = {
        "Imports": test_imports(),
        "Database Files": test_database_files(),
        "Configuration": test_configuration(),
        "Camera": test_camera(),
        "GPIO": test_gpio(),
        "LCD": test_lcd(),
        "Face Recognition": test_face_recognition(),
    }
    
    test_optional_imports()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    critical_tests = {
        "Imports": results["Imports"],
        "Camera": results["Camera"],
        "Face Recognition": results["Face Recognition"],
    }
    
    optional_tests = {
        "Database Files": results["Database Files"],
        "GPIO": results["GPIO"],
        "LCD": results["LCD"],
    }
    
    critical_pass = all(v for v in critical_tests.values() if v is not None)
    optional_pass = all(v for v in optional_tests.values() if v is not None)
    
    print("\nCritical Tests:")
    for test, result in critical_tests.items():
        if result is None:
            status = "SKIPPED"
        elif result:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
        print(f"  {test:20} {status}")
    
    print("\nOptional Tests:")
    for test, result in optional_tests.items():
        if result is None:
            status = "SKIPPED"
        elif result:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
        print(f"  {test:20} {status}")
    
    print("\n" + "=" * 60)
    if critical_pass:
        print("✓ READY FOR DEPLOYMENT")
        print("\nYou can now run: python3 app.py")
        return 0
    else:
        print("✗ CRITICAL ISSUES DETECTED")
        print("\nFix the above issues before running the application.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
