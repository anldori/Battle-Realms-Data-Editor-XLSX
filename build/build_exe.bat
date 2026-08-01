@echo off
REM ============================================================================
REM  Battle Realms Data Editor (XLSX) - build a standalone .exe
REM
REM  Produces an executable that needs neither Python nor PyQt6 on the machine
REM  it runs on. Double-click this file and pick a layout.
REM
REM  This script lives in build\ but builds the project in the folder above it.
REM
REM  Icon:  drop an icon.ico next to this file (build\icon.ico) and it is used
REM         automatically. A copy in the project root also works.
REM
REM  Scripted use:  build_exe.bat 1   one folder    (asks nothing, no pause)
REM                 build_exe.bat 2   single file
REM ============================================================================
setlocal EnableExtensions
title Battle Realms Data Editor - build

set "HERE=%~dp0"
cd /d "%HERE%.."
set "ROOT=%CD%"

set "NAME=BattleRealmsDataEditor"
set "WORK=%HERE%_work"

echo ============================================================
echo   Battle Realms Data Editor - build a standalone .exe
echo ============================================================
echo.
echo Project folder: %ROOT%
echo.

if not exist "%ROOT%\br_editor.py" (
    echo [ERROR] br_editor.py was not found in:
    echo         %ROOT%
    echo.
    echo         Keep this script inside the project's build folder.
    echo.
    if "%~1"=="" pause
    exit /b 1
)

REM ---- 1. locate Python ------------------------------------------------------
set "PYCMD="
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYCMD=py -3"
)
if not defined PYCMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYCMD=python"
)
if not defined PYCMD (
    echo [ERROR] Python was not found. Run quick_start.bat first - it can
    echo         install Python for you.
    echo.
    if "%~1"=="" pause
    exit /b 1
)

REM ---- 2. make sure the build tools are there --------------------------------
%PYCMD% -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo Installing PyInstaller ^(first run only^)...
    echo.
    %PYCMD% -m pip install --upgrade pip --quiet
    %PYCMD% -m pip install pyinstaller
    if errorlevel 1 goto pip_failed
    echo.
)
%PYCMD% -c "import PyQt6, openpyxl" >nul 2>nul
if errorlevel 1 (
    echo Installing the editor's own dependencies...
    %PYCMD% -m pip install -r "%ROOT%\requirements.txt"
    if errorlevel 1 goto pip_failed
    echo.
)

REM ---- 3. pick a layout ------------------------------------------------------
set "MODE="
if "%~1"=="1" set "MODE=--onedir"
if /i "%~1"=="onedir" set "MODE=--onedir"
if "%~1"=="2" set "MODE=--onefile"
if /i "%~1"=="onefile" set "MODE=--onefile"
if defined MODE goto chosen

echo Which layout do you want?
echo.
echo    [1] One folder   dist\%NAME%\        starts instantly, about 90 MB
echo                     share the whole folder, or zip it
echo.
echo    [2] Single file  dist\%NAME%.exe     one portable file, about 45 MB
echo                     each launch takes a few seconds to unpack
echo.

set "MODE=--onedir"
where choice >nul 2>nul
if errorlevel 1 goto ask_fallback
choice /c 12 /n /m "Choose 1 or 2: "
if errorlevel 2 set "MODE=--onefile"
goto chosen

:ask_fallback
set "ANS=1"
set /p "ANS=Choose 1 or 2: "
if "%ANS%"=="2" set "MODE=--onefile"

:chosen
echo.

REM ---- 4. optional icon ------------------------------------------------------
REM  build\icon.ico wins, then icon.ico in the project root.
set "ICON="
if exist "%HERE%icon.ico" (
    set "ICON=--icon "%HERE%icon.ico""
    echo Icon: build\icon.ico
) else if exist "%ROOT%\icon.ico" (
    set "ICON=--icon "%ROOT%\icon.ico""
    echo Icon: icon.ico
) else (
    echo Icon: none found, using the default.
    echo       To use your own, put icon.ico next to this script.
)
echo.

REM ---- 5. build --------------------------------------------------------------
echo Building %MODE:--=% ... this takes a couple of minutes.
echo.

%PYCMD% -m PyInstaller "%ROOT%\br_editor.py" ^
    --name %NAME% ^
    %MODE% ^
    --windowed ^
    --noconfirm ^
    --clean ^
    %ICON% ^
    --distpath "%ROOT%\dist" ^
    --workpath "%WORK%" ^
    --specpath "%WORK%" ^
    --paths "%ROOT%" ^
    --collect-submodules openpyxl ^
    --exclude-module tkinter ^
    --exclude-module pytest ^
    --exclude-module PyQt6.QtQml ^
    --exclude-module PyQt6.QtQuick ^
    --exclude-module PyQt6.QtQuick3D ^
    --exclude-module PyQt6.QtWebEngineCore ^
    --exclude-module PyQt6.QtWebEngineWidgets ^
    --exclude-module PyQt6.QtMultimedia ^
    --exclude-module PyQt6.QtMultimediaWidgets ^
    --exclude-module PyQt6.QtCharts ^
    --exclude-module PyQt6.QtDataVisualization ^
    --exclude-module PyQt6.QtBluetooth ^
    --exclude-module PyQt6.QtNetworkAuth ^
    --exclude-module PyQt6.QtPositioning ^
    --exclude-module PyQt6.QtSensors ^
    --exclude-module PyQt6.QtSerialPort ^
    --exclude-module PyQt6.QtTest ^
    --exclude-module PyQt6.QtSql

if errorlevel 1 goto build_failed

echo.
echo ============================================================
echo   Build finished.
echo ============================================================
echo.
if "%MODE%"=="--onedir" (
    echo   Your program:  dist\%NAME%\%NAME%.exe
    echo   Share the whole  dist\%NAME%  folder.
) else (
    echo   Your program:  dist\%NAME%.exe
)
echo.
echo   Intermediate files sit in  build\_work  and can be deleted.
echo.
if "%~1"=="" pause
exit /b 0

:pip_failed
echo.
echo [ERROR] Could not install the build tools. Check your internet connection.
echo.
if "%~1"=="" pause
exit /b 1

:build_failed
echo.
echo [ERROR] The build failed. The PyInstaller output above says why.
echo.
if "%~1"=="" pause
exit /b 1
