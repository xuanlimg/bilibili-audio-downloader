@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo ?????????
    pause
    exit /b 1
)
".venv\Scripts\python.exe" "bilibili_audio_app.py"
if errorlevel 1 pause
