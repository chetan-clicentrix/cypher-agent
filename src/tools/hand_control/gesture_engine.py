"""
Gesture Engine — Uses the modern MediaPipe Tasks API (mediapipe >= 0.10.14).

Gestures supported:
  - Move Mouse    : Index fingertip tracks cursor
  - Left Click    : Pinch Index + Thumb
  - Right Click   : Pinch Ring + Thumb
  - Drag          : Hold Index + Thumb pinch while moving (click-hold)
  - Scroll        : Pinch Middle + Thumb (hand Y position drives scroll direction)
"""

import time
import threading
import numpy as np
from pathlib import Path

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    HandLandmarkerResult,
    RunningMode,
)

# Landmark indices
THUMB_TIP  = 4
INDEX_TIP  = 8
MIDDLE_TIP = 12
RING_TIP   = 16
PINKY_TIP  = 20
WRIST      = 0

_MODEL_PATH = Path(__file__).with_name("hand_landmarker.task")

# Connection pairs for visualisation
_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (5,6),(6,7),(7,8),
    (9,10),(10,11),(11,12),
    (13,14),(14,15),(15,16),
    (17,18),(18,19),(19,20),
    (0,5),(5,9),(9,13),(13,17),(0,17)
]


class GestureEngine:
    def __init__(self):
        from .config import (
            MIN_DETECTION_CONFIDENCE, MIN_TRACKING_CONFIDENCE,
            PINCH_THRESHOLD, RIGHT_CLICK_THRESHOLD, DRAG_KEEP_THRESHOLD,
            SCROLL_THRESHOLD, VOLUME_THRESHOLD, SWIPE_MIN_VELOCITY,
            FRAMES_TO_CONFIRM_GESTURE,
            COOLDOWN_CLICK_SECS, COOLDOWN_RIGHT_CLICK_SECS,
            COOLDOWN_SCROLL_SECS, COOLDOWN_VOLUME_SECS, COOLDOWN_ALTTAB_SECS,
        )
        self._t_pinch      = PINCH_THRESHOLD
        self._t_rclick     = RIGHT_CLICK_THRESHOLD
        self._t_drag       = DRAG_KEEP_THRESHOLD
        self._t_scroll     = SCROLL_THRESHOLD
        self._t_volume     = VOLUME_THRESHOLD
        self._t_swipe_v    = SWIPE_MIN_VELOCITY
        self._frames_req   = FRAMES_TO_CONFIRM_GESTURE
        self._cd_click     = COOLDOWN_CLICK_SECS
        self._cd_rclick    = COOLDOWN_RIGHT_CLICK_SECS
        self._cd_scroll    = COOLDOWN_SCROLL_SECS
        self._cd_volume    = COOLDOWN_VOLUME_SECS
        self._cd_alttab    = COOLDOWN_ALTTAB_SECS

        # Thread-safe result storage
        self._result: HandLandmarkerResult | None = None
        self._lock = threading.Lock()

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(_MODEL_PATH)),
            running_mode=RunningMode.LIVE_STREAM,
            num_hands=1,
            min_hand_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
            result_callback=self._on_result,
        )
        self.landmarker = HandLandmarker.create_from_options(options)

        # Debounce frame counters
        self._frames = {g: 0 for g in ("click", "rclick", "scroll", "volume", "drag")}

        # Cooldown timers
        self._last = {g: 0.0 for g in ("click", "rclick", "scroll", "volume", "alttab")}

        # Drag state
        self._dragging = False

        # Swipe tracking (wrist X position history)
        self._prev_wrist_x: float | None = None
        self._frame_ts_ms = 0

    def _on_result(self, result, output_image, ts_ms):
        with self._lock:
            self._result = result

    def process_frame(self, rgb_frame, bgr_frame=None):
        """
        Returns (norm_x, norm_y, gesture_str, annotated_bgr_frame).
        gesture_str can be: None | Click | RightClick | DragStart | DragEnd | 
                            ScrollUp | ScrollDown | VolumeUp | VolumeDown | AltTab
        """
        import cv2

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        self._frame_ts_ms += 33
        self.landmarker.detect_async(mp_image, self._frame_ts_ms)

        with self._lock:
            result = self._result

        annotated = bgr_frame.copy() if bgr_frame is not None else None

        if not result or not result.hand_landmarks:
            # If we were dragging and hand disappears, release the drag
            if self._dragging:
                self._dragging = False
                self._prev_wrist_x = None
                return None, None, "DragEnd", annotated
            self._prev_wrist_x = None
            return None, None, "None", annotated

        lm = result.hand_landmarks[0]

        # ── Draw skeleton ────────────────────────────────────────────────────
        if annotated is not None:
            h, w = annotated.shape[:2]
            for a, b in _CONNECTIONS:
                p1, p2 = lm[a], lm[b]
                cv2.line(annotated,
                         (int(p1.x*w), int(p1.y*h)),
                         (int(p2.x*w), int(p2.y*h)),
                         (0, 200, 0), 2)
            for lmk in lm:
                cv2.circle(annotated, (int(lmk.x*w), int(lmk.y*h)), 5, (0, 0, 255), -1)

        # ── Extract key points ───────────────────────────────────────────────
        thumb  = lm[THUMB_TIP]
        index  = lm[INDEX_TIP]
        middle = lm[MIDDLE_TIP]
        ring   = lm[RING_TIP]
        pinky  = lm[PINKY_TIP]
        wrist  = lm[WRIST]

        cursor_x = index.x
        cursor_y = index.y

        def dist(a, b):
            return np.linalg.norm(
                np.array([a.x, a.y, a.z]) - np.array([b.x, b.y, b.z])
            )

        d_index_thumb  = dist(thumb, index)
        d_middle_thumb = dist(thumb, middle)
        d_ring_thumb   = dist(thumb, ring)
        d_pinky_thumb  = dist(thumb, pinky)

        gesture = "None"
        now = time.time()

        # ── 2. Drag: Index+Thumb held (slightly looser threshold) ───────────
        if d_index_thumb < self._t_drag:
            self._frames["drag"] += 1
            if self._frames["drag"] >= self._frames_req:
                if not self._dragging:
                    self._dragging = True
                    gesture = "DragStart"
                else:
                    gesture = "None" # We are actively dragging, suppress other gestures
        else:
            if self._dragging:
                self._dragging = False
                gesture = "DragEnd"
            self._frames["drag"] = 0

        # If we are dragging, completely skip Alt+Tab, Volume, and Scroll to avoid lag
        if not self._dragging and gesture == "None":
            
            # ── Alt+Tab removed per user ──
            
            # ── 3. Left Click: Index+Thumb quick pinch ─
            if gesture == "None":
                if d_index_thumb < self._t_pinch:
                    self._frames["click"] += 1
                    if self._frames["click"] >= self._frames_req:
                        if (now - self._last["click"]) > self._cd_click:
                            gesture = "Click"
                            self._last["click"] = now
                        self._frames["click"] = 0
                else:
                    self._frames["click"] = 0

            # ── 4. Right Click: Ring+Thumb ───────────────────────────────────────
            if gesture == "None":
                if d_ring_thumb < self._t_rclick:
                    self._frames["rclick"] += 1
                    if self._frames["rclick"] >= self._frames_req:
                        if (now - self._last["rclick"]) > self._cd_rclick:
                            gesture = "RightClick"
                            self._last["rclick"] = now
                        self._frames["rclick"] = 0
                else:
                    self._frames["rclick"] = 0

            # ── 5. Scroll: Middle+Thumb ─────
            if gesture == "None":
                if d_middle_thumb < self._t_scroll:
                    self._frames["scroll"] += 1
                    if self._frames["scroll"] >= self._frames_req:
                        if (now - self._last["scroll"]) > self._cd_scroll:
                            gesture = "ScrollUp" if wrist.y < 0.5 else "ScrollDown"
                            self._last["scroll"] = now
                        self._frames["scroll"] = 0
                else:
                    self._frames["scroll"] = 0

            # ── Volume removed per user ──
                    
        self._prev_wrist_x = wrist.x

        return cursor_x, cursor_y, gesture, annotated

    def close(self):
        self.landmarker.close()
