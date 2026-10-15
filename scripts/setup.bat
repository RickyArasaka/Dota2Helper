@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo               DotaBlitz Setup Wizard
echo ========================================================

cd /d "%~dp0\.."

:: 1. Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python is not installed or not in PATH! Please install Python 3.11+.
    pause
    exit /b 1
)

:: 2. Create virtual environment
if not exist "venv" (
    echo [*] Creating virtual environment (venv)...
    python -m venv venv
)

:: 3. Activate venv & install packages
echo [*] Installing dependencies from requirements.txt...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 4. Install Dota 2 GSI configuration
echo [*] Installing Dota 2 Game State Integration configuration...
python scripts\install_gsi.py

echo.
echo ========================================================
echo [✓] Setup completed successfully!
echo To start DotaBlitz, run:
echo     venv\Scripts\activate
echo     python run.py
echo ========================================================
pause
