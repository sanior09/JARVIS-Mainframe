@echo off
chcp 65001 > nul
title JARVIS - Auto Find Microphone
color 0B

cd /d "%~dp0.."
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

echo ===================================================
echo     [JARVIS] ระบบค้นหาไมโครโฟนอัตโนมัติ (Auto-Scanner)
echo ===================================================
echo.
echo โปรดเตรียมตัวพูดใส่ไมค์ หรือเคาะไมค์เบาๆ
echo.

python scripts\find_mic.py

echo.
pause
