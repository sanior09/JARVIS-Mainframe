@echo off
chcp 65001 >nul
setlocal
title J.A.R.V.I.S. Mainframe Interface

:: ==========================================
:: [JARVIS CONFIG]
:: ==========================================
cd /d "%~dp0"
set "PYTHONPATH=%~dp0;%~dp0modules;%PYTHONPATH%"

:: Define ANSI Escape Codes for Colors (High-tech Blue theme)
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set ESC=%%b
set "CYAN=%ESC%[36m"
set "BLUE=%ESC%[94m"
set "WHITE=%ESC%[97m"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "RESET=%ESC%[0m"

cls
echo.
echo %CYAN%  ========================================================================%RESET%
echo %BLUE%           _    _     _______      _______  _____ %RESET%
echo %BLUE%          ^| ^|  / \   ^|  __ \ \    / /_   _^|/ ____^|%RESET%
echo %BLUE%          ^| ^| /  \  ^| ^|__) \ \  / /  ^| ^| ^| (___  %RESET%
echo %BLUE%      _   ^| ^|/ /\ \ ^|  _  / \ \/ /   ^| ^|  \___ \ %RESET%
echo %BLUE%     ^| ^|__^| / ____ \^| ^| \ \  \  /   _^| ^|_ ____) ^|%RESET%
echo %BLUE%      \____/_/    \_\_^|  \_\  \/   ^|_____^|_____/ %RESET%
echo %CYAN%  ========================================================================%RESET%
echo %WHITE%                JUST A RATHER VERY INTELLIGENT SYSTEM%RESET%
echo %CYAN%                    Powered by Nachapol Industries%RESET%
echo.
echo %CYAN%  [ SYSTEM BOOT SEQUENCE INITIATED ]%RESET%
echo.

:: Simulate loading
echo %WHITE%  [!] Initializing Cognitive Matrix...%RESET%
ping 127.0.0.1 -n 2 >nul
echo %WHITE%  [!] Establishing Neural Pathways...%RESET%
ping 127.0.0.1 -n 2 >nul
echo %WHITE%  [!] Loading Autonomous Evolution Protocol...%RESET%
ping 127.0.0.1 -n 2 >nul
echo.

echo %CYAN%  [ VERIFYING SYSTEM INTEGRITY ]%RESET%
:: ตรวจสอบ Python Installation
for /f "tokens=*" %%i in ('python -c "import site; print(site.getsitepackages()[0])" 2^>nul') do set "PY_SITE_PACKAGES=%%i"
if defined PY_SITE_PACKAGES (
    if exist "%PY_SITE_PACKAGES%" (for /d %%i in ("%PY_SITE_PACKAGES%\~*") do rd /s /q "%%i" >nul 2>&1)
)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%  [FATAL ERROR] Python interpreter not found in PATH.%RESET%
    echo %RED%  Please install Python 3.10+ and reboot the system.%RESET%
    pause
    exit /b 1
)
echo %GREEN%  [*] Core Engine: Python Verified.%RESET%
python scripts\boot_fx.py --status "Core Runtime: Python Environment" "ONLINE"

:: ตรวจสอบและติดตั้ง Dependencies ที่จำเป็น
set "REQUIRED_PACKAGES=langchain_core langgraph beautifulsoup4 python-dotenv chromadb psutil requests waitress duckduckgo_search langgraph-checkpoint-sqlite pyautogui opencv-python mediapipe aiohttp websockets line-bot-sdk groq apscheduler sqlalchemy"

for %%P in (%REQUIRED_PACKAGES%) do (
    python -m pip show %%P >nul 2>&1
    if %errorlevel% neq 0 (
        echo %CYAN%  [!] Synthesizing missing neural component: %%P...%RESET%
        python -m pip install %%P >nul
        if %errorlevel% neq 0 (
            echo %RED%  [ERROR] Component synthesis failed: %%P.%RESET%
            pause
            exit /b 1
        ) else (
          echo %GREEN%  [*] Neural component integrated: %%P.%RESET%
        )
    )
)

python scripts\boot_fx.py --status "Neural Dependencies: 19/19 Packages" "SYNCED"
echo.

echo %CYAN%  [ PURGING TEMPORARY CACHE ]%RESET%
del /s /q *.log >nul 2>&1
python scripts\boot_fx.py --status "System Cache & Execution Logs" "OPTIMIZED"
echo.

:: ตรวจสอบว่าไฟล์ jarvis.py มีอยู่จริงหรือไม่ในไดเรกทอรีปัจจุบัน
if not exist "jarvis.py" (
    echo %RED%  [FATAL ERROR] Core Logic File 'jarvis.py' is missing.%RESET%
    pause
    exit /b 1
)

:: เริ่มรัน Windows Autonomous Agent ใน Background
if exist "modules\agent_windows_core.py" (
    start /b "" pythonw modules\agent_windows_core.py
    python scripts\boot_fx.py --status "Windows Autonomous Desktop Agent" "ENGAGED"
) else if exist "agent_windows_core.py" (
    start /b "" pythonw agent_windows_core.py
    python scripts\boot_fx.py --status "Windows Autonomous Desktop Agent" "ENGAGED"
)

echo.
echo %CYAN%  [ SYNAPSE CALIBRATION SEQUENCE ]%RESET%
python scripts\boot_fx.py --bar "Loading Neural Matrix & Synaptic Buffer" 0.75
echo.
python scripts\boot_fx.py --status "Synaptic Knowledge Store (ChromaDB)" "CONNECTED"
python scripts\boot_fx.py --status "Local Named Pipe Bus (\\.\pipe\island)" "LISTENING"
python scripts\boot_fx.py --status "24/7 Watchdog Supervisor" "STANDBY"

echo.
echo %CYAN%  ========================================================================%RESET%
python scripts\boot_fx.py --type "  ALL SYSTEMS ONLINE. J.A.R.V.I.S. IS NOW LISTENING..." green 0.016
python scripts\boot_fx.py --type "  \"Good day, Sir. All cognitive systems are fully operational.\"" cyan 0.020
echo %CYAN%  ========================================================================%RESET%
echo %WHITE%  [!] Live telemetry running. Press Ctrl+C in this window to terminate.%RESET%
echo.

:: Boot the Watchdog instead of jarvis.py directly
python jarvis_watchdog.py

echo.
echo %RED%  [!] J.A.R.V.I.S. session ended (Exit Code: %errorlevel%).%RESET%
echo %CYAN%  Press any key to close this terminal window...%RESET%
pause >nul