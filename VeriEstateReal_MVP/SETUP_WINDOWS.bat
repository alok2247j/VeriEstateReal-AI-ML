@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo VeriEstateReal - First-time setup
 echo ==============================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher ^(py^) was not found. Install Python 3.10-3.12 from python.org and enable Add Python to PATH.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -m venv .venv
if errorlevel 1 goto failed
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto failed
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
python train_model.py
if errorlevel 1 goto failed
python seed_demo.py
if errorlevel 1 goto failed
echo.
echo Setup completed. Now double-click START_APP.bat.
pause
exit /b 0
:failed
echo Setup stopped because a command failed. Copy the error message and ask for help.
pause
exit /b 1
