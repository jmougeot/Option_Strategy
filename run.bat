@echo off
REM ============================================================================
REM Script de Lancement Rapide - Options Strategy Analyzer (Windows)
REM ============================================================================

cd /d "%~dp0"

echo.
echo Lancement de l'application...
echo.

REM Vérifier si l'environnement virtuel existe
if not exist "venv\" (
    echo ERREUR: Environnement virtuel non trouve !
    echo.
    echo Executez d'abord: install.bat
    echo.
    pause
    exit /b 1
)

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat

REM Définir le PYTHONPATH pour Windows
set PYTHONPATH=%cd%\src;%PYTHONPATH%

REM Lancer Streamlit
streamlit run src/myproject/app.py

