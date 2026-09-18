@echo off
title Fly Brain App Launcher
cd /d "%~dp0"

echo ========================================
echo   Setting up Fly Brain App Environment
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python and make sure to check "Add Python to PATH".
    echo.
    pause
    exit /b
)

:: Install required dependencies
echo Checking and installing required packages...
pip install --upgrade PySide6 keyring neuprint-python

echo.
echo ========================================
echo   Launching Fly Brain App...
echo ========================================
echo.

:: Run the application
python fly_brain_app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application closed with an error.
)

echo.
pause
