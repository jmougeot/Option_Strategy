@echo off
echo ============================================
echo RECOMPILATION DU MODULE C++ AVEC DEBUG
echo ============================================

echo.
echo [1] Activation de l'environnement virtuel...
call .venv\Scripts\activate.bat

echo.
echo [2] Desinstallation de l'ancienne version...
pip uninstall strategy_metrics_cpp -y 2>nul

echo.
echo [3] Installation de pybind11...
pip install pybind11 --quiet

echo.
echo [4] Compilation du module C++...
cd src\myproject\strategy\cpp
pip install . --verbose 2>&1 | tee build_log.txt

echo.
echo [5] Verification de l'installation...
cd ..\..\..\..
pip show strategy_metrics_cpp

echo.
echo [6] Test de l'import...
python -c "import strategy_metrics_cpp; print('OK:', strategy_metrics_cpp.__file__)"

echo.
echo [7] Log de compilation sauvegarde dans: src\myproject\strategy\cpp\build_log.txt
echo.
echo ============================================
echo FIN DE LA RECOMPILATION
echo ============================================
pause
