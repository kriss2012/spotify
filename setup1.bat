@echo off
REM ============================================================================
REM RUN MUSICFLOW (music_player.py)
REM ============================================================================
REM This script launches the music player GUI (music_player.py) using the system Python.

cd /d "%~dp0"
echo ========================================
echo   MusicFlow - Launch
echo ========================================
echo.
echo Attempting to run music_player.py...

REM Prefer `python` if available, otherwise try `py` launcher.
where python >nul 2>nul
if %errorlevel%==0 (
	start "" cmd /k python "music_player.py"
) else (
	where py >nul 2>nul
	if %errorlevel%==0 (
		start "" cmd /k py "music_player.py"
	) else (
		echo.
		echo ERROR: Python was not found on your PATH.
		echo Please install Python from https://python.org and ensure it's added to PATH.
	)
)

echo.
echo Launcher started (or error shown above).
echo Press any key to close this window.
pause >nul
