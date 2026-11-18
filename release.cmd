@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
if not exist ".venv\Scripts\python.exe" goto :novenv
".venv\Scripts\python.exe" make_release.py
if errorlevel 1 goto :fail
echo.
echo done. put dist\latest.json and the zip into a shared folder or HTTP.
pause
exit /b 0

:novenv
echo venv not found. run install.bat first.
pause
exit /b 1

:fail
echo.
echo release build failed. see output above.
pause
exit /b 1
