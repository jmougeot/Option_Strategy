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
pip install -r requirements.txt
echo.
echo Installation de Bloomberg API (blpapi)...
pip install --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/ blpapi --quiet
if %errorlevel% neq 0 (
    echo ERREUR: Echec de l'installation des dependances
    pause
    exit /b 1
)
echo OK: Dependances installees
echo.

REM Étape 6: Compilation du module C++ (acceleration des calculs)
echo ========================================================================
echo   Compilation du module C++ (acceleration des calculs)
echo ========================================================================
echo.

REM Detecter l'architecture pour les options de compilation
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    set ARCH=x64
    set ARCH_BITS=64 bits
    set MINGW_ARCH=x86_64
) else if "%PROCESSOR_ARCHITECTURE%"=="ARM64" (
    set ARCH=arm64
    set ARCH_BITS=ARM 64 bits
    set MINGW_ARCH=aarch64
) else (
    set ARCH=x86
    set ARCH_BITS=32 bits
    set MINGW_ARCH=i686
)
echo Architecture detectee: !ARCH! (!ARCH_BITS!)
echo.

REM Verifier si un compilateur C++ est disponible (g++ ou cl.exe)
set CPP_COMPILER=
where g++.exe >nul 2>&1
if %errorlevel% equ 0 (
    set CPP_COMPILER=g++
    echo Compilateur trouve: g++ ^(MinGW/GCC^)
    goto :compile_cpp
)

where cl.exe >nul 2>&1
if %errorlevel% equ 0 (
    set CPP_COMPILER=cl
    echo Compilateur trouve: cl.exe ^(MSVC^)
    goto :compile_cpp
)

REM Aucun compilateur trouve, essayer d'installer MinGW via winget
echo Aucun compilateur C++ trouve.
echo.
echo Installation automatique de MinGW-w64 ^(GCC pour Windows^)...
echo.

REM Verifier si winget est disponible
where winget.exe >nul 2>&1
if %errorlevel% neq 0 (
    echo winget non disponible. Installation manuelle requise.
    echo.
    echo Options d'installation:
    echo   1. MinGW-w64: https://www.mingw-w64.org/downloads/
    echo   2. Visual Studio Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo.
    echo L'application fonctionnera en mode Python pur ^(plus lent^)
    goto :skip_cpp
)

REM Installer MinGW via winget selon l'architecture
echo Installation de MinGW-w64 pour !ARCH! via winget...
if "!ARCH!"=="x64" (
    winget install -e --id MSYS2.MSYS2 --accept-package-agreements --accept-source-agreements >nul 2>&1
    if %errorlevel% equ 0 (
        echo MSYS2 installe. Installation de MinGW-w64...
        REM Ajouter MinGW au PATH pour cette session
        set "PATH=C:\msys64\mingw64\bin;!PATH!"
        
        REM Installer gcc via pacman si MSYS2 est present
        if exist "C:\msys64\usr\bin\bash.exe" (
            "C:\msys64\usr\bin\bash.exe" -lc "pacman -S --noconfirm mingw-w64-x86_64-gcc" >nul 2>&1
        )
    )
) else (
    winget install -e --id MSYS2.MSYS2 --accept-package-agreements --accept-source-agreements >nul 2>&1
)

REM Alternative: installer directement MinGW64 standalone
if not defined CPP_COMPILER (
    echo Tentative installation MinGW standalone...
    winget install -e --id mingw.mingw-w64-gcc-llvm --accept-package-agreements --accept-source-agreements >nul 2>&1
    
    REM Actualiser le PATH
    for %%p in ("C:\mingw64\bin" "C:\Program Files\mingw64\bin" "C:\msys64\mingw64\bin") do (
        if exist "%%~p\g++.exe" (
            set "PATH=%%~p;!PATH!"
            set CPP_COMPILER=g++
            echo MinGW trouve dans %%~p
            goto :compile_cpp
        )
    )
)

REM Verifier a nouveau apres installation
where g++.exe >nul 2>&1
if %errorlevel% equ 0 (
    set CPP_COMPILER=g++
    echo OK: g++ installe avec succes
    goto :compile_cpp
)

echo.
echo ATTENTION: Installation automatique du compilateur echouee.
echo            Vous pouvez l'installer manuellement:
echo.
echo   Option 1 - MinGW-w64 ^(recommande^):
echo       winget install MSYS2.MSYS2
echo       Puis dans MSYS2: pacman -S mingw-w64-!MINGW_ARCH!-gcc
echo.
echo   Option 2 - Visual Studio Build Tools:
echo       winget install Microsoft.VisualStudio.2022.BuildTools
echo.
echo L'application fonctionnera en mode Python pur ^(plus lent^)
goto :skip_cpp

:compile_cpp
echo.
echo Installation de pybind11...
pip install pybind11 --quiet

echo.
echo Compilation du module strategy_metrics_cpp pour !ARCH! avec !CPP_COMPILER!...
pushd src\myproject\strategy\cpp

REM Nettoyer les anciennes compilations
if exist build rmdir /s /q build 2>nul
if exist strategy_metrics_cpp.egg-info rmdir /s /q strategy_metrics_cpp.egg-info 2>nul

REM Desinstaller l'ancienne version si elle existe
pip uninstall strategy_metrics_cpp -y 2>nul

REM Compiler et installer
pip install . --quiet 2>nul

popd

REM Verifier l'installation
python -c "import strategy_metrics_cpp; print('OK: Module C++ installe avec succes')" 2>nul
if %errorlevel% neq 0 (
    echo ATTENTION: La compilation C++ a echoue, mode Python pur sera utilise
    echo            ^(L'application fonctionnera, mais sera plus lente^)
)

:skip_cpp
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
