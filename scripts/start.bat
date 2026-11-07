@echo off
rem Windows one-click start / verify
rem   scripts\start.bat          create .venv, install deps, start server (default port 8051)
rem   scripts\start.bat verify   run unit tests + startup verification
setlocal
cd /d "%~dp0.."
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if exist ".venv\Scripts\python.exe" goto :deps
set "PY=python"
python -c "import sys" >nul 2>&1 || set "PY=py -3"
echo [setup] creating virtualenv .venv ...
%PY% -m venv .venv || goto :fail

:deps
echo [setup] installing dependencies ...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :fail

if /i "%~1"=="verify" goto :verify
".venv\Scripts\python.exe" run.py
goto :eof

:verify
".venv\Scripts\python.exe" -m pip install -q pytest || goto :fail
echo [verify] running unit tests ...
".venv\Scripts\python.exe" -m pytest -q || goto :fail
echo [verify] startup verification ...
".venv\Scripts\python.exe" scripts\verify.py --spawn || goto :fail
echo [verify] OK
goto :eof

:fail
echo [x] failed, see the messages above. Python 3.10+ is required (tick "Add Python to PATH").
exit /b 1
