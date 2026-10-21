@echo off
title JARVIS Dynamic Island Test
cd /d "%~dp0.."
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)
python modules\dynamic_island.py
pause
