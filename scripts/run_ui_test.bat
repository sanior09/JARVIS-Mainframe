@echo off
title JARVIS UI Test Mode
echo ==================================================
echo   Starting JARVIS UI Test Server...
echo ==================================================
start http://127.0.0.1:8080
python c:\JARVIS\tests\test_ui.py
pause
