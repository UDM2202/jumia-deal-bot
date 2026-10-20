@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set /p URL=Paste the Jumia product link: 
set /p AT=Sale start time (e.g. 10:00, or leave empty for now): 
if "%AT%"=="" (python run.py cart "%URL%") else (python run.py cart "%URL%" --at %AT%)
pause
