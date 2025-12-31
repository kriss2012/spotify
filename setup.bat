@echo off
REM ============================================================================
REM SETUP SCRIPT FOR MUSIC PLAYER
REM ============================================================================
REM This script installs all required dependencies for the music player

echo.
echo ========================================
echo   MusicFlow - Music Player Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org
    pause
    exit /b 1
)

echo [1/4] Python detected successfully
echo.

REM Install pygame
echo [2/4] Installing pygame...
pip install pygame
if errorlevel 1 (
    echo ERROR: Failed to install pygame
    pause
    exit /b 1
)

REM Install Pillow
echo.
echo [3/4] Installing Pillow...
pip install pillow
if errorlevel 1 (
    echo ERROR: Failed to install Pillow
    pause
    exit /b 1
)

REM Install mutagen
echo.
echo [4/4] Installing mutagen...
pip install mutagen
if errorlevel 1 (
    echo ERROR: Failed to install mutagen
    pause
    exit /b 1
)

REM Create songs folder
echo.
echo Creating 'songs' folder...
if not exist "songs" (
    mkdir songs
    echo Folder created successfully!
) else (
    echo Folder already exists
)

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Add your MP3/WAV files to the 'songs' folder
echo 2. Run: python music_player.py
echo.
pause
