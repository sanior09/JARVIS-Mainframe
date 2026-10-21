@echo off
chcp 65001 >nul
title J.A.R.V.I.S. Ngrok Tunnel Gateway
setlocal enabledelayedexpansion

echo ========================================================================
echo               J.A.R.V.I.S. NGROK SECURE TUNNEL GATEWAY
echo ========================================================================
echo.

set "TARGET_PORT=5050"
set "NGROK_BIN="

:: 1. Check local project bin
if exist "%~dp0..\bin\ngrok.exe" (
    set "NGROK_BIN=%~dp0..\bin\ngrok.exe"
)

:: 2. Check LocalAppData ngrok
if "!NGROK_BIN!"=="" (
    if exist "%LOCALAPPDATA%\ngrok\ngrok.exe" (
        set "NGROK_BIN=%LOCALAPPDATA%\ngrok\ngrok.exe"
    )
)

:: 3. Check UserProfile AppData ngrok
if "!NGROK_BIN!"=="" (
    if exist "%USERPROFILE%\AppData\Local\ngrok\ngrok.exe" (
        set "NGROK_BIN=%USERPROFILE%\AppData\Local\ngrok\ngrok.exe"
    )
)

:: 4. Fallback: check PATH (filtering out broken Python shims)
if "!NGROK_BIN!"=="" (
    for /f "tokens=*" %%i in ('where.exe ngrok 2^>nul') do (
        if "!NGROK_BIN!"=="" (
            set "CANDIDATE=%%i"
            echo !CANDIDATE! | findstr /i "Python313" >nul
            if errorlevel 1 (
                set "NGROK_BIN=!CANDIDATE!"
            )
        )
    )
)

if "!NGROK_BIN!"=="" (
    echo [ERROR] ngrok binary was not located.
    echo Please install ngrok or place ngrok.exe in the 'bin' folder.
    pause
    exit /b 1
)

echo [*] Ngrok Binary: "!NGROK_BIN!"
echo [*] Target Host: 127.0.0.1:!TARGET_PORT!
echo [*] Initializing HTTP Tunnel...
echo ========================================================================
echo.

"!NGROK_BIN!" http 127.0.0.1:!TARGET_PORT!
if errorlevel 1 (
    echo.
    echo [!] Ngrok tunnel terminated with error code !errorlevel!.
    pause
)
