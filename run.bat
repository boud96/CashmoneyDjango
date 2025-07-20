@echo off
echo Starting Django and Streamlit servers...

REM Pull latest changes from git
echo Pulling latest changes from git...
git pull
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start Django server in a new command window
start "Django Server" cmd /k "python manage.py runserver"

REM Wait a moment for Django to start
timeout /t 3 /nobreak >nul

REM Start Streamlit in a new command window
start "Streamlit Server" cmd /k "streamlit run home.py"

echo Both servers are starting...
echo Django: http://127.0.0.1:8000/
echo Streamlit: http://localhost:8501/
echo.
echo This window will close automatically in 3 seconds...
timeout /t 3 /nobreak >nul
