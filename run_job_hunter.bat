@echo off
title Job Hunter Bot
cd /d "%~dp0"

echo Starting Job Hunter Bot...
echo.

if not exist "job_hunter_env" (
    echo Virtual environment not found!
    echo Please run setup_job_hunter.py first.
    pause
    exit /b 1
)

call job_hunter_env\Scriptsctivate
python main.py

if errorlevel 1 (
    echo.
    echo Job Hunter Bot encountered an error.
    echo Check the log files in data/logs/ for details.
    pause
)
