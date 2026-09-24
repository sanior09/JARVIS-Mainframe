@echo off
chcp 65001 >nul
title J.A.R.V.I.S. Mobile Server (Expo Go)
color 0B
echo.
echo ==============================================================
echo        J.A.R.V.I.S. MOBILE PROTOCOL INITIALIZED
echo ==============================================================
echo.
echo [!] Starting React Native (Expo) Server in OFFLINE MODE...
echo [!] This bypasses the Expo login requirement.
echo [!] Please wait for the QR Code to appear.
echo [!] Use your iPhone's camera to scan the QR Code.
echo.

echo [!] Synchronizing Host IP with Mobile Config...
python "%~dp0sync_mobile_ip.py"
echo.

cd /d "%~dp0..\jarvis-mobile"
call npx expo start --lan --clear

pause
