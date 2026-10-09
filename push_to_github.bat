@echo off
chcp 65001 >nul
title Push NBA Tracker to GitHub

set "PATH=%LOCALAPPDATA%\Programs\MinGit\cmd;%LOCALAPPDATA%\Programs\MinGit\ucrt64\bin;%PATH%"

echo ========================================================
echo   Pushing NBA Israelis Tracker to GitHub...
echo   Repository: https://github.com/srnoam-ctrl/nba-tracker-Israeli-Players.git
echo ========================================================
echo.
echo If a GitHub sign-in window opens in your browser,
echo please click 'Sign in with your browser' to authorize.
echo.

git push -u origin main

echo.
if %ERRORLEVEL% equ 0 (
    echo ========================================================
    echo   SUCCESS! All files and 48h automation pushed to GitHub!
    echo ========================================================
) else (
    echo ========================================================
    echo   Push did not complete. Please check the error above.
    echo ========================================================
)
echo.
pause
