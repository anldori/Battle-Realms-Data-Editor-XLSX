@echo off
REM ============================================================================
REM  Battle Realms Data Editor (XLSX) - launcher
REM
REM  Double-click this file to start the editor.
REM  You can also drag a .xlsx file onto it to open that file directly.
REM
REM  If Python is missing, this script offers to download and install it
REM  silently (per-user, no admin rights needed, PATH updated automatically).
REM ============================================================================
setlocal
cd /d "%~dp0"
title Battle Realms Data Editor

set "PYVER=3.12.10"
set "MINPY=3.9"
set "VCHECK=import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)"

REM ---- pick the right installer for this machine -----------------------------
set "PYARCH=amd64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "PYARCH=arm64"
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set "PYARCH=arm64"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "PYARCH=win32"

if /i "%PYARCH%"=="win32" (
    set "PYEXE=python-%PYVER%.exe"
) else (
    set "PYEXE=python-%PYVER%-%PYARCH%.exe"
)
set "PYURL=https://www.python.org/ftp/python/%PYVER%/%PYEXE%"
set "PYTMP=%TEMP%\%PYEXE%"

echo ============================================================
echo   Battle Realms Data Editor
echo ============================================================
echo.

REM ---- 1. locate a usable Python --------------------------------------------
call :find_python
if defined PYCMD goto have_python

echo Python %MINPY% or newer was not found on this computer.
echo.
echo This editor needs Python to run. It can be downloaded and set up
echo automatically for you:
echo.
echo    Version   : Python %PYVER%  ^(%PYARCH%^)
echo    Source    : www.python.org  ^(official^)
echo    Size      : about 26 MB
echo    Scope     : this user account only - no administrator rights needed
echo    Options   : silent install, "Add to PATH" enabled, pip included
echo.

call :ask_yes_no "Download and install Python %PYVER% now?"
if errorlevel 2 goto declined
echo.

call :install_python
if errorlevel 1 goto install_failed

call :refresh_path
call :find_python
if not defined PYCMD goto install_failed

echo.
echo Python installed successfully.
echo.

:have_python
set "PYFOUND="
for /f "delims=" %%V in ('%PYCMD% -c "import sys;print(sys.version.split()[0])" 2^>nul') do set "PYFOUND=%%V"
echo Using Python %PYFOUND%
echo.

REM ---- 2. make sure the Python packages are present --------------------------
%PYCMD% -c "import PyQt6, openpyxl" >nul 2>nul
if not errorlevel 1 goto launch

echo Installing required packages ^(first run only^)...
echo.
%PYCMD% -m pip install --upgrade pip --quiet
%PYCMD% -m pip install -r requirements.txt
if errorlevel 1 goto pip_failed
echo.

REM ---- 3. launch -------------------------------------------------------------
:launch
echo Starting Battle Realms Data Editor...
%PYCMD% br_editor.py %*
if errorlevel 1 goto app_failed
exit /b 0


REM ===========================================================================
REM  Exit paths
REM ===========================================================================
:declined
echo.
echo Installation skipped. Nothing was changed on your computer.
echo.
echo To install Python yourself later:
echo    1. Go to  https://www.python.org/downloads/
echo    2. Download Python %MINPY% or newer for Windows
echo    3. IMPORTANT: tick "Add python.exe to PATH" in the installer
echo    4. Run this file again
echo.
pause
exit /b 1

:install_failed
echo.
echo [ERROR] The Python installation did not complete.
echo.
echo Please install it manually instead:
echo    1. Go to  https://www.python.org/downloads/
echo    2. Download Python %MINPY% or newer for Windows
echo    3. IMPORTANT: tick "Add python.exe to PATH" in the installer
echo    4. Run this file again
echo.
pause
exit /b 1

:pip_failed
echo.
echo [ERROR] Could not install the required packages ^(PyQt6, openpyxl^).
echo         Check your internet connection, then run this file again.
echo.
pause
exit /b 1

:app_failed
echo.
echo [ERROR] The editor exited with an error. See the message above.
echo.
pause
exit /b 1


REM ===========================================================================
REM  Subroutines
REM ===========================================================================

REM --- Ask a yes/no question. Returns errorlevel 1 for Yes, 2 for No.
:ask_yes_no
where choice >nul 2>nul
if errorlevel 1 goto ask_fallback
choice /c YN /n /m "%~1 [Y/N] "
exit /b %errorlevel%
:ask_fallback
REM for the rare system without choice.exe
set "ANS="
set /p "ANS=%~1 [Y/N] "
if /i "%ANS%"=="Y" exit /b 1
if /i "%ANS%"=="YES" exit /b 1
exit /b 2


REM --- Test one candidate interpreter; on success store it in PYCMD.
:try_py
if defined PYCMD exit /b 0
if not exist %1 exit /b 0
%1 -c "%VCHECK%" >nul 2>nul
if errorlevel 1 exit /b 0
set "PYCMD=%1"
exit /b 0


REM --- Find a Python >= MINPY. Sets PYCMD to a quoted exe path or to "py -3".
:find_python
set "PYCMD="

REM the py launcher is the most reliable when several versions are installed
where py >nul 2>nul
if errorlevel 1 goto fp_path
py -3 -c "%VCHECK%" >nul 2>nul
if errorlevel 1 goto fp_path
set "PYCMD=py -3"
exit /b 0

REM plain "python" on PATH. The Microsoft Store stub also answers to this name
REM but cannot run code, so it fails the version check and is skipped.
:fp_path
for /f "delims=" %%I in ('where python 2^>nul') do call :try_py "%%I"
if defined PYCMD exit /b 0

REM common install locations, in case PATH has not been refreshed yet
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :try_py "%%D\python.exe"
if defined PYCMD exit /b 0
for /d %%D in ("%ProgramFiles%\Python3*") do call :try_py "%%D\python.exe"
if defined PYCMD exit /b 0
for /d %%D in ("%ProgramFiles(x86)%\Python3*") do call :try_py "%%D\python.exe"
exit /b 0


REM --- Download and silently install Python. Returns errorlevel 1 on failure.
:install_python
echo Downloading Python %PYVER% ...
echo   %PYURL%
echo.

if exist "%PYTMP%" del /f /q "%PYTMP%" >nul 2>nul

where curl >nul 2>nul
if errorlevel 1 goto dl_powershell
curl -L --fail --progress-bar -o "%PYTMP%" "%PYURL%"
goto dl_done

:dl_powershell
echo Using PowerShell to download...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri '%PYURL%' -OutFile '%PYTMP%' } catch { exit 1 }"

:dl_done
if not exist "%PYTMP%" goto dl_failed

echo.
echo Installing Python %PYVER% silently. This takes a minute, please wait...
echo ^(no setup window will appear - that is expected^)
echo.

start /wait "" "%PYTMP%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1 Include_test=0 AssociateFiles=0 Shortcuts=0
set "RC=%errorlevel%"

del /f /q "%PYTMP%" >nul 2>nul

if not "%RC%"=="0" goto setup_failed
exit /b 0

:dl_failed
echo.
echo [ERROR] Download failed - the installer file was not saved.
exit /b 1

:setup_failed
echo [ERROR] The Python installer returned error code %RC%.
exit /b 1


REM --- Re-read PATH from the registry so this window sees the new Python.
:refresh_path
set "REGPATH_U="
set "REGPATH_S="
for /f "skip=2 tokens=2,*" %%A in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "REGPATH_U=%%B"
for /f "skip=2 tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "REGPATH_S=%%B"
if defined REGPATH_S set "PATH=%REGPATH_S%"
if defined REGPATH_U set "PATH=%PATH%;%REGPATH_U%"
exit /b 0
