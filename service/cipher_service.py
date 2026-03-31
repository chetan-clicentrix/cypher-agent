"""
Cipher Background Service Runner
=================================
Headless entry point for 24/7 operation.
- Redirects all output to a rotating log file
- Writes a PID file for health checks
- Auto-restarts the engine on crash (max 3, exponential back-off)
- Launches the system tray icon in a side process

Run directly:
    python d:\\Cipher\\service\\cipher_service.py

Or via Task Scheduler (see install_service.ps1).
"""

import sys
import os
import time
import signal
import logging
import subprocess
import multiprocessing
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────

SERVICE_DIR  = Path(__file__).parent           # d:\Cipher\service\
ROOT_DIR     = SERVICE_DIR.parent              # d:\Cipher\
LOG_FILE     = SERVICE_DIR / "cipher_service.log"
PID_FILE     = SERVICE_DIR / "cipher.pid"
STATUS_FILE  = SERVICE_DIR / "cipher_status.txt"   # read by tray icon

MAX_RESTARTS = 3
BACKOFF_SECS = [30, 60, 120]   # wait between restarts (exponential)
COOLDOWN_SEC = 300             # 5-min cooldown after max restarts exceeded

# ── Logging Setup ────────────────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    """Configure rotating file logger (5 MB, 3 backups)."""
    logger = logging.getLogger("CipherService")
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)

    # Also show in console if launched manually (not via Task Scheduler)
    if sys.stdout.isatty():
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(console)

    # Redirect bare print() / uncaught tracebacks to the log
    sys.stdout = _StreamToLogger(logger, logging.INFO)
    sys.stderr = _StreamToLogger(logger, logging.ERROR)

    return logger


class _StreamToLogger:
    """Redirect stdout/stderr writes to a Python logger."""

    def __init__(self, logger: logging.Logger, level: int):
        self._logger = logger
        self._level  = level
        self._buf    = ""

    def write(self, message: str):
        self._buf += message
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.rstrip():
                self._logger.log(self._level, line.rstrip())

    def flush(self):
        if self._buf.rstrip():
            self._logger.log(self._level, self._buf.rstrip())
            self._buf = ""

    def isatty(self):
        return False


# ── PID / Status Helpers ─────────────────────────────────────────────────────

def _write_pid(logger: logging.Logger):
    PID_FILE.write_text(str(os.getpid()))
    logger.info(f"PID {os.getpid()} written to {PID_FILE}")


def _remove_pid():
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _set_status(status: str):
    """Write a one-line status for the tray icon to display."""
    try:
        STATUS_FILE.write_text(status)
    except Exception:
        pass


# ── Tray Icon Process ─────────────────────────────────────────────────────────

def _launch_tray() -> subprocess.Popen:
    """Spawn the tray icon as a separate detached process."""
    tray_script = SERVICE_DIR / "tray_icon.py"
    if not tray_script.exists():
        return None
    try:
        proc = subprocess.Popen(
            [sys.executable, str(tray_script)],
            cwd=str(ROOT_DIR),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return proc
    except Exception as e:
        print(f"[WARNING] Could not launch tray icon: {e}")
        return None


# ── Engine Runner ─────────────────────────────────────────────────────────────

def _run_engine_once():
    """
    Import and run CypherEngine in wake-word mode.
    Runs in the current process — blocks until engine exits or crashes.
    """
    # Ensure the project root is on sys.path so 'src' is importable
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

    from src.core.engine import CypherEngine
    engine = CypherEngine()
    engine.run_headless()


# ── Main Service Loop ─────────────────────────────────────────────────────────

_shutdown_requested = False


def _handle_signal(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True


def main():
    global _shutdown_requested

    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("  Cipher Background Service — Starting")
    logger.info("=" * 60)

    _write_pid(logger)
    _set_status("starting")

    # Register shutdown signals
    signal.signal(signal.SIGTERM, _handle_signal)
    try:
        signal.signal(signal.SIGBREAK, _handle_signal)   # Windows Ctrl+Break
    except AttributeError:
        pass

    # Launch tray icon (fire & forget)
    tray_proc = _launch_tray()
    if tray_proc:
        logger.info(f"Tray icon launched (pid={tray_proc.pid})")

    restart_count = 0

    try:
        while not _shutdown_requested:
            if restart_count > MAX_RESTARTS:
                logger.error(f"Too many restarts ({restart_count}). Cooling down {COOLDOWN_SEC}s …")
                _set_status("cooldown")
                for _ in range(COOLDOWN_SEC):
                    if _shutdown_requested:
                        break
                    time.sleep(1)
                restart_count = 0   # reset after cooldown
                continue

            logger.info(f"Starting CypherEngine (attempt {restart_count + 1}) …")
            _set_status("active")

            try:
                _run_engine_once()
                # Clean exit (engine.run_headless returned normally)
                logger.info("CypherEngine exited cleanly.")
                break

            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received — shutting down.")
                _shutdown_requested = True
                break

            except Exception as exc:
                restart_count += 1
                wait = BACKOFF_SECS[min(restart_count - 1, len(BACKOFF_SECS) - 1)]
                logger.error(f"Engine crashed: {exc}", exc_info=True)
                logger.info(f"Restarting in {wait}s … (restart {restart_count}/{MAX_RESTARTS})")
                _set_status(f"restarting ({restart_count}/{MAX_RESTARTS})")

                for _ in range(wait):
                    if _shutdown_requested:
                        break
                    time.sleep(1)

    finally:
        _set_status("stopped")
        _remove_pid()

        # Ask tray to exit
        if tray_proc and tray_proc.poll() is None:
            tray_proc.terminate()

        logger.info("Cipher Background Service — Stopped.")


if __name__ == "__main__":
    main()
