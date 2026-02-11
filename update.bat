@echo off
setlocal

REM Aller dans le dossier du script
cd /d "%~dp0"

REM telecharge les changements
git pull
git checkout jean

REM Clean rebuild C++ extension
call rebuild.bat

REM Update pip dependencies
.venv\Scripts\pip.exe install -r requirements.txt

REM Launch
call run.bat