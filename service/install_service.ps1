# ============================================================
#  Cipher AI — Install Background Service (Startup Folder)
# ============================================================
#
#  Run this ONCE from PowerShell:
#      cd d:\Cipher
#      .\service\install_service.ps1
#
# ============================================================

param(
    [string]$RootDir = "",
    [string]$PythonExe = ""
)

if (-not $RootDir) {
    $RootDir = Split-Path $PSScriptRoot -Parent
}

if (-not $PythonExe) {
    $PythonExe = Join-Path $RootDir "venv\Scripts\python.exe"
}

# 1. Look for pythonw.exe instead of python.exe
$PythonwExe = $PythonExe -replace "python\.exe$", "pythonw.exe"

if (-not (Test-Path $PythonwExe)) {
    Write-Error "[!] Windowless Python not found at: $PythonwExe"
    exit 1
}

$ServiceScript = Join-Path $RootDir "service\cipher_service.py"

if (-not (Test-Path $ServiceScript)) {
    Write-Error "[!] Service script not found at: $ServiceScript"
    exit 1
}

$StartupFolder = [Environment]::GetFolderPath("Startup")
$VbsPath = Join-Path $StartupFolder "Cipher_Service.vbs"

Write-Host ""
Write-Host "  ===========================================" -ForegroundColor Cyan
Write-Host "    Cipher AI - Service Installer" -ForegroundColor Cyan
Write-Host "  ===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Method     : Windows Startup Folder (VBScript native hidden)"
Write-Host "  Engine     : $PythonExe"
Write-Host "  Script     : $ServiceScript"
Write-Host "  Startup Dir: $StartupFolder"
Write-Host ""

# ── Clean up old Task Scheduler & LNK entries ────────────────────────
$oldTask = Get-ScheduledTask -TaskName "CipherAI" -ErrorAction SilentlyContinue
if ($oldTask) {
    Write-Host "[*] Removing old Task Scheduler entry..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName "CipherAI" -Confirm:$false
}

$oldLnk = Join-Path $StartupFolder "Cipher_Service.lnk"
if (Test-Path $oldLnk) {
    Write-Host "[*] Removing deprecated .lnk entry..." -ForegroundColor Yellow
    Remove-Item $oldLnk -Force
}

# ── Create the VBScript (.vbs) ────────────────────────────────────
try {
    $VbsContent = @"
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.CurrentDirectory = "$RootDir"
objShell.Run """$PythonExe"" ""$ServiceScript""", 0, False
"@
    Set-Content -Path $VbsPath -Value $VbsContent -Encoding Ascii

    Write-Host "[+] VBScript created at: $VbsPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Cipher will now auto-start completely hidden at every Windows login."
    Write-Host ""

    # Offer to start immediately
    $startNow = Read-Host "  Start the service now? (y/N)"
    if ($startNow -match "^[yY]") {
        # Start the process directly via PowerShell
        Start-Process -FilePath $PythonExe -ArgumentList "`"$ServiceScript`"" -WorkingDirectory $RootDir -WindowStyle Hidden
        Write-Host "[+] Service started! Look for the purple C in your system tray." -ForegroundColor Green
    }
}
catch {
    Write-Error "[!] Failed to install startup script: $_"
    exit 1
}

