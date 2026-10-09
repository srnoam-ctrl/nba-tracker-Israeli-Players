@echo off
chcp 65001 >nul
title "Deni Avdija NBA Dashboard Server"

set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist %PYTHON_CMD% (
    set PYTHON_CMD=python
)

echo Starting NBA Channel 5 Tracker Live Server on http://localhost:5005...
start "" /b %PYTHON_CMD% server.py

timeout /t 2 /nobreak >nul
start "" "http://localhost:5005"
