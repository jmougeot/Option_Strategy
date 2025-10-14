@echo off
REM ============================================================================
REM Script de Lancement Rapide - Options Strategy Analyzer (Windows)
REM ============================================================================
REM Lance l'application Streamlit dans l'environnement virtuel
REM Usage: Double-cliquez sur run.bat
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

REM Lancer Streamlit
streamlit run app.py

pause
