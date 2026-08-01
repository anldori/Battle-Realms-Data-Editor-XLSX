@echo off
REM ============================================================================
REM  Battle Realms Data Editor - build a standalone Windows .exe
REM
REM  Double-click this file. It installs PyInstaller if needed, then packages
REM  the editor so it runs on machines with no Python installed.
REM
REM  Output goes to the "dist" folder next to this script.
REM ============================================================================
setlocal
cd /d "%~dp0"
title Build Battle Realms Data Editor

set "APPNAME=BattleRealmsDataEditor"
set "VCHECK=import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)"

echo ============================================================
echo   Build Battle Realms Data Editor  --^>  .exe
echo ============================================================
echo.

REM ---- 1. find Python --------------------------------------------------------
call :find_python
if not defined PYCMD goto no_python

set "PYFOUND="
for /f "delims=" %%V in ('%PYCMD% -c "import sys;print(sys.version.split()[0])" 2^>nul') do set "PYFOUND=%%V"
echo Using Python %PYFOUND%
echo.

REM ---- 2. dependencies ------------------------------------------------------
%PYCMD% -c "import PyQt6, openpyxl" >nul 2>nul
if not errorlevel 1 goto have_deps
echo Installing the editor's dependencies...
%PYCMD% -m pip install -r requirements.txt
if errorlevel 1 goto pip_failed
echo.
:have_deps

%PYCMD% -c "import PyInstaller" >nul 2>nul
if not errorlevel 1 goto have_pyinstaller
echo Installing PyInstaller ^(build tool, first time only^)...
%PYCMD% -m pip install pyinstaller
if errorlevel 1 goto pip_failed
echo.
:have_pyinstaller

REM ---- 3. choose the packaging mode -----------------------------------------
echo Choose how to package the editor:
echo.
echo    [1] One folder   - dist\%APPNAME%\  ^(recommended^)
echo                       Starts instantly. Share the whole folder,
echo                       or zip it. About 90 MB on disk.
echo.
echo    [2] Single file  - dist\%APPNAME%.exe
echo                       One portable file, easy to hand around.
echo                       About 45 MB, but each launch takes a few
echo                       seconds while it unpacks itself.
echo.

set "MODE="
where choice >nul 2>nul
if errorlevel 1 goto mode_fallback
choice /c 12 /n /m "Enter 1 or 2: "
if errorlevel 2 set "MODE=onefile"
if errorlevel 1 if not defined MODE set "MODE=onedir"
goto mode_done
:mode_fallback
set /p "MODE=Enter 1 or 2: "
if "%MODE%"=="2" (set "MODE=onefile") else (set "MODE=onedir")
:mode_done
echo.

if "%MODE%"=="onefile" (
    set "MODEFLAG=--onefile"
    set "OUTPUT=dist\%APPNAME%.exe"
) else (
    set "MODEFLAG=--onedir"
    set "OUTPUT=dist\%APPNAME%\%APPNAME%.exe"
)

REM ---- 4. optional icon -----------------------------------------------------
set "ICONFLAG="
if exist "icon.ico" set "ICONFLAG=--icon icon.ico"
if exist "icon.ico" echo Using icon.ico for the executable.

REM ---- 5. build -------------------------------------------------------------
echo Building. This takes one to three minutes...
echo.

%PYCMD% -m PyInstaller br_editor.py ^
    --name "%APPNAME%" ^
    %MODEFLAG% ^
    --windowed ^
    --noconfirm ^
    --clean ^
    %ICONFLAG% ^
    --collect-submodules openpyxl ^
    --exclude-module tkinter ^
    --exclude-module unittest ^
    --exclude-module pydoc ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module PIL ^
    --exclude-module PyQt5 ^
    --exclude-module PySide2 ^
    --exclude-module PySide6 ^
    --exclude-module PyQt6.QtQml ^
    --exclude-module PyQt6.QtQuick ^
    --exclude-module PyQt6.QtQuick3D ^
    --exclude-module PyQt6.QtQuickWidgets ^
    --exclude-module PyQt6.QtMultimedia ^
    --exclude-module PyQt6.QtMultimediaWidgets ^
    --exclude-module PyQt6.QtWebEngineCore ^
    --exclude-module PyQt6.QtWebEngineWidgets ^
    --exclude-module PyQt6.QtWebChannel ^
    --exclude-module PyQt6.QtWebSockets ^
    --exclude-module PyQt6.QtBluetooth ^
    --exclude-module PyQt6.QtNfc ^
    --exclude-module PyQt6.QtPositioning ^
    --exclude-module PyQt6.QtSerialPort ^
    --exclude-module PyQt6.QtSensors ^
    --exclude-module PyQt6.QtCharts ^
    --exclude-module PyQt6.QtDataVisualization ^
    --exclude-module PyQt6.QtDesigner ^
    --exclude-module PyQt6.QtHelp ^
    --exclude-module PyQt6.QtPdf ^
    --exclude-module PyQt6.QtPdfWidgets ^
    --exclude-module PyQt6.QtSpatialAudio ^
    --exclude-module PyQt6.QtTextToSpeech ^
    --exclude-module PyQt6.QtRemoteObjects ^
    --exclude-module PyQt6.Qt3DCore ^
    --exclude-module PyQt6.Qt3DRender ^
    --exclude-module PyQt6.QtTest

if errorlevel 1 goto build_failed
if not exist "%OUTPUT%" goto build_failed

echo.
echo ============================================================
echo   Build finished
echo ============================================================
echo.
echo   %OUTPUT%
echo.
if "%MODE%"=="onefile" echo   Share this single .exe - no Python needed on the target PC.
if "%MODE%"=="onedir"  echo   Share the whole dist\%APPNAME% folder - no Python needed.
echo.
echo   The "build" folder and %APPNAME%.spec are build leftovers
echo   and can be deleted.
echo.

call :ask_yes_no "Open the output folder now?"
if errorlevel 2 goto finish
if "%MODE%"=="onefile" (start "" "%CD%\dist") else (start "" "%CD%\dist\%APPNAME%")

:finish
echo.
pause
exit /b 0


REM ===========================================================================
REM  Exit paths
REM ===========================================================================
:no_python
echo [ERROR] Python 3.9 or newer was not found.
echo.
echo         Run quick_start.bat first - it can install Python for you.
echo.
pause
exit /b 1

:pip_failed
echo.
echo [ERROR] Package installation failed.
echo         Check your internet connection and try again.
echo.
pause
exit /b 1

:build_failed
echo.
echo [ERROR] The build failed. Scroll up for the PyInstaller error.
echo.
echo         Things worth trying:
echo           - delete the "build" folder and %APPNAME%.spec, then retry
echo           - make sure no antivirus is blocking PyInstaller
echo           - run:  %PYCMD% -m pip install --upgrade pyinstaller
echo.
pause
exit /b 1


REM ===========================================================================
REM  Subroutines
REM ===========================================================================
:ask_yes_no
where choice >nul 2>nul
if errorlevel 1 goto ask_fallback
choice /c YN /n /m "%~1 [Y/N] "
exit /b %errorlevel%
:ask_fallback
set "ANS="
set /p "ANS=%~1 [Y/N] "
if /i "%ANS%"=="Y" exit /b 1
if /i "%ANS%"=="YES" exit /b 1
exit /b 2

:try_py
if defined PYCMD exit /b 0
if not exist %1 exit /b 0
%1 -c "%VCHECK%" >nul 2>nul
if errorlevel 1 exit /b 0
set "PYCMD=%1"
exit /b 0

:find_python
set "PYCMD="
where py >nul 2>nul
if errorlevel 1 goto fp_path
py -3 -c "%VCHECK%" >nul 2>nul
if errorlevel 1 goto fp_path
set "PYCMD=py -3"
exit /b 0
:fp_path
for /f "delims=" %%I in ('where python 2^>nul') do call :try_py "%%I"
if defined PYCMD exit /b 0
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :try_py "%%D\python.exe"
if defined PYCMD exit /b 0
for /d %%D in ("%ProgramFiles%\Python3*") do call :try_py "%%D\python.exe"
if defined PYCMD exit /b 0
for /d %%D in ("%ProgramFiles(x86)%\Python3*") do call :try_py "%%D\python.exe"
exit /b 0
