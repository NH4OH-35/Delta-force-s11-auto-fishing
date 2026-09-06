@echo off
setlocal
cd /d "%~dp0"
echo Output-device isolation test
py -m pip install soundcard numpy scipy
if errorlevel 1 goto install_failed
py "%~dp0test_output_isolation.py"
echo.
pause
exit /b 0

:install_failed
echo Required package installation failed.
pause
exit /b 1
