@echo off
title Agent AM - The Bayaan YouTube Manager
cd /d "%~dp0"
if not exist logs mkdir logs
echo ========================================================
echo Agent AM (The Bayaan YouTube Channel Manager)
echo Background Server & Autonomous Scheduler is starting...
echo ========================================================
".\venv\Scripts\python.exe" main.py >> "logs\agent_runner.log" 2>&1
