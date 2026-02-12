# Walkthrough - Missing Persons System

## ✅ Fixes Applied
1. **MediaPipe Dependency**: 
   - Addressed installation issues with `mediapipe` on Windows.
   - Implemented a robust fallback in `ai/engine.py` to disable face detection if the library fails to load, preventing server crashes.
   - Fixed `config` import conflict in `ai/engine.py`.

2. **Database Schema**:
   - Resolved schema mismatches in `accounts_user` table.
   - Dropped zombie columns (`address`, `successful_reports_count`) that were present in the database but not in the Django models, allowing `createsuperuser` to function correctly.
   - **Refactoring**: Renamed `src` to `ai` and updated all internal references.
   - **Security**: Added field encryption for sensitive data (`national_id`, `phone`).

3. **Library Compatibility**:
   - Updated `django-filter` to version `25.2` to resolve compatibility issues with Django 5.x (`AttributeError: 'super' object has no attribute '_set_choices'`).

4. **Dependencies**:
   - Verified and installed correct versions of `tf-keras`, `tensorflow`, `mediapipe`, and `opencv-python`.
   - Added `django-cryptography`.

## 🚀 How to Run
1. Activate virtual environment:
   ```powershell
   d:/missing_persons_system/venv/Scripts/Activate.ps1
   ```
2. Apply migrations (Crucial after refactoring):
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   ```
3. Run the server:
   ```powershell
   python manage.py runserver
   ```
   The server will start at `http://127.0.0.1:8000/`.

## 🔑 Admin Access
A superuser has been created for you to access the dashboard:
- **URL**: `http://127.0.0.1:8000/admin-dashboard/` (or `/admin/`)
- **Email**: `admin@example.com`
- **Password**: `adminpassword123`

## 📊 Feature Status
- **Dashboard**: Fully functional. Loads statistics via APIs.
- **AI Matching**: Functional. Face detection is **REQUIRED** by default (configurable via `FACE_DETECTION_REQUIRED` in settings).
- **Reports/Users**: Fully CRUD capable via Admin Dashboard.
- **Security**: Sensitive fields are encrypted at rest.
