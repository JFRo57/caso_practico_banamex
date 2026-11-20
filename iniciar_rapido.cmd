@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
py -3 -c "import sys, ensurepip; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if errorlevel 1 goto bootstrap
py -3 preparar.py --start --quick %*
set "BANAMEX_QUICK_RESULT=%ERRORLEVEL%"
if not "%BANAMEX_QUICK_RESULT%"=="0" if not defined CI pause
exit /b %BANAMEX_QUICK_RESULT%
:bootstrap
call iniciar.cmd --quick %*
exit /b %ERRORLEVEL%
