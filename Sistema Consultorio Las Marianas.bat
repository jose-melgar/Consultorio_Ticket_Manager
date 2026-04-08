@echo off
title Sistema de Tickets - Consultorio Las Marianas
setlocal enabledelayedexpansion

:: 1. Detectar la ruta de esta carpeta de forma absoluta
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo ======================================================
echo   CARGANDO SISTEMA UNIFICADO...
echo ======================================================

:: 2. Localizar el Python en el entorno virtual (venv)
set "PYTHON_EXE="
if exist "%ROOT_DIR%venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%venv\Scripts\python.exe"
) else if exist "%ROOT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"
)

if "%PYTHON_EXE%"=="" (
    echo.
    echo ERROR: No se encontro el entorno virtual 'venv' en la raiz.
    pause
    exit
)

:: 3. Iniciar el Sistema (Backend + Frontend juntos)
echo [1/1] Iniciando Servidor en puerto 5000...
cd backend
:: Ejecutamos de forma oculta/segundo plano
start /B "" "%PYTHON_EXE%" app.py >nul 2>&1

:: 4. Abrir el navegador
:: Esperamos solo 3 segundos porque ahora es mucho mas rapido
ping 127.0.0.1 -n 4 >nul
start http://localhost:5000

echo.
echo ======================================================
echo   SISTEMA ACTIVO (Puerto 5000)
echo ======================================================
echo   Para apagar el sistema, cierra esta ventana.
echo ======================================================
pause >nul
exit