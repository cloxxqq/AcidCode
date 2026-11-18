@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
if not exist ".venv\Scripts\python.exe" goto :novenv
".venv\Scripts\python.exe" -m acidcode %*
endlocal
exit /b %errorlevel%

:novenv
echo venv not found. run install.bat once.
pause
exit /b 1
