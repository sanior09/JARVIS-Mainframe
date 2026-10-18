@echo off
chcp 65001 >nul
title J.A.R.V.I.S. RAM Cleaner
python c:\JARVIS\scripts\clear_ram.py
ping 127.0.0.1 -n 4 >nul
