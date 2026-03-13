@echo off
setlocal enabledelayedexpansion

title pyProspector -- Build Installer

echo ================================================================
echo   pyProspector  -  Installer Builder
echo ================================================================
echo.

:: ── Configurable paths ────────────────────────────────────────────
set ISCC="C:\Users\madson.unias\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
set VENV=.venv
set PYTHON=%~dp0%VENV%\Scripts\python.exe
set PIP=%~dp0%VENV%\Scripts\pip.exe
set PYINSTALLER=%~dp0%VENV%\Scripts\pyinstaller.exe
set DIST_DIR=%~dp0dist\pyProspector

:: ── Verify prerequisites ──────────────────────────────────────────
echo Checking prerequisites...

if not exist %ISCC% (
    echo.
    echo ERROR: Inno Setup 6 compiler not found at:
    echo   %ISCC%
    echo Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
    goto :fail
)

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python not found in PATH. Install Python 3.10+ first.
    goto :fail
)

echo   [OK] Inno Setup and Python found.
echo.


:: ── STEP 1: Virtual environment ───────────────────────────────────
echo [1/6] Setting up virtual environment...

if not exist "%~dp0%VENV%\Scripts\python.exe" (
    python -m venv "%~dp0%VENV%"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        goto :fail
    )
    echo   [OK] Virtual environment created.
) else (
    echo   [OK] Virtual environment already exists.
)


:: ── STEP 2: Install build dependencies ───────────────────────────
echo.
echo [2/6] Installing dependencies (requirements + Pillow + PyInstaller)...

%PIP% install -r "%~dp0requirements.txt" Pillow pyinstaller ^
    --quiet --disable-pip-version-check

if errorlevel 1 (
    echo ERROR: pip install failed.
    goto :fail
)

:: Install Playwright browsers driver (Python side only, browsers downloaded later)
%PYTHON% -m playwright install --dry-run >nul 2>&1
echo   [OK] Dependencies installed.


:: ── STEP 3: Convert PNG icon to ICO ──────────────────────────────
echo.
echo [3/6] Generating ICO icon from PNG...

%PYTHON% "%~dp0convert_icon.py"

if errorlevel 1 (
    echo ERROR: Icon conversion failed.
    goto :fail
)


:: ── STEP 4: Build with PyInstaller ───────────────────────────────
echo.
echo [4/6] Running PyInstaller (this may take several minutes)...

%PYINSTALLER% "%~dp0pyprospector.spec" --clean --noconfirm

if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    goto :fail
)
echo   [OK] PyInstaller build complete.


:: ── STEP 5: Download Playwright Chromium browser ─────────────────
echo.
echo [5/6] Downloading Playwright Chromium browser (~300 MB, requires internet)...
echo   Browsers will be saved inside the dist folder for offline installation.

:: Store browsers next to the exe so launcher.py can find them
set PLAYWRIGHT_BROWSERS_PATH=%DIST_DIR%\playwright-browsers

%PYTHON% -m playwright install chromium

if errorlevel 1 (
    echo ERROR: Playwright browser download failed.
    echo   Check your internet connection and try again.
    goto :fail
)
echo   [OK] Chromium downloaded to: %PLAYWRIGHT_BROWSERS_PATH%


:: ── STEP 6: Compile Inno Setup installer ─────────────────────────
echo.
echo [6/6] Compiling installer with Inno Setup...

if not exist "%~dp0Output" mkdir "%~dp0Output"

%ISCC% "%~dp0installer.iss"

if errorlevel 1 (
    echo ERROR: Inno Setup compilation failed.
    goto :fail
)


:: ── Done ─────────────────────────────────────────────────────────
echo.
echo ================================================================
echo   BUILD COMPLETE
echo   Installer: %~dp0Output\pyProspector_Setup.exe
echo ================================================================
echo.
pause
exit /b 0


:fail
echo.
echo ================================================================
echo   BUILD FAILED  --  fix the error above and re-run.
echo ================================================================
echo.
pause
exit /b 1
