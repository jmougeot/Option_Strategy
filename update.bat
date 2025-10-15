@echo off
setlocal ENABLEDELAYEDEXPANSION

echo 🚀 Script de mise à jour Git

:: === 1) Vérifier si Git est installé ===
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ⬇️ Git n'est pas installé. Installation en cours...

    :: Vérifier si winget est dispo
    winget --version >nul 2>&1
    if %ERRORLEVEL%==0 (
        winget install --id Git.Git -e --source winget --silent --accept-package-agreements --accept-source-agreements
    ) else (
        echo ❌ Winget non disponible. Installe Git manuellement : https://git-scm.com/download/win
        pause
        exit /b 1
    )
)

:: === 2) Aller dans le dossier du repo ===
cd /d "%~dp0"

:: === 3) Vérifier si le dossier est déjà un repo Git ===
if not exist ".git" (
    echo 🆕 Ce dossier n'est pas encore un dépôt Git.
    git init

    :: Demander l'URL du remote
    set /p REMOTE_URL="https://github.com/jmougeot/Projet_innovation"
    git remote add origin "!REMOTE_URL!"

    :: Créer une première branche main si nécessaire
    git branch -M main

    :: Premier commit si vide
    git add .
    git commit -m "Initial commit"
    git push -u origin main
) else (
    echo ✅ Dépôt Git déjà initialisé.
)

:: === 4) Synchronisation ===
echo 🔄 Mise à jour du dépôt...
git pull origin main
git add .
git commit -m "Auto update" >nul 2>&1
git push origin main

echo ✅ Synchronisation terminée !
pause