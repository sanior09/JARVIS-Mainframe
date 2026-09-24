@echo off
chcp 65001 > nul
title JARVIS - Auto Find Microphone
color 0B

echo ===================================================
echo     [JARVIS] ระบบค้นหาไมโครโฟนอัตโนมัติ (Auto-Scanner)
echo ===================================================
echo.
echo โปรดเตรียมตัวพูดใส่ไมค์ หรือเคาะไมค์เบาๆ
echo.

python find_mic.py

echo.
pause
