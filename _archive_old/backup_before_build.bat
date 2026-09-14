@echo off
rem Backup before build - run this BEFORE replacing main.py and BEFORE building.
rem Close the application first!

echo ================================================
echo  Backup before build (close the app first!)
echo ================================================
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup_before_build.ps1"
set RC=%ERRORLEVEL%

if %RC% GEQ 8 (
    echo.
    echo BACKUP FAILED ^(robocopy code %RC%^). Do NOT build. Check messages above.
) else if %RC% NEQ 0 (
    echo.
    echo BACKUP FAILED ^(exit code %RC%^). Do NOT build. Check messages above.
) else (
    echo.
    echo BACKUP COMPLETED SUCCESSFULLY. You may now replace main.py and build.
)

echo.
pause
exit /b %RC%
