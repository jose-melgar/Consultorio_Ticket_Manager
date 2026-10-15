@echo off
setlocal
chcp 65001 >nul
title Sistema de Tickets - Consultorio Las Marianas
cd /d "%~dp0"
set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    echo ERROR: Falta el entorno Python. Consulte docs\README.md.
    pause
    exit /b 1
)
if not exist "backend\build\index.html" (
    echo ERROR: Falta compilar la interfaz. Consulte docs\README.md.
    pause
    exit /b 1
)
echo Iniciando sistema local. Use Ctrl+C para apagar correctamente.
"%PYTHON_EXE%" -B backend\app.py --open-browser
if errorlevel 1 (
    echo No se pudo iniciar el sistema. Revise el mensaje anterior.
    pause
    exit /b 1
)
endlocal
