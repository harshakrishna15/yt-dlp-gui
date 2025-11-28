@echo off
setlocal
set ROOT=%~dp0..
pushd "%ROOT%"

if not defined PYTHON set PYTHON=python
echo Creating venv with %PYTHON%...
%PYTHON% -m venv .venv
call .venv\Scripts\activate.bat

echo Upgrading pip...
pip install --upgrade pip

echo Installing requirements...
pip install -r requirements.txt

echo Setup complete.
echo Activate: call .venv\Scripts\activate
echo Run: python run_gui.py
echo If you see _tkinter errors, install Python from python.org (includes Tk).

popd
endlocal
