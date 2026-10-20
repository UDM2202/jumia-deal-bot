@echo off
cd /d "%~dp0"
echo Setting up the Jumia deal bot...
py -m venv .venv || (echo Python not found. Install it from python.org and tick "Add to PATH". & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
if not exist secrets.yaml copy secrets.example.yaml secrets.yaml
echo.
echo Done! Now open secrets.yaml in Notepad and paste your Telegram token.
pause
