@echo off
title ScamShield Server
cd /d "%~dp0"
echo Starting ScamShield...
start "" cmd /c "timeout /t 2 >nul && start http://localhost:8000"
python server.py
if errorlevel 1 (
  echo.
  echo Python command failed. Trying py launcher...
  py server.py
)
pause
