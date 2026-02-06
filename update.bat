@echo off
setlocal

REM Aller dans le dossier du script
cd /d "%~dp0"

REM Activer l'environnement
./venv/scripts/activate.ps1

REM telecharge les changements
git pull
git checkout jean

REM Update 
cd generation_cpp
pip install .
cd..


./run.bat