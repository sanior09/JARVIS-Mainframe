@echo off
title JARVIS UI Test Mode
cd /d "%~dp0.."
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)
echo ==================================================
echo   Starting JARVIS UI Test Server...
echo ==================================================
start http://127.0.0.1:8080
python tests\test_ui.py
pause
