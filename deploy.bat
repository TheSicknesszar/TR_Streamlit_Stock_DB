@echo off
REM =============================================================================
REM RefurbAdmin AI - Production Deployment Script
REM =============================================================================
REM Windows batch script for deploying RefurbAdmin AI
REM South African Context: POPIA Compliant
REM =============================================================================

setlocal enabledelayedexpansion

REM Configuration
set APP_NAME=RefurbAdmin AI
set APP_DIR=%~dp0
set VENV_DIR=%APP_DIR%.venv
set PYTHON_VERSION=3.12

REM Colors
set GREEN=[92m
set YELLOW=[93m
set RED=[91m
set RESET=[0m

echo %GREEN%
echo ============================================
echo   %APP_NAME% Deployment Script
echo ============================================
echo %RESET%

REM Check Python installation
echo %YELLOW%Checking Python installation...%RESET%
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%Error: Python not found. Please install Python %PYTHON_VERSION%.%RESET%
    echo Download from: https://www.python.org/downloads/
    exit /b 1
)

python --version
echo.

REM Create virtual environment
echo %YELLOW%Creating virtual environment...%RESET%
if not exist "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo %RED%Error: Failed to create virtual environment.%RESET%
        exit /b 1
    )
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists.
)
echo.

REM Activate virtual environment
echo %YELLOW%Activating virtual environment...%RESET%
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo %RED%Error: Failed to activate virtual environment.%RESET%
    exit /b 1
)
echo Virtual environment activated.
echo.

REM Upgrade pip
echo %YELLOW%Upgrading pip...%RESET%
python -m pip install --upgrade pip --quiet

REM Install production dependencies
echo %YELLOW%Installing production dependencies...%RESET%
pip install -r requirements-production.txt --quiet
if errorlevel 1 (
    echo %RED%Error: Failed to install dependencies.%RESET%
    exit /b 1
)
echo Dependencies installed successfully.
echo.

REM Copy environment file
echo %YELLOW%Setting up environment configuration...%RESET%
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo Environment file created from template.
        echo %YELLOW%IMPORTANT: Edit .env and update all configuration values!%RESET%
    )
) else (
    echo Environment file already exists.
)
echo.

REM Create necessary directories
echo %YELLOW%Creating directories...%RESET%
if not exist "logs" mkdir logs
if not exist "logs\audit" mkdir logs\audit
if not exist "logs\app" mkdir logs\app
if not exist "data" mkdir data
if not exist "data\backups" mkdir data\backups
if not exist "data\uploads" mkdir data\uploads
if not exist "data\cache" mkdir data\cache
echo Directories created.
echo.

REM Run database migrations
echo %YELLOW%Running database migrations...%RESET%
if exist "manage.py" (
    python manage.py migrate
    if errorlevel 1 (
        echo %YELLOW%Warning: Migration may have issues. Check output above.%RESET%
    )
) else (
    echo Skipping migrations - manage.py not found.
)
echo.

REM Create admin user (optional)
echo %YELLOW%Setup complete!%RESET%
echo.
echo %GREEN%============================================%RESET%
echo   Deployment Complete!
echo %GREEN%============================================%RESET%
echo.
echo Next steps:
echo 1. Edit .env file with your configuration
echo 2. Generate SECRET_KEY and JWT_SECRET_KEY
echo 3. Run: run_app.bat
echo.
echo For Docker deployment:
echo   docker-compose -f deployment\docker-compose.yml up -d
echo.
echo Support: support@refurbadmin.co.za
echo Website: www.refurbadmin.co.za
echo.

REM Deactivate virtual environment
call "%VENV_DIR%\Scripts\deactivate.bat"

endlocal
exit /b 0
