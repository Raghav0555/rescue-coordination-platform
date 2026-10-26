@echo off
cd /d "%~dp0backend"
if not exist venv\Scripts\python.exe python -m venv venv
call venv\Scripts\activate.bat
pip install -q -r requirements.txt
cd /d "%~dp0frontend"
start "Frontend" cmd /k "python -m http.server 5500"
timeout /t 2 >nul
start http://localhost:5500/dashboard.html
start http://localhost:5500/field-app.html
cd /d "%~dp0backend"
uvicorn app.main:app --port 8000
pause
