@echo off
REM ========================================
REM WORKFLOW QUOTIDIEN - DIX PLATFORM
REM ========================================

echo.
echo ========================================
echo  WORKFLOW QUOTIDIEN - DIX PLATFORM
echo ========================================
echo  Date: %date% %time%
echo ========================================
echo.

REM Se placer dans le répertoire du script
cd /d "%~dp0"

REM Lancer le workflow master
python workflow_master.py

REM Vérifier le code de sortie
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo  WORKFLOW TERMINE AVEC SUCCES
    echo ========================================
    echo.
) else (
    echo.
    echo ========================================
    echo  WORKFLOW TERMINE AVEC ERREURS
    echo ========================================
    echo.
)

REM Pause pour voir les résultats (retirer pour automatisation)
pause
