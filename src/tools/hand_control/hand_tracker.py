import time
import multiprocessing

def _tracking_loop(stop_event: multiprocessing.Event):
    """
    The main isolated process loop. Put all heavyweight imports (cv2, mediapipe)
    inside here so they don't break multiprocess pickling on Windows.
    """
    import cv2
    from .camera import CameraFeed
    from .gesture_engine import GestureEngine
    from .system_controller import SystemController

    camera = CameraFeed()
    if not camera.start():
        print("Failed to open camera for hand tracking.")
        return
        
    engine = GestureEngine()
    sys_ctrl = SystemController()
    
    # We create a named window to show the debug view so the user knows it's active
    cv2.namedWindow("Jarvis Hand Tracking", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Jarvis Hand Tracking", cv2.WND_PROP_TOPMOST, 1)
    
    print("Hand tracking process started. Press ESC or close the window to stop.")

    try:
        while not stop_event.is_set():
            loop_start = time.time()
            
            success, bgr_frame, rgb_frame = camera.read_frame()
            if not success:
                time.sleep(0.01)
                continue
                
            norm_x, norm_y, gesture, annotated_frame = engine.process_frame(rgb_frame, bgr_frame)
            
            if norm_x is not None and norm_y is not None:
                sys_ctrl.update_cursor(norm_x, norm_y)
                if gesture != "None":
                    sys_ctrl.execute_gesture(gesture)
                    
            # Display debug window
            if annotated_frame is not None:
                cv2.putText(annotated_frame, f"Gesture: {gesture}", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("Jarvis Hand Tracking", annotated_frame)
                
            # Check ESC key OR window X button close
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                print("ESC pressed. Exiting hand tracking.")
                break
            # WND_PROP_VISIBLE < 1 means the user closed the window with X
            if cv2.getWindowProperty("Jarvis Hand Tracking", cv2.WND_PROP_VISIBLE) < 1:
                print("Window closed. Exiting hand tracking.")
                break

            # FPS cap: target ~30fps to avoid hogging the CPU
            elapsed = time.time() - loop_start
            sleep_time = max(0, 0.033 - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
                
    except KeyboardInterrupt:
        pass
    finally:
        engine.close()
        camera.stop()
        cv2.destroyAllWindows()
        print("Hand tracking process cleanly exited.")
        
# Module-level tracking reference
_tracking_process = None
_stop_event = None

def start_hand_tracking() -> str:
    global _tracking_process, _stop_event
    
    if _tracking_process is not None and _tracking_process.is_alive():
        return "Hand tracking is already running."
        
    _stop_event = multiprocessing.Event()
    _tracking_process = multiprocessing.Process(
        target=_tracking_loop, 
        args=(_stop_event,), 
        daemon=True
    )
    _tracking_process.start()
    return "Hand tracking mode turned on. Camera is active and recognizing gestures."

def stop_hand_tracking() -> str:
    global _tracking_process, _stop_event
    
    if _tracking_process is None or not _tracking_process.is_alive():
        return "Hand tracking is not running."
        
    _stop_event.set()
    _tracking_process.join(timeout=3)
    if _tracking_process.is_alive():
        _tracking_process.terminate()
        
    _tracking_process = None
    _stop_event = None
    return "Hand tracking mode turned off. Camera released."
