@echo off
setlocal
cd /d "%~dp0"
echo This test will press F6 once after five seconds.
echo Make sure Delta Force binds cast/reel to F6.
echo Press any key, then switch to the game.
pause >nul
py "%~dp0test_action_key.py"
echo.
pause
