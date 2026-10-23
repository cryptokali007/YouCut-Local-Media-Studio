@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title YouCutOwn Studio
set "APP=%~dp0app"
set "PYTHON=%APP%\runtime\python.exe"
if not exist "%APP%\runtime\.setup-ready" goto setup
if not exist "%PYTHON%" goto setup
if not exist "%APP%\runtime\pythonw.exe" goto setup
if not exist "%APP%\bin\ffmpeg.exe" goto setup
if not exist "%APP%\bin\ffprobe.exe" goto setup
goto launch
:setup
echo YouCutOwn Studio - preparing your local installation.
call "%~dp0Install.bat" -NoPause
if errorlevel 1 (
  echo Setup did not finish. Review the message above, then run Install.bat again.
  pause
  exit /b 1
)
:launch
if "%~1"=="--smoke" goto smoke
start "" /b "%APP%\runtime\pythonw.exe" "%APP%\app.py"
exit /b 0
:smoke
"%PYTHON%" "%APP%\app.py" --smoke
exit /b %errorlevel%
