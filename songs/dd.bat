@echo off
setlocal EnableDelayedExpansion

echo Starting safe rename process...

REM Step 1: Rename everything to temporary names
set count=1
for /f "delims=" %%f in ('dir /b /a-d *.mp3 *.MP3 2^>nul') do (
    ren "%%f" "temp_!count!.mp3"
    set /a count+=1
)

REM Step 2: Rename temp files to final numbers
set count=1
for /f "delims=" %%f in ('dir /b /a-d temp_*.mp3') do (
    set num=000!count!
    set num=!num:~-3!
    ren "%%f" "!num!.mp3"
    set /a count+=1
)

echo.
echo ==========================
echo Renaming Completed!
echo Total files processed: %count%
echo ==========================
pause
