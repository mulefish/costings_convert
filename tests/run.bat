@echo off
cd /d "%~dp0"
npx playwright test --reporter=list %*
pause
