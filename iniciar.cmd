@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
call :main %*
set "BANAMEX_RESULT=%ERRORLEVEL%"
if not "%BANAMEX_RESULT%"=="0" if not defined CI pause
exit /b %BANAMEX_RESULT%

:main
cd /d "%~dp0"
set "UV_ARCH="
if /I "%PROCESSOR_ARCHITECTURE%"=="AMD64" set "UV_ARCH=x86_64"
if /I "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "UV_ARCH=aarch64"
if /I "%PROCESSOR_ARCHITEW6432%"=="AMD64" set "UV_ARCH=x86_64"
if /I "%PROCESSOR_ARCHITEW6432%"=="ARM64" set "UV_ARCH=aarch64"
if not defined UV_ARCH (
  echo Se necesita Windows de 64 bits.
  exit /b 1
)
set "BANAMEX_UV_DIR=%~dp0.runtime\bootstrap\uv-0.13.9-%UV_ARCH%"
set "BANAMEX_UV_ZIP=%BANAMEX_UV_DIR%\uv.zip"
set "BANAMEX_UV_HASH=edd61f7f5728a56cc62455386661860bdfc7bab65872f39b0c25bdcc1d8e1beb"
if "%UV_ARCH%"=="aarch64" set "BANAMEX_UV_HASH=72eed595983a4d7d22d79f21065b0f4479cc7e5c7a89104bb410c8f47559a878"
if not exist "%BANAMEX_UV_DIR%\uv.exe" (
  if not exist "%BANAMEX_UV_DIR%" mkdir "%BANAMEX_UV_DIR%"
  echo Preparando Python privado. La primera ejecucion necesita internet.
  curl.exe --fail --location --retry 3 --output "%BANAMEX_UV_ZIP%" "https://github.com/astral-sh/uv/releases/download/0.13.9/uv-%UV_ARCH%-pc-windows-msvc.zip"
  if errorlevel 1 exit /b 1
  powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; if ((Get-FileHash -Algorithm SHA256 -LiteralPath $env:BANAMEX_UV_ZIP).Hash -ne $env:BANAMEX_UV_HASH) { throw 'SHA256 incorrecto al descargar uv' }; Expand-Archive -Force -LiteralPath $env:BANAMEX_UV_ZIP -DestinationPath $env:BANAMEX_UV_DIR"
  if errorlevel 1 exit /b 1
  del "%BANAMEX_UV_ZIP%"
)
set "UV_PYTHON_INSTALL_DIR=%~dp0.runtime\python"
set "UV_PYTHON_BIN_DIR=%~dp0.runtime\python-bin"
set "UV_CACHE_DIR=%~dp0.runtime\uv-cache"
"%BANAMEX_UV_DIR%\uv.exe" python install --no-bin --no-registry 3.13.18
if errorlevel 1 exit /b 1
set "BANAMEX_PYTHON="
"%BANAMEX_UV_DIR%\uv.exe" python find --managed-python 3.13.18 > "%BANAMEX_UV_DIR%\python-path.txt"
if errorlevel 1 exit /b 1
set /p "BANAMEX_PYTHON="<"%BANAMEX_UV_DIR%\python-path.txt"
if not defined BANAMEX_PYTHON exit /b 1
"%BANAMEX_PYTHON%" preparar.py --start %*
exit /b %ERRORLEVEL%
