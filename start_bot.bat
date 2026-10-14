@echo off
setlocal
cd /d "%~dp0"

if not exist ".env" (
    echo ERROR: .env was not found.
    echo Copy .env.example to .env and fill in BOT_TOKEN and OWNER_ID first.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating the Python environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo ERROR: Python 3 was not found. Install Python 3.11 or newer.
        pause
        exit /b 1
    )
)

if not exist ".venv\bot-dependencies-installed" (
    echo Installing bot dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Dependency installation failed.
        pause
        exit /b 1
    )
    type nul > ".venv\bot-dependencies-installed"
)

echo Starting the Telegram bot. Keep this window open while it runs.
echo Press Ctrl+C to stop it.
"%~dp0.venv\Scripts\python.exe" -m bot
set "BOT_EXIT=%errorlevel%"
if "%BOT_EXIT%"=="0" exit /b 0
echo.
if "%BOT_EXIT%"=="3" (
    echo Another copy of the bot is already running. This window will not start a second one.
) else (
    echo The bot stopped with an error. Check the message above.
)
pause
exit /b %BOT_EXIT%
