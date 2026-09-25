@echo off
REM Starts the Scoute engine and web app in two windows (after first-time setup in README).
start "Scoute engine" cmd /k "cd /d %~dp0engine && venv\Scripts\activate && uvicorn app.main:app --port 8000"
start "Scoute web" cmd /k "cd /d %~dp0web && npm run dev"
timeout /t 8 >nul
start http://localhost:3000
