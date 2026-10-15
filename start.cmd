@echo off
rem Двойной клик: запускает start.ps1 (нужен Docker Desktop).
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 pause
