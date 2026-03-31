import time
from src.tools.hand_control import start_hand_tracking, stop_hand_tracking

if __name__ == '__main__':
    print(start_hand_tracking())
    print("Move your index finger to guide the mouse.")
    print("Pinch index+thumb to click.")
    print("Press CTRL+C in this terminal to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(stop_hand_tracking())
