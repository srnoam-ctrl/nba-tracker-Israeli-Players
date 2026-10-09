@echo off
chcp 65001 >nul
title "Deni Avdija and Channel 5 Tracker"
echo ========================================================
echo   Updating Deni Avdija NBA and Israeli TV Broadcast Tracker
echo ========================================================
echo.

set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if not exist %PYTHON_CMD% (
    set PYTHON_CMD=python
)

%PYTHON_CMD% run_tracker.py

echo.
echo ========================================================
echo   Done! To view the dashboard, open dashboard\index.html
echo ========================================================
pause
