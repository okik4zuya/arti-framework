@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
REM Override by setting ARTIPDF_DIR in the environment before running this script, e.g.:
REM   set ARTIPDF_DIR=D:\tools\artipdf && build_installer.bat
if not defined ARTIPDF_DIR set "ARTIPDF_DIR=C:\python_tools\artipdf"
set "PAYLOAD_BIN=%SCRIPT_DIR%payload\bin"

REM makensis's OutFile ("dist\...") and File /r ("payload\bin\...", "..\tools", etc.) in
REM arti-installer.nsi are relative to CWD at makensis invocation time - pin it to this
REM script's own directory regardless of how build_installer.bat was launched.
cd /d "%SCRIPT_DIR%"

REM ── Stage poppler/tesseract from the maintainer's local artipdf checkout ──────
REM Plain local copy, no internet download, no version pinning (per decision #4/#5
REM in the vendoring plan) - fail fast if the source isn't there rather than
REM silently producing an installer with a missing bin\ payload.

if not exist "%ARTIPDF_DIR%\poppler" (
    echo.
    echo ERROR: %ARTIPDF_DIR%\poppler not found.
    echo This build step copies poppler/tesseract from a local folder - it is not
    echo downloaded. Set ARTIPDF_DIR to a folder containing poppler\ and tesseract\
    echo subfolders with those binaries, e.g.:
    echo     set ARTIPDF_DIR=D:\tools\artipdf ^&^& build_installer.bat
    exit /b 1
)
if not exist "%ARTIPDF_DIR%\tesseract" (
    echo.
    echo ERROR: %ARTIPDF_DIR%\tesseract not found.
    echo This build step copies poppler/tesseract from a local folder - it is not
    echo downloaded. Set ARTIPDF_DIR to a folder containing poppler\ and tesseract\
    echo subfolders with those binaries, e.g.:
    echo     set ARTIPDF_DIR=D:\tools\artipdf ^&^& build_installer.bat
    exit /b 1
)

echo.
echo Staging poppler/tesseract into %PAYLOAD_BIN% ...
if not exist "%PAYLOAD_BIN%\poppler" mkdir "%PAYLOAD_BIN%\poppler"
if not exist "%PAYLOAD_BIN%\tesseract" mkdir "%PAYLOAD_BIN%\tesseract"

robocopy "%ARTIPDF_DIR%\poppler" "%PAYLOAD_BIN%\poppler" /E /NFL /NDL /NJH /NJS
if %errorlevel% geq 8 (
    echo.
    echo ERROR: robocopy failed staging poppler ^(exit code %errorlevel%^).
    exit /b 1
)

robocopy "%ARTIPDF_DIR%\tesseract" "%PAYLOAD_BIN%\tesseract" /E /NFL /NDL /NJH /NJS
if %errorlevel% geq 8 (
    echo.
    echo ERROR: robocopy failed staging tesseract ^(exit code %errorlevel%^).
    exit /b 1
)

REM ── Locate makensis ────────────────────────────────────────────────────────────
where makensis >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: makensis not found on PATH.
    echo Install NSIS from https://nsis.sourceforge.io/Download and ensure
    echo its install directory ^(containing makensis.exe^) is on PATH.
    exit /b 1
)

REM ── Read FRAMEWORK_VERSION from ..\VERSION so the installer can never drift from it ──
set "APP_VERSION="
for /f "tokens=2 delims==" %%V in ('findstr /b "FRAMEWORK_VERSION=" "%SCRIPT_DIR%..\VERSION"') do set "APP_VERSION=%%V"
if not defined APP_VERSION (
    echo.
    echo ERROR: FRAMEWORK_VERSION not found in %SCRIPT_DIR%..\VERSION
    exit /b 1
)

echo.
echo Building installer v%APP_VERSION%...
echo.

REM makensis's OutFile won't create dist\ itself - it fails with "Can't open output file"
REM if the directory doesn't exist yet.
if not exist "%SCRIPT_DIR%dist" mkdir "%SCRIPT_DIR%dist"

makensis "/DAPP_VERSION=%APP_VERSION%" "%SCRIPT_DIR%arti-installer.nsi"

echo.
echo Done. Setup exe is in %SCRIPT_DIR%dist\
pause
