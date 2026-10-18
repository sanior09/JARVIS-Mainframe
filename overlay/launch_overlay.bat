@echo off
title J.A.R.V.I.S. Overlay HUD — Launcher
color 0B
echo.
echo  ==========================================
echo   J.A.R.V.I.S. Floating Overlay HUD
echo   Nachapol Industries
echo  ==========================================
echo.

REM -- Locate Python from JARVIS venv if available --
SET JARVIS_ROOT=%~dp0..
SET VENV_PYTHON=%JARVIS_ROOT%\venv\Scripts\python.exe

IF EXIST "%VENV_PYTHON%" (
    SET PYTHON_EXE=%VENV_PYTHON%
) ELSE (
    SET PYTHON_EXE=python
)

echo [*] Using Python: %PYTHON_EXE%
echo.

REM -- Install dependencies if needed --
echo [*] Checking dependencies...
%PYTHON_EXE% -c "import PySide6" 2>nul
IF ERRORLEVEL 1 (
    echo [!] PySide6 not found. Installing...
    %PYTHON_EXE% -m pip install PySide6 PySide6-WebEngine --quiet
)

%PYTHON_EXE% -c "import pynput" 2>nul
IF ERRORLEVEL 1 (
    echo [!] pynput not found. Installing...
    %PYTHON_EXE% -m pip install pynput --quiet
)

%PYTHON_EXE% -c "import requests" 2>nul
IF ERRORLEVEL 1 (
    %PYTHON_EXE% -m pip install requests --quiet
)

echo.
echo [*] All dependencies ready. Launching HUD...
echo [*] Hotkey: Ctrl+Space to toggle
echo [*] Right-click tray icon to quit
echo.

REM -- Launch the overlay --
cd /d "%~dp0"
%PYTHON_EXE% main.py

echo.
echo [*] JARVIS Overlay exited.
pause
