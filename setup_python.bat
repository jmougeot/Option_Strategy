@echo off
REM ============================================================================
REM Script d'installation automatique de Python 3 pour Windows
REM ============================================================================
REM Ce script verifie si Python 3 est installe et guide l'utilisateur
REM pour l'installer automatiquement si necessaire.
REM ============================================================================

setlocal enabledelayedexpansion

echo ==========================================
echo   Verification de Python 3
echo ==========================================
echo.

REM Verifier si Python est installe
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Verification de la version de Python...
    for /f "tokens=2" %%V in ('python --version 2^>^&1') do set PYTHON_VERSION=%%V
    
    REM Extraire la version majeure et mineure
    for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
        set PYTHON_MAJOR=%%a
        set PYTHON_MINOR=%%b
    )
    
    REM Verifier si la version est 3.8+
    if !PYTHON_MAJOR! geq 3 (
        if !PYTHON_MINOR! geq 8 (
            echo [32m✓ Python !PYTHON_VERSION! est deja installe[0m
            echo.
            echo [32m✓ Aucune installation necessaire[0m
            echo.
            echo Vous pouvez maintenant lancer l'installation du projet:
            echo   install.bat
            pause
            exit /b 0
        )
    )
    
    echo [33m⚠ Python !PYTHON_VERSION! trouve, mais version 3.8+ requise[0m
    echo.
) else (
    echo [31m✗ Python 3 n'est pas installe[0m
    echo.
)

REM Python n'est pas installe ou version incorrecte
echo ==========================================
echo   Installation de Python 3
echo ==========================================
echo.
echo Ce script va telecharger et installer Python 3.11 (version recommandee)
echo.
echo Options:
echo   1. Installer automatiquement Python 3.11 (RECOMMANDE)
echo   2. Ouvrir le site web de telechargement manuel
echo   3. Annuler
echo.
set /p choice="Votre choix (1-3): "

if "%choice%"=="1" goto auto_install
if "%choice%"=="2" goto manual_install
if "%choice%"=="3" goto cancel
echo Choix invalide
goto cancel

:auto_install
echo.
echo Telechargement de Python 3.11...
echo.

REM Detecter l'architecture
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    set ARCH=amd64
) else (
    set ARCH=win32
)

REM URL de telechargement pour Python 3.11.9 (derniere version stable)
if "%ARCH%"=="amd64" (
    set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
) else (
    set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe
)

set INSTALLER=%TEMP%\python_installer.exe

echo Telechargement depuis: %PYTHON_URL%
echo.

REM Telecharger avec PowerShell
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%INSTALLER%'}"

if not exist "%INSTALLER%" (
    echo.
    echo [31m✗ Echec du telechargement[0m
    echo.
    echo Veuillez installer Python manuellement depuis python.org
    pause
    exit /b 1
)

echo.
echo Installation de Python...
echo.
echo IMPORTANT: L'installateur va s'ouvrir.
echo           Assurez-vous de cocher "Add Python to PATH" !
echo.
pause

REM Lancer l'installateur avec les options recommandees
"%INSTALLER%" /passive InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1 Include_doc=0

echo.
echo Nettoyage...
del "%INSTALLER%"

echo.
echo ==========================================
echo   Installation terminee
echo ==========================================
echo.
echo IMPORTANT: Vous devez FERMER cette fenetre et en ouvrir une NOUVELLE
echo            pour que Python soit reconnu dans le PATH.
echo.
echo Ensuite, executez:
echo   install.bat
echo.
pause
exit /b 0

:manual_install
echo.
echo Ouverture du site de telechargement de Python...
start https://www.python.org/downloads/windows/
echo.
echo Instructions:
echo   1. Telechargez Python 3.8 ou superieur
echo   2. Lancez l'installateur
echo   3. COCHEZ "Add Python to PATH" (tres important!)
echo   4. Cliquez sur "Install Now"
echo   5. Une fois termine, relancez ce script
echo.
pause
exit /b 0

:cancel
echo.
echo Installation annulee.
echo.
echo Pour installer Python manuellement:
echo   1. Visitez https://www.python.org/downloads/
echo   2. Telechargez Python 3.8+
echo   3. Lors de l'installation, cochez "Add Python to PATH"
echo   4. Relancez install.bat
echo.
pause
exit /b 1
