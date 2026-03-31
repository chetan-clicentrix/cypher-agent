"""
Configuration for the Hand Tracking Module.
Tune these 'magic numbers' to adjust sensitivity, smoothing, and gestures.
"""

# Camera
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# MediaPipe
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.5

# Smoothing (1-Euro Filter)
# Decrease MIN_CUTOFF to decrease slow speed jitter
# Increase BETA to decrease high speed lag
SMOOTH_MIN_CUTOFF = 0.01  # Heavily filter at low speeds
SMOOTH_BETA = 0.1         # Increase for less lag at high speeds
SMOOTH_D_CUTOFF = 1.0

# Mouse Control
SCREEN_MARGIN = 100 # pixels from edge to reach screen boundary (to reach edges of monitor comfortably)

# Gestures (Distances are normalized 0.0 to 1.0)
PINCH_THRESHOLD       = 0.035   # Index + Thumb  → Left Click
RIGHT_CLICK_THRESHOLD = 0.035   # Ring + Thumb   → Right Click
DRAG_KEEP_THRESHOLD   = 0.04    # Index + Thumb held → Drag (slightly larger than click)
SCROLL_THRESHOLD      = 0.08    # Middle + Thumb → Scroll
VOLUME_THRESHOLD      = 0.08    # Pinky + Thumb  → Volume Up/Down
SWIPE_MIN_VELOCITY    = 0.012   # Normalized units/frame for Alt+Tab swipe

# Debounce & Cooldowns
FRAMES_TO_CONFIRM_GESTURE = 3
COOLDOWN_CLICK_SECS       = 0.35
COOLDOWN_RIGHT_CLICK_SECS = 0.45
COOLDOWN_SCROLL_SECS      = 0.05
COOLDOWN_VOLUME_SECS      = 0.08
COOLDOWN_ALTTAB_SECS      = 0.7
