"""
Cipher System Tray Icon
========================
Provides a Windows system tray icon for the background service.

Shows:
  - Service status (active / restarting / stopped)
  - Right-click menu: Open Logs, Restart, Stop

Communicates with cipher_service.py via:
  - SERVICE_DIR/cipher_status.txt  (service writes, tray reads)
  - SERVICE_DIR/cipher.pid         (presence = service alive)
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

# ── Dependency guard ─────────────────────────────────────────────────────────
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print(
        "[tray_icon] pystray/Pillow not installed.\n"
        "Run: pip install pystray Pillow"
    )
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
SERVICE_DIR = Path(__file__).parent
ROOT_DIR    = SERVICE_DIR.parent
LOG_FILE    = SERVICE_DIR / "cipher_service.log"
PID_FILE    = SERVICE_DIR / "cipher.pid"
STATUS_FILE = SERVICE_DIR / "cipher_status.txt"

# ── Icon Drawing ──────────────────────────────────────────────────────────────

def _make_icon(color: str = "#7C3AED") -> Image.Image:
    """Draw a simple 'C' logo for the tray icon (64×64 px)."""
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    draw.ellipse([0, 0, size - 1, size - 1], fill=color)

    # White 'C' letter
    cx, cy = size // 2, size // 2
    r = 18
    draw.arc([cx - r, cy - r, cx + r, cy + r], start=40, end=320, fill="white", width=7)

    return img


def _status_icon(status: str) -> Image.Image:
    """Pick icon colour based on status string."""
    if "active" in status:
        return _make_icon("#059669")    # green
    elif "restart" in status or "cooldown" in status:
        return _make_icon("#D97706")    # amber
    else:
        return _make_icon("#DC2626")    # red


# ── Status Reader ─────────────────────────────────────────────────────────────

def _read_status() -> str:
    try:
        return STATUS_FILE.read_text().strip()
    except Exception:
        return "unknown"


def _service_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        # On Windows, os.kill with signal 0 checks existence
        os.kill(pid, 0)
        return True
    except (ValueError, OSError):
        return False


def _read_pid() -> int | None:
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None


# ── Tray Menu Actions ─────────────────────────────────────────────────────────

def _open_logs(icon, item):
    """Open the log file in Notepad."""
    try:
        os.startfile(str(LOG_FILE))
    except Exception as e:
        print(f"[tray] Could not open log: {e}")


def _restart_service(icon, item):
    """Kill current service process and relaunch it."""
    pid = _read_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    time.sleep(2)
    _start_service_process()


def _stop_service(icon, item):
    """Terminate the service and quit the tray."""
    pid = _read_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    icon.stop()


def _start_service_process():
    """Launch cipher_service.py as a detached background process."""
    script = SERVICE_DIR / "cipher_service.py"
    subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(ROOT_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


# ── Status Polling ────────────────────────────────────────────────────────────

def _poll_status(icon: pystray.Icon):
    """Background thread — updates icon colour + tooltip every 5 s."""
    while True:
        try:
            status = _read_status() if _service_running() else "stopped"
            icon.icon  = _status_icon(status)
            icon.title = f"Cipher AI — {status.title()}"
            icon.menu  = _build_menu(status)
        except Exception:
            pass
        time.sleep(5)


# ── Menu Builder ──────────────────────────────────────────────────────────────

def _build_menu(status: str = "") -> pystray.Menu:
    indicator = "🟢" if "active" in status else ("🟡" if "restart" in status else "🔴")
    return pystray.Menu(
        pystray.MenuItem(f"{indicator} Status: {status.title() or 'Unknown'}", lambda i, s: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("📋 Open Logs",       _open_logs),
        pystray.MenuItem("🔁 Restart Service", _restart_service),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ Stop Cipher",     _stop_service),
    )


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    initial_status = _read_status() if _service_running() else "stopped"
    icon_img = _status_icon(initial_status)

    icon = pystray.Icon(
        name  = "CipherAI",
        icon  = icon_img,
        title = f"Cipher AI — {initial_status.title()}",
        menu  = _build_menu(initial_status),
    )

    # Poll status in background thread
    poll_thread = threading.Thread(target=_poll_status, args=(icon,), daemon=True)
    poll_thread.start()

    icon.run()


if __name__ == "__main__":
    main()
