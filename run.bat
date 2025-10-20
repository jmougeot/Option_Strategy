@echo off
REM ============================================================================
REM Script de Lancement Rapide - Options Strategy Analyzer (Windows)
REM ============================================================================

cd /d "%~dp0"

echo Lancement de l'application...

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat

REM Définir le PYTHONPATH pour Windows
set PYTHONPATH=%cd%\src;%PYTHONPATH%

REM Lancer Streamlit
streamlit run src/myproject/app.py

