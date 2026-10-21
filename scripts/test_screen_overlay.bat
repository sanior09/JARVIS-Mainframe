@echo off
title JARVIS Screen Takeover Overlay Test
cd /d "%~dp0.."
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)
echo ========================================================
echo  JARVIS Screen Border Glow & Status Pill Test
echo  Press ESC or Click the Red Stop Button [■] to exit
echo ========================================================
python modules\jarvis_screen_takeover_overlay.py --test
pause
