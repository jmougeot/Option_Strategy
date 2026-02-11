@echo off
setlocal

REM ============================================================================
REM Rebuild C++ Extension - Clean build & recompile
REM ============================================================================

cd /d "%~dp0"

echo.
echo ========================================================================
echo   Rebuild C++ Extension (strategy_metrics_cpp)
echo ========================================================================
echo.

REM Clean old build artifacts
echo Cleaning build cache...
if exist "generation_cpp\build" (
    rmdir /s /q "generation_cpp\build"
    echo   - build/ removed
)
if exist "generation_cpp\strategy_metrics_cpp.egg-info" (
    rmdir /s /q "generation_cpp\strategy_metrics_cpp.egg-info"
    echo   - egg-info/ removed
)

REM Remove old .pyd files
for %%f in (generation_cpp\*.pyd) do (
    del /f "%%f"
    echo   - %%f removed
)

echo.
echo Compiling C++ extension...
echo.

REM Compile
cd generation_cpp
..\.venv\Scripts\python.exe setup.py build_ext --inplace
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Compilation failed!
    pause
    exit /b 1
)

cd ..

echo.
echo ========================================================================
echo   Rebuild complete!
echo ========================================================================
echo.
