@echo off
setlocal
cd /d "%~dp0"

echo Stopping the bot process for this project, if it is running...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$root = [IO.Path]::GetFullPath((Get-Location).Path).TrimEnd('\'); $matches = Get-CimInstance Win32_Process -Filter 'Name = ''python.exe'' OR Name = ''pythonw.exe''' | Where-Object { $_.CommandLine -and $_.CommandLine.Contains('-m bot') -and $_.CommandLine.IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0 }; $matches | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Stopped bot process ' + $_.ProcessId) }; if ($matches) { Start-Sleep -Seconds 2 }"
if errorlevel 1 (
    echo Could not inspect or stop the existing bot. Run stop_bot.bat manually, then start_bot.bat.
    pause
    exit /b 1
)

echo Starting the bot in a new window...
start "Telegram bot" "%~dp0start_bot.bat"
