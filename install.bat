@echo off
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
    echo Voulez-vous l'installer automatiquement ? (O/N)
    set /p response="Votre choix: "
    if /i "!response!"=="O" (
        echo.
        echo Lancement de l'installation automatique de Python...
        call setup_python.bat
        if %errorlevel% neq 0 (
            echo.
            echo ERREUR: L'installation de Python a echoue
            pause
            exit /b 1
        )
        echo.
        echo Relancez install.bat pour continuer l'installation
        pause
        exit /b 0
    ) else (
        echo.
        echo Installation annulee.
        echo Veuillez installer Python 3.8+ manuellement depuis python.org
        echo IMPORTANT: Cochez "Add Python to PATH" lors de l'installation !
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
