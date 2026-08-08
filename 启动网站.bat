@echo off
chcp 65001 >nul
title Campus Intel Terminal - Local
cd /d "%~dp0"
echo.
echo  ============================================
echo    Campus Intel Terminal - Local Site
echo    http://localhost:8000/
echo    Closing this window stops the site.
echo  ============================================
echo.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 2; Start-Process 'http://localhost:8000/'"
python site_server.py
