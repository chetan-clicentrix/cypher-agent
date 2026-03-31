"""
tests/test_service.py
=====================
Sanity checks for the Cipher background service runner.
Tests that cipher_service.py starts correctly and cleans up its PID file.

Run:
    cd d:\\Cipher
    venv\\Scripts\\python.exe -m pytest tests\\test_service.py -v
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

ROOT_DIR    = Path(__file__).parent.parent          # d:\Cipher
SERVICE_DIR = ROOT_DIR / "service"
PID_FILE    = SERVICE_DIR / "cipher.pid"
STATUS_FILE = SERVICE_DIR / "cipher_status.txt"
LOG_FILE    = SERVICE_DIR / "cipher_service.log"
PYTHON_EXE  = ROOT_DIR / "venv" / "Scripts" / "python.exe"
SERVICE_SCRIPT = SERVICE_DIR / "cipher_service.py"


def _start_service(timeout: int = 10) -> subprocess.Popen:
    """Launch cipher_service.py as a subprocess and wait for PID file."""
    proc = subprocess.Popen(
        [str(PYTHON_EXE), str(SERVICE_SCRIPT)],
        cwd=str(ROOT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait for PID file to appear (means service has initialised)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if PID_FILE.exists():
            return proc
        time.sleep(0.5)
    return proc   # return even if PID file not yet present


def _stop_service(proc: subprocess.Popen, wait: int = 5):
    """Terminate the service gracefully."""
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            proc.kill()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_service_script_exists():
    """cipher_service.py must be present."""
    assert SERVICE_SCRIPT.exists(), f"Service script not found at {SERVICE_SCRIPT}"


def test_service_starts_and_writes_pid():
    """Service should write a PID file within 15 seconds of starting."""
    proc = _start_service(timeout=15)
    try:
        assert PID_FILE.exists(), "PID file was not created within 15 seconds"
        pid = int(PID_FILE.read_text().strip())
        assert pid > 0, f"Invalid PID in file: {pid}"
    finally:
        _stop_service(proc)


def test_service_writes_status_file():
    """Service should write a status file."""
    proc = _start_service(timeout=15)
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            if STATUS_FILE.exists():
                break
            time.sleep(0.5)
        assert STATUS_FILE.exists(), "Status file was not created within 15 seconds"
        status = STATUS_FILE.read_text().strip()
        assert status in ("starting", "active"), f"Unexpected status: '{status}'"
    finally:
        _stop_service(proc)


def test_service_creates_log_file():
    """Service should write log output to cipher_service.log."""
    # Clean up any stale log from a previous run
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    proc = _start_service(timeout=15)
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:
                break
            time.sleep(0.5)
        assert LOG_FILE.exists(), "Log file was not created"
        assert LOG_FILE.stat().st_size > 0, "Log file is empty"
    finally:
        _stop_service(proc)


def test_service_removes_pid_on_stop():
    """After the service stops the PID file should be cleaned up."""
    proc = _start_service(timeout=15)
    _stop_service(proc, wait=10)

    # Wait up to 5 more seconds for cleanup
    deadline = time.time() + 5
    while time.time() < deadline:
        if not PID_FILE.exists():
            break
        time.sleep(0.5)

    assert not PID_FILE.exists(), "PID file was not removed after service stopped"
