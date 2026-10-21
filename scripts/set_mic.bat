@echo off
chcp 65001 > nul
title JARVIS - Microphone Setup
color 0B

cd /d "%~dp0.."
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

echo ===================================================
echo       J.A.R.V.I.S. MICROPHONE SETUP UTILITY
echo ===================================================
echo.
python scripts\set_mic.py
echo.
echo ===================================================
echo Press any key to exit...
pause >nul
