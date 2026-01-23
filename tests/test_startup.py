import subprocess
import time
import sys
import os

def test_startup():
    print("--- Starting Startup Test ---")
    
    # Path to main.py
    main_py = os.path.join(os.path.dirname(__file__), "..", "main.py")
    main_py = os.path.abspath(main_py)
    
    # Run the app for a few seconds
    # We use a timeout to kill it if it doesn't close itself
    # But Flet app starts a window, so we might need to use a environment variable
    # to tell flet to run headlessly or just check for immediate traceback
    
    try:
        # We run it as a subprocess and look for "TypeError" or "Unhandled error" in output
        # Flet often prints these to stderr/stdout even if the window stays open
        process = subprocess.Popen(
            [sys.executable, main_py],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for 10 seconds to allow the app to initialize and session to be created
        print("Waiting for app to initialize (10 seconds)...")
        time.sleep(10)
        
        # Check if process crashed immediately
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print("Process terminated early.")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            if "TypeError" in stderr or "TypeError" in stdout or "Unhandled error" in stderr:
                print("FAIL: Startup error detected.")
                sys.exit(1)
        else:
            # Still running, which is good (didn't crash immediately)
            # Kill the process tree to ensure Flet view is also closed
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
            else:
                process.terminate()
            
            stdout, stderr = process.communicate(timeout=5)
            
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            
            if "TypeError" in stderr or "TypeError" in stdout or "Unhandled error" in stderr:
                print("FAIL: Async/Await error detected in output.")
                sys.exit(1)
            else:
                print("SUCCESS: No immediate startup errors detected.")
                
    except Exception as e:
        print(f"Error during test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_startup()
