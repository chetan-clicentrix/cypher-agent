"""
Encapsulates OpenCV camera capture.
"""
import cv2
from .config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS

class CameraFeed:
    def __init__(self):
        self.cap = None

    def start(self) -> bool:
        """Opens the camera."""
        # Use cv2.CAP_DSHOW on Windows for faster init and directshow backend
        self.cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            return False
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        return True

    def read_frame(self):
        """Reads a frame and returns (success, bgr_frame, rgb_frame)."""
        if self.cap is None or not self.cap.isOpened():
            return False, None, None
            
        success, frame = self.cap.read()
        if not success:
            return False, None, None
            
        # Flip horizontally for intuitive mirror effect
        frame = cv2.flip(frame, 1)
        
        # Convert BGR (OpenCV) to RGB (MediaPipe)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return True, frame, rgb_frame

    def stop(self):
        """Releases the camera."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
