@echo off
setlocal

REM Aller dans le dossier du script
cd /d "%~dp0"

REM Activer l'environnement virtuel s'il existe
if exist "venv\Scripts\activate.bat" (
	call "venv\Scripts\activate.bat"
)

REM Ajouter le dossier src au PYTHONPATH (format Windows)
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

REM Utiliser le Python du venv si disponible
set "PY_EXE=python"
if exist "venv\Scripts\python.exe" (
	set "PY_EXE=venv\Scripts\python.exe"
)

REM Lancer l'application Streamlit
"%PY_EXE%" -m streamlit run "src\myproject\app.py"

endlocal
pause
