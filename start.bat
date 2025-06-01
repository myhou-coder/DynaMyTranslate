@echo off
REM 启动前端Next.js（生产模式）
start "Next.js Frontend" cmd /k "cd front && npm run build && npm run start -- -H 0.0.0.0 -p 3000"

REM 启动后端Flask（指定Python环境）
start "Flask Backend" cmd /k "cd server && "D:\myenvs\translate\python.exe" app.py"

