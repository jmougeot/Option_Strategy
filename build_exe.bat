@echo off
setlocal

REM ============================================================================
REM Build Option Strategy .exe avec Python 3.11 + blpapi
REM ============================================================================

cd /d "%~dp0"

echo.
echo ========================================================================
echo   Building Option Strategy Desktop App (.exe)
echo ========================================================================
echo.

REM Activer l'environnement virtuel
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ Environnement virtuel non trouve!
    echo    Lancez d'abord: install_py311.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

REM Vérifier la version de Python
python --version
echo.

REM Vérifier que blpapi est installé
python -c "import blpapi; print('✅ blpapi version:', blpapi.__version__)" 2>nul
if errorlevel 1 (
    echo ⚠️ blpapi non installe, installation...
    pip install --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/ blpapi
)

REM Vérifier que pyinstaller est installé
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installation de PyInstaller...
    pip install pyinstaller
)

REM Nettoyer les anciens builds
echo.
echo 🧹 Nettoyage des anciens builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM Construire l'exécutable
echo.
echo 📦 Construction de l'executable...
echo    Cela peut prendre plusieurs minutes...
echo.

pyinstaller ^
    --name "Option Strategy" ^
    --onedir ^
    --console ^
    --icon "assets\icon.ico" ^
    --add-data "src;src" ^
    --add-data "assets;assets" ^
    --add-data ".streamlit;.streamlit" ^
    --hidden-import streamlit ^
    --hidden-import streamlit.runtime ^
    --hidden-import streamlit.runtime.scriptrunner ^
    --hidden-import streamlit.runtime.scriptrunner.script_runner ^
    --hidden-import streamlit.web ^
    --hidden-import streamlit.web.cli ^
    --hidden-import streamlit.web.bootstrap ^
    --hidden-import plotly ^
    --hidden-import plotly.express ^
    --hidden-import plotly.graph_objects ^
    --hidden-import plotly.subplots ^
    --hidden-import pandas ^
    --hidden-import pandas._libs ^
    --hidden-import numpy ^
    --hidden-import webview ^
    --hidden-import blpapi ^
    --hidden-import bottle ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import pyarrow ^
    --hidden-import altair ^
    --hidden-import toml ^
    --hidden-import watchdog ^
    --hidden-import validators ^
    --hidden-import gitpython ^
    --hidden-import pydeck ^
    --collect-all streamlit ^
    --collect-all plotly ^
    --collect-all blpapi ^
    --collect-all pandas ^
    --collect-all altair ^
    --copy-metadata streamlit ^
    --noconfirm ^
    desktop_app.py

if errorlevel 1 (
    echo.
    echo ❌ Build failed!
    echo.
    echo Verifiez que:
    echo   1. Vous avez lance install_py311.bat d'abord
    echo   2. Python 3.11 est utilise (pas 3.13)
    echo   3. Toutes les dependances sont installees
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo   ✅ BUILD TERMINE!
echo ========================================================================
echo.
echo 📁 Executable: dist\Option Strategy\Option Strategy.exe
echo.
echo NOTE: Pour distribuer, copiez tout le dossier "dist\Option Strategy"
echo       Le Bloomberg Terminal doit etre installe sur la machine cible.
echo.
pause

endlocal
