@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$root = [IO.Path]::GetFullPath((Get-Location).Path).TrimEnd('\'); $matches = Get-CimInstance Win32_Process -Filter 'Name = ''python.exe'' OR Name = ''pythonw.exe''' | Where-Object { $_.CommandLine -and $_.CommandLine.Contains('-m bot') -and $_.CommandLine.IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0 }; if (-not $matches) { Write-Host 'No bot process for this project is running.'; exit 0 }; $matches | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Stopped bot process ' + $_.ProcessId) }"
