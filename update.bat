@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cls

echo.
echo ════════════════════════════════════════════════════════════
echo          🔄 MISE À JOUR - OPTION STRATEGY
echo ════════════════════════════════════════════════════════════
echo.

REM Vérifier Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Git n'est pas installé
    echo.
    echo 📥 Téléchargement de Git...
    
    set GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0.2-64-bit.exe
    set TEMP_DIR=%TEMP%\git_install
    
    if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
    
    powershell -Command "Invoke-WebRequest -Uri '%GIT_URL%' -OutFile '%TEMP_DIR%\Git-installer.exe'" 2>nul
    
    if exist "%TEMP_DIR%\Git-installer.exe" (
        echo ✅ Téléchargement terminé
        echo.
        echo 🚀 Installation de Git...
        start /wait "" "%TEMP_DIR%\Git-installer.exe" /SILENT
        del "%TEMP_DIR%\Git-installer.exe" >nul 2>&1
        echo ✅ Git installé
        echo.
    ) else (
        echo ❌ Échec du téléchargement
        echo � Installez Git manuellement: https://git-scm.com/download/win
        pause
        exit /b 1
    )
)

echo ✅ Git détecté
echo.

REM Vérifier le dépôt Git
if not exist ".git" (
    echo ❌ Pas un dépôt Git
    echo 💡 Clonez le projet: git clone https://github.com/jmougeot/Option_Strategy.git
    pause
    exit /b 1
)

REM Mise à jour
echo � Mise à jour depuis GitHub...
echo.

git pull origin main >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Modifications locales détectées
    echo.
    set /p save="Sauvegarder vos modifications? [O/N]: "
    if /i "!save!"=="O" (
        git stash >nul 2>&1
        echo ✅ Modifications sauvegardées
    ) else (
        git reset --hard HEAD >nul 2>&1
        git clean -fd >nul 2>&1
        echo ✅ Modifications abandonnées
    )
    echo.
    git pull origin main
)

echo.
echo ✅ Mise à jour terminée!
echo.

REM Mettre à jour les dépendances si nécessaire
if exist "venv\Scripts\activate.bat" (
    echo 📦 Mise à jour des dépendances...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet --disable-pip-version-check
    call deactivate
    echo ✅ Dépendances à jour
    echo.
)

REM Proposer de lancer l'application
set /p run="Lancer l'application? [O/N]: "
if /i "!run!"=="O" (
    call run.bat
) else (
    echo.
    echo ✅ Terminé
    pause
)
