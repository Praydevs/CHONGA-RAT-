@echo off
setlocal
cd /d "%~dp0"
title Chonga Rat panel

where python >nul 2>nul
if errorlevel 1 goto nopython

rem "start-panel.bat lan" opens both listeners to the local network so agents
rem on other PCs can attach. Default stays loopback-only.
if /i "%~1"=="lan" goto lan

echo Loopback mode: this PC only. Run "start-panel.bat lan" to accept other PCs.
echo.
goto launch

:lan
set "PANEL_BIND=0.0.0.0"
set "AGENT_BIND=0.0.0.0"
echo LAN mode: binding 0.0.0.0 (all interfaces)
echo The server prints the exact LAN URL below, on the "lan" line.
echo Firewall, once, admin PowerShell:
echo   New-NetFirewallRule -DisplayName "Chonga Rat panel" -Direction Inbound -Protocol TCP -LocalPort 8787,8790 -Action Allow -Profile Private
echo.

:launch
rem open the browser a moment after the server starts listening
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8787/'"

echo Press Ctrl+C to stop.
echo.
python server\panel-server.py
goto :eof

:nopython
echo Python 3.10 or newer was not found on PATH.
echo Install it from https://www.python.org/downloads/ and run this file again.
pause
