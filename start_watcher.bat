@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
title Jumia deal bot - keep this window open
:loop
python run.py watch
echo Bot stopped. Restarting in 30 seconds... (close this window to quit)
timeout /t 30
goto loop
