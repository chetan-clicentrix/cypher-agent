@echo off
REM Cypher AI Assistant - Quick Start Script

echo.
echo ========================================
echo   Cypher AI Assistant
echo ========================================
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment...
    call venv\Scripts\activate.bat
    echo [+] Virtual environment activated!
    echo.
) else (
    echo [!] Virtual environment not found!
    echo [!] Please run: python -m venv venv
    pause
    exit /b 1
)

REM Run Cypher
echo [*] Starting Cypher...
echo.
python -m src.core.engine

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo [!] Cypher exited with an error
    pause
)
