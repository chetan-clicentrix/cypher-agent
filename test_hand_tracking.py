import time
import sys
import os

# Ensure the root directory is in the path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.hand_control import start_hand_tracking, stop_hand_tracking

def main():
    print("Testing hand tracking process spawning...")
    res1 = start_hand_tracking()
    print("Result:", res1)
    
    # Try calling it again to test idempotency
    print("\nCalling it again while running...")
    res_dup = start_hand_tracking()
    print("Result:", res_dup)
    
    print("\nWaiting 10 seconds to let OpenCV and MediaPipe initialize...")
    for i in range(10, 0, -1):
        print(f"{i}...", end="", flush=True)
        time.sleep(1)
    print()
    
    print("\nStopping hand tracking process...")
    res2 = stop_hand_tracking()
    print("Result:", res2)
    
    print("\nCalling stop again...")
    res_dup_stop = stop_hand_tracking()
    print("Result:", res_dup_stop)
    
    print("\nTest finished.")

if __name__ == "__main__":
    main()
