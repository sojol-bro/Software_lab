@echo off
setlocal

echo ==============================
echo Starting Django Server...
echo ==============================

REM Go to Django project folder
cd /d "C:\Users\shahm\OneDrive\Desktop\SkillNet\Software_lab\job"

REM Run with venv Python (absolute path)
"C:\Users\shahm\OneDrive\Desktop\SkillNet\Software_lab\venv\Scripts\python.exe" -c "import PIL; print('Pillow:', PIL.__version__)"
"C:\Users\shahm\OneDrive\Desktop\SkillNet\Software_lab\venv\Scripts\python.exe" manage.py runserver

pause

REM http://127.0.0.1:8000/