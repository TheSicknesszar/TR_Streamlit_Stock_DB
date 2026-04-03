@echo off
REM RefurbAdmin AI - Frontend Launcher
REM South African IT Refurbishment Inventory & Pricing Platform
REM
REM This batch file:
REM 1. Creates a virtual environment if it doesn't exist
REM 2. Installs frontend dependencies
REM 3. Launches the Streamlit dashboard
REM
REM Usage: run_frontend.bat

echo ============================================
echo   RefurbAdmin AI - Frontend Dashboard
echo   South African IT Refurbishment Platform
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Python found...
python --version
echo.

REM Navigate to project directory
cd /d "%~dp0"

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo [2/4] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo [2/4] Virtual environment found...
)
echo.

REM Activate virtual environment
echo [3/4] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo.

REM Install frontend dependencies
echo [4/4] Installing frontend dependencies...
pip install -q --upgrade pip
pip install -q -r frontend\requirements.txt
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
    echo Continuing anyway...
)
echo.

REM Ensure data directory exists
if not exist "data" mkdir data

REM Ensure logs directory exists
if not exist "logs" mkdir logs

echo ============================================
echo   Starting Streamlit Dashboard...
echo   
echo   Dashboard URL: http://localhost:8501
echo   
echo   Press Ctrl+C to stop the server
echo ============================================
echo.

REM Launch Streamlit
streamlit run frontend\app.py --server.headless true --server.port 8501

REM If Streamlit exits, pause to show any errors
if errorlevel 1 (
    echo.
    echo ERROR: Streamlit exited with an error
    pause
)
