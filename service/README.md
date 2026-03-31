# Cipher Background Service

Run Cipher **24/7 in the background** — no terminal needed.  
Just say **"Cipher"** or **"Jarvis"** and it wakes up instantly.

---

## Quick Start

### 1. Install the service (once)

Open **PowerShell** in `d:\Cipher` and run:

```powershell
.\service\install_service.ps1
```

It will:
- Register a **Task Scheduler** job (`CipherAI`) that auto-starts on every login
- Offer to start the service **right now** without rebooting

### 2. That's it!

Cipher runs silently in the background. A **tray icon** appears in your system tray — look for the purple **C** logo.

---

## Tray Icon Menu

| Action | What it does |
|--------|-------------|
| 🟢 Status: Active | Service is running and listening |
| 📋 Open Logs | Opens `service/cipher_service.log` in Notepad |
| 🔁 Restart Service | Kills and relaunches the engine |
| ❌ Stop Cipher | Stops the service and removes the tray icon |

---

## Log File

All output is written to:
```
d:\Cipher\service\cipher_service.log
```
Rotates automatically at **5 MB** (keeps 3 backups).

---

## Auto-Restart Policy

If the engine crashes, the service waits and retries automatically:

| Crash # | Wait before retry |
|---------|------------------|
| 1st     | 30 seconds       |
| 2nd     | 60 seconds       |
| 3rd     | 120 seconds      |
| > 3rd   | 5-min cooldown, then resets |

---

## Uninstall

```powershell
.\service\uninstall_service.ps1
```

Removes the Task Scheduler entry and terminates any running process.  
Cipher can still be used manually via `.\cypher.bat`.

---

## Files

```
service/
  cipher_service.py     ← headless runner (auto-restart, logging)
  tray_icon.py          ← system tray icon (pystray)
  install_service.ps1   ← registers Task Scheduler job
  uninstall_service.ps1 ← removes Task Scheduler job
  cipher_service.log    ← generated at runtime
  cipher.pid            ← generated at runtime
  cipher_status.txt     ← generated at runtime (tray reads this)
```
