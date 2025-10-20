@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat 
set PYTHONPATH=%cd%\src;%PYTHONPATH%
streamlit run src/myproject/app.py
pause
