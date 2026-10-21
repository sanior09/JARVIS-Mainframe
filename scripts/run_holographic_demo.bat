@echo off
title Holographic Gesture Engine
cd /d "%~dp0.."
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)
echo ==================================================
echo   Starting Holographic Gesture Engine Demo...
echo ==================================================
set PYTHONIOENCODING=utf-8
python modules\holographic_gestures.py
pause
