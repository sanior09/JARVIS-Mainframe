@echo off
chcp 65001 >nul
title JARVIS Automated User Simulator - Modules Test Suite
echo =======================================================
echo    JARVIS MULTI-SYSTEM SIMULATOR - TEST FRAMEWORK
echo =======================================================
cd /d "%~dp0\.."
python tests\simulate_user_test.py %*
pause
