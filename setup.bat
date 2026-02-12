@echo off
setlocal

echo ===================================================
echo   Missing Persons System - Automated Setup Script
echo ===================================================

REM Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

REM Create Virtual Environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
) else (
    echo [INFO] Virtual environment already exists.
)

REM Activate Virtual Environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate

REM Install Requirements
echo [INFO] Installing requirements...
pip install -r requirements.txt

REM Check for .env file
if not exist ".env" (
    echo [INFO] Creating .env file from template...
    (
        echo SECRET_KEY=django-insecure-change-me-12345
        echo DEBUG=True
        echo DB_ENGINE=django.db.backends.sqlite3
        echo DB_NAME=db.sqlite3
        echo ALLOWED_HOSTS=127.0.0.1,localhost
    ) > .env
    echo [INFO] .env file created with default settings.
    echo [WARNING] Please update .env with your actual database and API configurations if needed.
) else (
    echo [INFO] .env file found.
)

REM Run Migrations
echo [INFO] Running database migrations...
python manage.py migrate

REM Create Superuser (Interactive)
echo.
echo [INFO] Would you like to create a superuser (admin)?
echo Press Y to create, or any other key to skip.
set /p create_admin=
if /i "%create_admin%"=="Y" (
    python manage.py createsuperuser
)

echo.
echo ===================================================
echo   Setup Completed Successfully!
echo ===================================================
echo.
echo To run the server, use:
echo venv\Scripts\activate
echo python manage.py runserver
echo.
pause
