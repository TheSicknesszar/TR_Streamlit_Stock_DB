@echo off
REM =============================================================================
REM RefurbAdmin AI - Windows Launcher
REM =============================================================================
REM This batch file creates a virtual environment and runs the FastAPI application.
REM South African IT Refurbishment Inventory & Pricing Platform
REM =============================================================================

setlocal EnableDelayedExpansion

echo.
echo =============================================================================
echo                    RefurbAdmin AI - Startup
echo =============================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [INFO] Python found
python --version
echo.

REM Set project directory
set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

REM Virtual environment path
set VENV_DIR=%PROJECT_DIR%.venv

REM Check if virtual environment exists
if not exist "%VENV_DIR%" (
    echo [INFO] Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created
    echo.
) else (
    echo [INFO] Virtual environment already exists
    echo.
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

echo [SUCCESS] Virtual environment activated
echo.

REM Install/upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo [INFO] Installing dependencies...
if exist "%PROJECT_DIR%requirements.txt" (
    pip install -r "%PROJECT_DIR%requirements.txt" --quiet
    if errorlevel 1 (
        echo [WARNING] Some dependencies may have failed to install
    )
) else (
    echo [WARNING] requirements.txt not found
)
echo [SUCCESS] Dependencies installed
echo.

REM Create .env file if it doesn't exist
if not exist "%PROJECT_DIR%.env" (
    echo [INFO] Creating .env file from .env.example...
    if exist "%PROJECT_DIR%.env.example" (
        copy "%PROJECT_DIR%.env.example" "%PROJECT_DIR%.env" >nul
        echo [SUCCESS] .env file created - Please review and update settings
    ) else (
        echo [WARNING] .env.example not found - Creating default .env
        (
            echo APP_NAME=RefurbAdmin AI
            echo APP_ENV=development
            echo DEBUG=True
            echo DATABASE_URL=sqlite+aiosqlite:///./data/refurbadmin_dev.db
            echo SECRET_KEY=dev-secret-key-change-in-production
        ) > "%PROJECT_DIR%.env"
    )
    echo.
)

REM Create data directories
echo [INFO] Creating data directories...
if not exist "%PROJECT_DIR%data" mkdir "%PROJECT_DIR%data"
if not exist "%PROJECT_DIR%data\raw" mkdir "%PROJECT_DIR%data\raw"
if not exist "%PROJECT_DIR%data\processed" mkdir "%PROJECT_DIR%data\processed"
if not exist "%PROJECT_DIR%data\cache" mkdir "%PROJECT_DIR%data\cache"
if not exist "%PROJECT_DIR%data\logs" mkdir "%PROJECT_DIR%data\logs"
echo [SUCCESS] Data directories ready
echo.

REM Display configuration
echo =============================================================================
echo                         Configuration
echo =============================================================================
echo Project Directory: %PROJECT_DIR%
echo Environment: Development
echo Database: SQLite (development)
echo API Docs: http://localhost:8000/docs
echo.

REM Start the application
echo =============================================================================
echo                    Starting RefurbAdmin AI
echo =============================================================================
echo.
echo [INFO] Starting FastAPI server on http://localhost:8000
echo [INFO] API Documentation: http://localhost:8000/docs
echo [INFO] ReDoc: http://localhost:8000/redoc
echo [INFO] Press Ctrl+C to stop the server
echo.

REM Run the application with uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

REM If we get here, the server was stopped
echo.
echo [INFO] Server stopped
pause
