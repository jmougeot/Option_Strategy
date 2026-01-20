@echo off
setlocal

REM Aller dans le dossier du script
cd /d "%~dp0"

REM Activer l'environnement virtuel s'il existe
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

REM Ajouter le dossier src au PYTHONPATH
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

REM Lancer l'application desktop
echo 🚀 Lancement de Option Strategy...
python desktop_app.py

endlocal
