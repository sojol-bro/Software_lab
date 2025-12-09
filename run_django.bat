@echo off
echo ==============================
echo Starting Django Server...
echo ==============================

REM Go to project folder (quotes handle spaces)
cd /d "C:\Users\saharier\Desktop\United International University\10th semester\WEB\Web-Programming-team-main"

REM Activate virtual environment
call "venv\Scripts\activate.bat"

REM Go to job folder
cd job

REM Run Django server
python manage.py runserver

pause
REM http://127.0.0.1:8000/