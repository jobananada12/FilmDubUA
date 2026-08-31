@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python не знайдено. Встанови Python 3.11+.
  pause
  exit /b 1
)
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Не вдалося встановити залежності.
  pause
  exit /b 1
)
python app.py
pause
