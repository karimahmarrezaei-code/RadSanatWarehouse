@echo off
set QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer
set QTWEBENGINE_DISABLE_SANDBOX=1
cd /d "%~dp0"
start "" "%~dp0RadSanatWarehouse.exe"
