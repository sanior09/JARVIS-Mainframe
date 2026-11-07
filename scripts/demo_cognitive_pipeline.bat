@echo off
chcp 65001 > nul
title JARVIS AI Cognitive Pipeline Diagnostic
color 0B

cd /d "%~dp0.."
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

python scripts\demo_cognitive_pipeline.py

echo.
pause

