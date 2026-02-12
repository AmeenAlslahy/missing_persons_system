#!/bin/bash

echo "==================================================="
echo "  Missing Persons System - Automated Setup Script"
echo "==================================================="

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    exit 1
fi

# Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[INFO] Virtual environment already exists."
fi

# Activate Virtual Environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Install Requirements
echo "[INFO] Installing requirements..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "[INFO] Creating .env file from template..."
    cat <<EOF > .env
SECRET_KEY=django-insecure-change-me-12345
DEBUG=True
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
ALLOWED_HOSTS=127.0.0.1,localhost
EOF
    echo "[INFO] .env file created with default settings."
    echo "[WARNING] Please update .env with your actual database and API configurations if needed."
else
    echo "[INFO] .env file found."
fi

# Run Migrations
echo "[INFO] Running database migrations..."
python manage.py migrate

# Create Superuser (Interactive)
echo ""
read -p "[INFO] Would you like to create a superuser (admin)? (y/n): " create_admin
if [[ "$create_admin" =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

echo ""
echo "==================================================="
echo "  Setup Completed Successfully!"
echo "==================================================="
echo ""
echo "To run the server, use:"
echo "source venv/bin/activate"
echo "python manage.py runserver"
echo ""
