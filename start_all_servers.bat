@echo off
echo ===================================================
echo Starting Enterprise AI Platform...
echo ===================================================

echo Starting API Gateway on Port 8000...
start "API Gateway" cmd /k "cd C:\Users\KalleChakradhar\Downloads\dify\enterprise-ai-platform && run_gateway.bat"

echo Starting NextChat Frontend on Port 3000...
start "NextChat Frontend" cmd /k "cd C:\Users\KalleChakradhar\Downloads\dify\enterprise-ai-platform\apps\nextchat && npm run dev"

echo ===================================================
echo Both servers are starting up in separate windows!
echo - API Gateway will be available at http://127.0.0.1:8000
echo - NextChat will be available at http://localhost:3000
echo ===================================================
pause
