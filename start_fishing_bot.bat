@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto python_found
)

where python >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto python_found
)

echo Python was not found.
echo Install Python from https://www.python.org/downloads/windows/
pause
exit /b 1

:python_found
echo Checking required Python packages...
%PYTHON_CMD% -c "import soundcard, numpy, scipy, keyboard" >nul 2>nul
if not errorlevel 1 goto packages_ready

echo Installing required Python packages...
%PYTHON_CMD% -m pip install soundcard numpy scipy keyboard
if errorlevel 1 goto install_failed

:packages_ready
echo Starting fishing bot...
%PYTHON_CMD% "%~dp0fishing_bot.py"
echo.
pause
exit /b 0

:install_failed
echo.
echo Package installation failed. Check your internet connection and Python installation.
pause
exit /b 1
