@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM Script d'Installation Automatique - Options Strategy Analyzer (Windows)
REM ============================================================================
REM Ce script installe tout ce qui est nécessaire pour lancer l'application
REM Usage: Double-cliquez sur install.bat ou lancez dans PowerShell
REM ============================================================================

echo.
echo ========================================================================
echo   Installation - Options Strategy Analyzer
echo ========================================================================
echo.

REM Étape 1: Vérifier Python
echo Verification de Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python 3 n'est pas installe ou pas dans le PATH
    echo.
    echo Ce script peut installer Python 3.11 automatiquement.
    echo.
    echo Options:
    echo   1. Installer automatiquement Python 3.11 ^(RECOMMANDE^)
    echo   2. Ouvrir le site web de telechargement manuel
    echo   3. Annuler
    echo.
    set /p choice="Votre choix (1-3): "
    
    if "!choice!"=="1" (
        echo.
        echo ========================================================================
        echo   Installation automatique de Python 3.11
        echo ========================================================================
        echo.
        
        REM Detecter l'architecture
        if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
            set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
        ) else (
            set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe
        )
        
        set INSTALLER=%TEMP%\python_installer.exe
        
        echo Telechargement de Python 3.11...
        echo URL: !PYTHON_URL!
        echo.
        
        REM Telecharger avec PowerShell
        powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!PYTHON_URL!' -OutFile '!INSTALLER!'}"
        
        if not exist "!INSTALLER!" (
            echo.
            echo ERREUR: Echec du telechargement
            echo Veuillez installer Python manuellement depuis python.org
            pause
            exit /b 1
        )
        
        echo.
        echo Installation de Python en cours...
        echo.
        pause
        
        REM Lancer l'installateur avec les options recommandees
        "!INSTALLER!" /passive InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1 Include_doc=0
        
        del "!INSTALLER!"
        
        echo.
        echo ========================================================================
        echo   Installation de Python terminee
        echo ========================================================================
        echo.
        echo IMPORTANT: Vous devez FERMER cette fenetre et en ouvrir une NOUVELLE
        echo            pour que Python soit reconnu dans le PATH.
        echo.
        echo Ensuite, executez a nouveau install.bat
        echo.
        pause
        exit /b 0
        
    ) else if "!choice!"=="2" (
        echo.
        echo Ouverture du site de telechargement de Python...
        start https://www.python.org/downloads/windows/
        echo.
        echo Instructions:
        echo   1. Telechargez Python 3.8 ou superieur
        echo   2. Lancez l'installateur
        echo   3. COCHEZ "Add Python to PATH" ^(tres important!^)
        echo   4. Cliquez sur "Install Now"
        echo   5. Une fois termine, relancez install.bat
        echo.
        pause
        exit /b 0
        
    ) else (
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
    )
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo OK: %PYTHON_VERSION% detecte
echo.

REM Étape 2: Créer l'environnement virtuel
echo Creation de l'environnement virtuel...
if exist "venv\" (
    echo Environnement virtuel deja existant, utilisation de celui-ci...
) else (
    python -m venv venv
    echo OK: Environnement virtuel cree
)
echo.

REM Étape 3: Activer l'environnement virtuel
echo Activation de l'environnement virtuel...
call venv\Scripts\activate.bat
echo OK: Environnement active
echo.

REM Étape 4: Mettre à jour pip
echo Mise a jour de pip...
python -m pip install --upgrade pip --quiet
echo OK: pip mis a jour
echo.

REM Étape 5: Installer les dépendances
echo Installation des dependances...
echo   - streamlit
echo   - plotly
echo   - pandas
pip install streamlit plotly pandas --quiet
if %errorlevel% neq 0 (
    echo ERREUR: Echec de l'installation des dependances
    pause
    exit /b 1
)
echo OK: Dependances installees
echo.

REM Étape 6: Générer la base de données
echo Generation de la base de donnees d'options...
if exist "generate_full_database.py" (
    python generate_full_database.py >nul 2>&1
    echo OK: Base de donnees generee (calls_export.json)
) else (
    echo ATTENTION: generate_full_database.py non trouve, etape ignoree
)
echo.

REM Étape 7: Créer le script de lancement
echo Creation du script de lancement...
(
echo @echo off
echo cd /d "%%~dp0"
echo call venv\Scripts\activate.bat
echo streamlit run src/app.py
echo pause
) > run.bat
echo OK: Script run.bat cree
echo.

REM Résumé
echo ========================================================================
echo   INSTALLATION TERMINEE AVEC SUCCES !
echo ========================================================================
echo.
echo Prochaines etapes:
echo.
echo   Pour lancer l'application:
echo   - Option 1: Double-cliquez sur run.bat
echo   - Option 2: Dans PowerShell:
echo       venv\Scripts\Activate.ps1
echo       streamlit run src/app.py
echo.
echo   L'application s'ouvrira automatiquement dans votre navigateur
echo   URL: http://localhost:8501
echo.
echo ========================================================================
echo.
pause
