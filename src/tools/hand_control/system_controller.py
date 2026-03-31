import math
import time
import ctypes
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController, Key
import win32api
from .config import SMOOTH_MIN_CUTOFF, SMOOTH_BETA, SMOOTH_D_CUTOFF

# Windows virtual key codes for media volume
VK_VOLUME_UP   = 0xAF
VK_VOLUME_DOWN = 0xAE


class OneEuroFilter:
    """1-Euro Filter — removes jitter from a noisy spatial signal."""

    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta       = beta
        self.d_cutoff   = d_cutoff
        self.x_prev = self.dx_prev = self.t_prev = None

    def _alpha(self, cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t=None):
        if t is None:
            t = time.time()
        if self.x_prev is None:
            self.x_prev, self.dx_prev, self.t_prev = x, 0.0, t
            return x
        dt = t - self.t_prev
        if dt <= 0:
            return x
        a_d   = self._alpha(self.d_cutoff, dt)
        dx    = (x - self.x_prev) / dt
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a      = self._alpha(cutoff, dt)
        x_hat  = a * x + (1 - a) * self.x_prev
        self.x_prev, self.dx_prev, self.t_prev = x_hat, dx_hat, t
        return x_hat


class SystemController:
    """Translates gesture tokens into OS-level mouse/keyboard/volume events."""

    def __init__(self):
        self.mouse    = MouseController()
        self.keyboard = KeyboardController()

        self.screen_w = win32api.GetSystemMetrics(0)
        self.screen_h = win32api.GetSystemMetrics(1)

        self.filter_x = OneEuroFilter(SMOOTH_MIN_CUTOFF, SMOOTH_BETA, SMOOTH_D_CUTOFF)
        self.filter_y = OneEuroFilter(SMOOTH_MIN_CUTOFF, SMOOTH_BETA, SMOOTH_D_CUTOFF)

        self._dragging = False

        # Volume state (0-100)
        self._volume = 50

    # ── Cursor ────────────────────────────────────────────────────────────
    def update_cursor(self, norm_x: float, norm_y: float):
        raw_x = norm_x * self.screen_w
        raw_y = norm_y * self.screen_h
        sx = max(0, min(self.screen_w - 1, int(self.filter_x(raw_x))))
        sy = max(0, min(self.screen_h - 1, int(self.filter_y(raw_y))))
        self.mouse.position = (sx, sy)

    # ── Gesture Dispatcher ────────────────────────────────────────────────
    def execute_gesture(self, gesture: str):
        if gesture == "Click":
            self.mouse.click(Button.left, 1)
            print("🖱️  Left Click")

        elif gesture == "RightClick":
            self.mouse.click(Button.right, 1)
            print("🖱️  Right Click")

        elif gesture == "DragStart":
            self.mouse.press(Button.left)
            self._dragging = True
            print("🤏 Drag Start")

        elif gesture == "DragEnd":
            if self._dragging:
                self.mouse.release(Button.left)
                self._dragging = False
                print("🤏 Drag End")

        elif gesture == "ScrollDown":
            self.mouse.scroll(0, -2)

        elif gesture == "ScrollUp":
            self.mouse.scroll(0, 2)

        elif gesture == "VolumeUp":
            self._set_volume("up")
            print("🔊 Volume Up")

        elif gesture == "VolumeDown":
            self._set_volume("down")
            print("🔉 Volume Down")

        elif gesture == "AltTab":
            self.keyboard.press(Key.alt)
            self.keyboard.press(Key.tab)
            self.keyboard.release(Key.tab)
            self.keyboard.release(Key.alt)
            print("⬅️  Alt+Tab")

    # ── Volume helper ────────────────────────────────────────────────────
    def _set_volume(self, direction: str):
        """Fires a media key press — instant, no subprocess, no blocking."""
        vk = VK_VOLUME_UP if direction == "up" else VK_VOLUME_DOWN
        # keybd_event: key down then key up
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP = 2
