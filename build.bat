@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

title Inventory - Build

echo ============================================
echo              Inventory - Build
echo ============================================
echo.

echo [1/4] Comprobando Python...
set "PY_CMD="
py --version >nul 2>&1 && set "PY_CMD=py"
if not defined PY_CMD (
    python --version >nul 2>&1 && set "PY_CMD=python"
)

if not defined PY_CMD (
    echo Python no esta instalado. Descargando Python 3.13.15 desde python.org...
    set "PYTHON_INSTALLER=%TEMP%\inventory_python_3.13.15.exe"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.13.15/python-3.13.15-amd64.exe' -OutFile '%PYTHON_INSTALLER%'"
    if errorlevel 1 goto :python_error
    echo Instalando Python para el usuario actual...
    "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    if errorlevel 1 goto :python_error
    del /q "%PYTHON_INSTALLER%" >nul 2>&1
    set "PATH=%LocalAppData%\Programs\Python\Python313;%LocalAppData%\Programs\Python\Python313\Scripts;%PATH%"
    set "PY_CMD=py"
    py --version >nul 2>&1 || set "PY_CMD=python"
)

if not defined PY_CMD goto :python_error
%PY_CMD% --version

echo.
echo [2/4] Comprobando dependencias...
set "MISSING="
%PY_CMD% -c "import customtkinter" >nul 2>&1 || set "MISSING=!MISSING! customtkinter"
%PY_CMD% -c "import numpy" >nul 2>&1 || set "MISSING=!MISSING! numpy"
%PY_CMD% -c "import pandas" >nul 2>&1 || set "MISSING=!MISSING! pandas"
%PY_CMD% -c "import openpyxl" >nul 2>&1 || set "MISSING=!MISSING! openpyxl"
%PY_CMD% -c "import matplotlib" >nul 2>&1 || set "MISSING=!MISSING! matplotlib"
%PY_CMD% -c "import PyInstaller" >nul 2>&1 || set "MISSING=!MISSING! pyinstaller"

if defined MISSING (
    echo Faltan:%MISSING%
    echo Instalando unicamente lo que falta...
    %PY_CMD% -m pip install !MISSING!
    if errorlevel 1 goto :error
) else (
    echo Todas las dependencias ya estan instaladas.
    echo Se omite pip por completo.
)

echo.
echo [3/4] Comprobando el codigo...
%PY_CMD% -m py_compile main.py gui_app.py db.py analytics.py config.py
if errorlevel 1 goto :error

echo.
echo [4/4] Compilando Inventory.exe...
echo Esta version evita el escaneo masivo de submodulos de NumPy/Pandas/Matplotlib.
echo.

set "DOWNLOADS=%USERPROFILE%\Downloads"
set "WORK=%~dp0build"
if not exist "%DOWNLOADS%" mkdir "%DOWNLOADS%"

taskkill /F /IM Inventory.exe >nul 2>&1

%PY_CMD% -m PyInstaller inventory.spec --noconfirm --distpath "%DOWNLOADS%" --workpath "%WORK%"
if errorlevel 1 goto :error

if not exist "%DOWNLOADS%\Inventory.exe" goto :error

echo.
echo ============================================
echo  LISTO
echo  %DOWNLOADS%\Inventory.exe
echo ============================================
echo.
start "" explorer.exe /select,"%DOWNLOADS%\Inventory.exe"
pause
exit /b 0

:python_error
echo.
echo ============================================
echo  ERROR: no se pudo instalar o encontrar Python.
echo ============================================
echo.
echo Verifica que Windows permita descargar desde python.org y volve a ejecutar.
pause
exit /b 1

:error
echo.
echo ============================================
echo  ERROR: no se pudo compilar Inventory.exe
echo ============================================
echo.
echo Si PyInstaller muestra un error concreto, copialo completo para revisarlo.
pause
exit /b 1
