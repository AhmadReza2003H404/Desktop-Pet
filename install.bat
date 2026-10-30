@echo off
rem Desktop Pets installer for Windows: makes a virtual environment, installs PySide6,
rem adds "Desktop Pets" to the Start Menu, and starts it.
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during setup. Then run install.bat again.
    pause
    exit /b 1
)

%PY% -c "import sys; sys.exit(sys.version_info < (3, 10))"
if errorlevel 1 (
    echo Desktop Pets needs Python 3.10 or newer.
    %PY% --version
    pause
    exit /b 1
)

echo ==^> Creating virtual environment in .venv
%PY% -m venv .venv || goto :failed

echo ==^> Installing PySide6 (this can take a minute)
.venv\Scripts\python.exe -m pip install --upgrade pip >nul
.venv\Scripts\python.exe -m pip install -r requirements.txt || goto :failed

echo ==^> Adding Desktop Pets to the Start Menu
.venv\Scripts\python.exe main.py --install || goto :failed

echo ==^> Starting your pet!
start "" .venv\Scripts\pythonw.exe main.py
echo Done. Next time, open "Desktop Pets" from the Start Menu.
pause
exit /b 0

:failed
echo.
echo Something went wrong (see the messages above).
pause
exit /b 1
