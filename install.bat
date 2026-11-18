@echo off
setlocal
cd /d "%~dp0"
echo [1/3] создаю venv...
python -m venv .venv || goto :fail
echo [2/3] обновляю pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
echo [3/3] ставлю AcidCode и зависимости...
".venv\Scripts\python.exe" -m pip install -e . || goto :fail
echo.
echo готово. запускай: acidcode.cmd
pause
exit /b 0

:fail
echo.
echo установка упала. смотри вывод выше.
pause
exit /b 1
