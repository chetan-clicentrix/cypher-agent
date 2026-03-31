# ============================================================
#  Cipher AI — Uninstall Background Service
# ============================================================
#
#  Run from PowerShell:
#      cd d:\Cipher
#      .\service\uninstall_service.ps1
#
# ============================================================

Write-Host ""
Write-Host "  ===========================================" -ForegroundColor Yellow
Write-Host "    Cipher AI - Service Uninstaller" -ForegroundColor Yellow
Write-Host "  ===========================================" -ForegroundColor Yellow
Write-Host ""

# ── Remove Scripts from Startup Folder ──────────────────────────────────────
$StartupFolder = [Environment]::GetFolderPath("Startup")
$VbsPath       = Join-Path $StartupFolder "Cipher_Service.vbs"
$LnkPath       = Join-Path $StartupFolder "Cipher_Service.lnk"

if (Test-Path $VbsPath) {
    Remove-Item $VbsPath -Force
    Write-Host "[+] Removed legacy Startup VBScript: $VbsPath" -ForegroundColor Green
}

if (Test-Path $LnkPath) {
    Remove-Item $LnkPath -Force
    Write-Host "[+] Removed Startup Shortcut: $LnkPath" -ForegroundColor Green
} else {
    Write-Host "[i] No Startup shortcut found." -ForegroundColor Cyan
}

# ── Remove old Task Scheduler entry if exists ────────────────────────────────
$oldTask = Get-ScheduledTask -TaskName "CipherAI" -ErrorAction SilentlyContinue
if ($oldTask) {
    Unregister-ScheduledTask -TaskName "CipherAI" -Confirm:$false
    Write-Host "[+] Removed legacy Task Scheduler entry." -ForegroundColor Green
}

# ── Kill any running cipher_service.py processes ─────────────────────────────
$ServiceDir = $PSScriptRoot
$PidFile    = Join-Path $ServiceDir "cipher.pid"

if (Test-Path $PidFile) {
    $pid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($pid) {
        Write-Host "[*] Terminating service process (PID $pid) ..." -ForegroundColor Yellow
        try {
            Stop-Process -Id [int]$pid -Force -ErrorAction SilentlyContinue
            Write-Host "[+] Process stopped." -ForegroundColor Green
        } catch {
            Write-Host "[i] Process already stopped." -ForegroundColor Cyan
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# ── Clean status file ─────────────────────────────────────────────────────────
$StatusFile = Join-Path $ServiceDir "cipher_status.txt"
if (Test-Path $StatusFile) {
    Remove-Item $StatusFile -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "  Cipher background service has been fully uninstalled." -ForegroundColor Green
Write-Host "  You can still run Cipher manually with: .\cypher.bat" -ForegroundColor Cyan
Write-Host ""
