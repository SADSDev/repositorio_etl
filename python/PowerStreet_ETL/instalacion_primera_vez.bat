
@echo off
setlocal

set "ROOT=%~dp0"

echo =================================
echo   CONFIGURACION DEL PROYECTO
echo =================================

if exist "%ROOT%.venv\" (
    echo Eliminando el entorno virtual anterior...
    rmdir /s /q "%ROOT%.venv"
    
    if errorlevel 1 (
        echo ERROR: No se pudo eliminar el entorno anterior.
        exit /b 1
    )
)

echo Creando entorno virtual...
python -m venv "%ROOT%.venv"

if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual.
    exit /b 1
)

if not exist "%ROOT%.venv\Scripts\python.exe" (
    echo ERROR: No se encontro Python dentro del entorno.
    exit /b 1
)

echo Activando entorno virtual...
call "%ROOT%.venv\Scripts\activate.bat"

if errorlevel 1 (
    echo ERROR: No se pudo activar el entorno virtual.
    exit /b 1
)

echo Entorno virtual listo.

echo Ejecutando configuracion inicial...
cd /d "%ROOT%set_up_primera_vez"

if errorlevel 1 (
    echo ERROR: No se encontro la carpeta de configuracion.
    exit /b 1
)

python set_up.py

if errorlevel 1 (
    echo ERROR: Fallo la configuracion inicial.
    exit /b 1
)

echo.
echo Configuracion completada correctamente.

exit /b 0
