"""
PC Control Tool — Jarvis
Windows automation: open apps, control media, volume, screenshots, notes, reminders, system.
"""

import os
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus


# ─────────────────────────────────────────────
# 1. Open URL / YouTube Search
# ─────────────────────────────────────────────

def open_url(url: str) -> str:
    """Open any URL in the default browser."""
    try:
        webbrowser.open(url)
        return f"Opened: {url}"
    except Exception as e:
        return f"Failed to open URL: {e}"


def play_on_youtube(query: str) -> str:
    """Search YouTube for a query and open it in the browser."""
    try:
        url = f"https://www.youtube.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        return f"Opening YouTube search for: {query}"
    except Exception as e:
        return f"YouTube error: {e}"


# ─────────────────────────────────────────────
# 2. Open App by Name
# ─────────────────────────────────────────────

# Common app name → executable mappings for Windows
_APP_MAP = {
    "chrome":       "start chrome",
    "google chrome":"start chrome",
    "firefox":      "start firefox",
    "edge":         "start msedge",
    "notepad":      "notepad",
    "vscode":       "code",
    "vs code":      "code",
    "visual studio code": "code",
    "spotify":      "start spotify",
    "discord":      "start discord",
    "whatsapp":     "start whatsapp",
    "telegram":     "start telegram",
    "explorer":     "explorer",
    "file explorer":"explorer",
    "calculator":   "calc",
    "paint":        "mspaint",
    "word":         "start winword",
    "excel":        "start excel",
    "powerpoint":   "start powerpnt",
    "task manager": "taskmgr",
    "settings":     "start ms-settings:",
    "control panel":"control",
    "cmd":          "start cmd",
    "powershell":   "start powershell",
}

def open_app(app_name: str) -> str:
    """Open a Windows application by name."""
    try:
        key = app_name.lower().strip()
        cmd = _APP_MAP.get(key)
        if not cmd:
            # Try a fuzzy match
            for k, v in _APP_MAP.items():
                if k in key or key in k:
                    cmd = v
                    break
        if not cmd:
            return (
                f"I don't know how to open '{app_name}'. "
                f"Known apps: {', '.join(sorted(set(_APP_MAP.keys()))[:15])}..."
            )
        subprocess.Popen(cmd, shell=True)
        return f"Opening {app_name}..."
    except Exception as e:
        return f"Failed to open app: {e}"


def open_folder(folder_path: str) -> str:
    """Open a folder in Windows Explorer."""
    try:
        path = Path(folder_path)
        if not path.exists():
            return f"Folder not found: {folder_path}"
        subprocess.Popen(f'explorer "{path}"', shell=True)
        return f"Opened folder: {folder_path}"
    except Exception as e:
        return f"Failed to open folder: {e}"


# ─────────────────────────────────────────────
# 3. Volume Control
# ─────────────────────────────────────────────

def set_volume(level: int) -> str:
    """Set system volume (0-100) using PowerShell."""
    try:
        level = max(0, min(100, int(level)))
        script = (
            f"$vol = New-Object -ComObject WScript.Shell; "
            f"$wsh = New-Object -ComObject WScript.Shell; "
            f"[audio]::Volume = {level / 100}"
        )
        # Use nircmd if available, otherwise PowerShell media key approach
        ps_script = f"""
$obj = New-Object -ComObject WScript.Shell
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int j();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int k(); int l(); int m(); int n();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, System.Guid pguidEventContext);
    int GetMute(out bool pbMute);
}}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{
    int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
}}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{
    int f();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumeratorComObject {{ }}
public class Audio {{
    static IAudioEndpointVolume Vol() {{
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0, 1, out dev));
        IAudioEndpointVolume vol = null;
        var iid = typeof(IAudioEndpointVolume).GUID;
        Marshal.ThrowExceptionForHR(dev.Activate(ref iid, 23, 0, out vol));
        return vol;
    }}
    public static float Volume {{
        get {{ float v = -1; Marshal.ThrowExceptionForHR(Vol().GetMasterVolumeLevelScalar(out v)); return v; }}
        set {{ Marshal.ThrowExceptionForHR(Vol().SetMasterVolumeLevelScalar(value, System.Guid.Empty)); }}
    }}
}}
'@
[Audio]::Volume = {level / 100}
"""
        subprocess.run(["powershell", "-Command", ps_script],
                       capture_output=True, timeout=10)
        return f"Volume set to {level}%"
    except Exception as e:
        return f"Volume control error: {e}"


def mute_volume() -> str:
    """Toggle mute using the media key."""
    try:
        # Send mute key via PowerShell
        ps = "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
        subprocess.run(["powershell", "-Command", ps], capture_output=True, timeout=5)
        return "Toggled mute."
    except Exception as e:
        return f"Mute error: {e}"


# ─────────────────────────────────────────────
# 4. Screenshot
# ─────────────────────────────────────────────

def take_screenshot(save_path: Optional[str] = None) -> str:
    """Take a screenshot and save it to D:\Cipher\screenshots\."""
    try:
        from PIL import ImageGrab
        if not save_path:
            screenshots_dir = Path(r"C:/Users/cheta/OneDrive/Desktop/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            save_path = str(screenshots_dir / filename)
        img = ImageGrab.grab()
        img.save(save_path)
        return f"Screenshot saved to: {save_path}"
    except Exception as e:
        return f"Screenshot error: {e}"


# ─────────────────────────────────────────────
# 5. Notes
# ─────────────────────────────────────────────

NOTES_FILE = Path("notes.txt")

def create_note(text: str) -> str:
    """Append a timestamped note to notes.txt in the Cipher folder."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"[{timestamp}] {text}\n"
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
        return f"Note saved: {text}"
    except Exception as e:
        return f"Note error: {e}"


def read_notes(last_n: int = 10) -> str:
    """Read the last N notes from notes.txt."""
    try:
        if not NOTES_FILE.exists():
            return "No notes yet. Say 'note: <something>' to create one."
        lines = NOTES_FILE.read_text(encoding="utf-8").strip().splitlines()
        recent = lines[-last_n:] if len(lines) > last_n else lines
        return "\n".join(recent) if recent else "No notes found."
    except Exception as e:
        return f"Read notes error: {e}"


# ─────────────────────────────────────────────
# 6. Reminder / Timer
# ─────────────────────────────────────────────

def set_reminder(minutes: float, message: str) -> str:
    """Set a reminder that fires a Windows toast notification after N minutes."""
    try:
        seconds = float(minutes) * 60

        def _fire():
            time.sleep(seconds)
            _send_toast(f"⏰ Reminder: {message}")

        t = threading.Thread(target=_fire, daemon=True, name=f"reminder_{message[:10]}")
        t.start()
        return f"Reminder set! I'll remind you in {minutes} minute(s): '{message}'"
    except Exception as e:
        return f"Reminder error: {e}"


def _send_toast(message: str):
    """Send a Windows toast notification via PowerShell."""
    ps = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText01
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
$xml.GetElementsByTagName("text")[0].AppendChild($xml.CreateTextNode("{message}")) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Jarvis")
$notifier.Show($toast);
"""
    try:
        subprocess.run(["powershell", "-Command", ps], capture_output=True, timeout=10)
    except Exception:
        pass  # Notification failure shouldn't crash the reminder


# ─────────────────────────────────────────────
# 7. System Control
# ─────────────────────────────────────────────

def system_control(action: str) -> str:
    """
    Perform a system power action.
    action: 'sleep', 'shutdown', 'restart', 'lock'
    """
    action = action.lower().strip()
    cmds = {
        "sleep":    "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
        "shutdown": "shutdown /s /t 30 /c \"Shutting down in 30 seconds. Run 'shutdown /a' to cancel.\"",
        "restart":  "shutdown /r /t 30 /c \"Restarting in 30 seconds. Run 'shutdown /a' to cancel.\"",
        "lock":     "rundll32.exe user32.dll,LockWorkStation",
        "cancel":   "shutdown /a",
    }
    cmd = cmds.get(action)
    if not cmd:
        return f"Unknown action '{action}'. Options: sleep, shutdown, restart, lock, cancel."
    try:
        subprocess.Popen(cmd, shell=True)
        if action == "sleep":
            return "Putting your PC to sleep."
        elif action == "shutdown":
            return "Your PC will shut down in 30 seconds. Say 'cancel shutdown' to stop it."
        elif action == "restart":
            return "Your PC will restart in 30 seconds. Say 'cancel shutdown' to stop it."
        elif action == "lock":
            return "Locking your PC."
        elif action == "cancel":
            return "Shutdown/restart cancelled."
    except Exception as e:
        return f"System control error: {e}"
