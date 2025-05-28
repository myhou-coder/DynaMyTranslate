@echo off
REM 启动前端Next.js（生产模式）
start "Next.js Frontend" cmd /k "cd front && npm run dev"

REM 启动后端Flask（指定Python环境）
start "Flask Backend" cmd /k "cd server && "D:\myenvs\translate\python.exe" app.py"

