@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 scripts\setup_tunnel.py
) else (
  python scripts\setup_tunnel.py
)

set EXIT_CODE=%errorlevel%
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
