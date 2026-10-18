@echo off
title Holographic Gesture Engine
cd /d "%~dp0.."
echo ==================================================
echo   Starting Holographic Gesture Engine Demo...
echo ==================================================
set PYTHONIOENCODING=utf-8
python modules\holographic_gestures.py
pause
