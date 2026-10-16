@echo off
title Stop Agent AM
cd /d "%~dp0"
echo ========================================================
echo Stopping Agent AM Background Services...
echo ========================================================

powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*run_worker.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('Process stopped: ' + $_.ProcessId) }"

echo.
echo Agent AM has been stopped successfully.
pause
