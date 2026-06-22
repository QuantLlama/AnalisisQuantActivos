@echo off
REM =============================================================================
REM setup_env.bat — Configuración automática del entorno (Windows)
REM =============================================================================

echo ==============================================
echo   FLUX Quant — Setup de Entorno
echo ==============================================

REM Verificar Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.10+
    exit /b 1
)

FOR /F "tokens=2" %%i IN ('python --version') DO SET PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% encontrado.

REM Crear entorno virtual
IF NOT EXIST ".venv" (
    echo [...] Creando entorno virtual .venv ...
    python -m venv .venv
    echo [OK] Entorno virtual creado.
) ELSE (
    echo [OK] Entorno virtual ya existe.
)

REM Activar entorno
call .venv\Scripts\activate.bat
echo [OK] Entorno virtual activado.

REM Actualizar pip
python -m pip install --upgrade pip --quiet

REM Instalar dependencias
echo [...] Instalando dependencias...
pip install -r requirements.txt

REM Crear directorios
IF NOT EXIST ".cache" mkdir .cache
IF NOT EXIST "logs" mkdir logs
IF NOT EXIST "exports" mkdir exports
IF NOT EXIST "data\raw" mkdir data\raw

echo.
echo ==============================================
echo   Setup completado exitosamente!
echo.
echo   Para activar el entorno:
echo     .venv\Scripts\activate.bat
echo.
echo   Para iniciar el sistema:
echo     flux
echo.
echo   Para iniciar el Dashboard Web:
echo     flux web
echo ==============================================
