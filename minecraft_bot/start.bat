@echo off
chcp 65001 >nul
title J.A.R.V.I.S. - Minecraft Companion Mode
color 0b

echo ======================================================================
echo           J.A.R.V.I.S. Minecraft Companion Launcher
echo ======================================================================
echo.
echo [วิธีใช้งาน]:
echo  1. เปิดเกม Minecraft เข้าสู่ World ของเจ้านายตามปกติ
echo  2. กดปุ่ม Esc -^> 'Open to LAN' (เปิดสู่แลน) -^> 'Start LAN World'
echo.
echo  * ระบบจะสแกนหาพอร์ต LAN อัตโนมัติ และส่ง J.A.R.V.I.S. เข้าเกมทันที!
echo  * สั่งงานในเกมได้โดยตรงผ่านช่องแชท (กด T) หรือสั่งด้วยเสียงผ่าน J.A.R.V.I.S.
echo ======================================================================
echo.

cd /d "c:\JARVIS\minecraft_bot"
node launch.js %1

echo.
pause
