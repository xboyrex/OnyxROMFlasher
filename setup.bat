@echo off
REM POCO F7 ROM Flasher - Setup Script
REM Run this once to prepare the environment

setlocal enabledelayedexpansion

echo.
echo ========================================
echo POCO F7 ROM Flasher - Setup
echo ========================================
echo.

REM Check Python
echo [1] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python 3.8+ not found
    echo   Install from: https://www.python.org/
    echo   Make sure "Add Python to PATH" is checked
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo   Found: %PYTHON_VERSION%
echo.

REM Create directories
echo [2] Creating directories...
if not exist "logs" (
    mkdir logs
    echo   Created: logs\
)
if not exist "tools" (
    mkdir tools
    echo   Created: tools\
)
echo.

REM Install dependencies
echo [3] Installing Python dependencies...
echo   Running: pip install -r requirements.txt
pip install -r requirements.txt
if errorlevel 1 (
    echo   WARNING: Failed to install dependencies
    echo   Try running: pip install -r requirements.txt
) else (
    echo   Dependencies installed successfully
)
echo.

REM Check bundled tools
echo [4] Checking bundled tools...
set MISSING_TOOLS=0

if exist "tools\adb.exe" (
    echo   [✓] tools\adb.exe found
) else (
    echo   [✗] tools\adb.exe MISSING
    set MISSING_TOOLS=1
)

if exist "tools\fastboot.exe" (
    echo   [✓] tools\fastboot.exe found
) else (
    echo   [✗] tools\fastboot.exe MISSING
    set MISSING_TOOLS=1
)

if exist "tools\payload-dumper-go.exe" (
    echo   [✓] tools\payload-dumper-go.exe found
) else (
    echo   [✗] tools\payload-dumper-go.exe MISSING
    set MISSING_TOOLS=1
)

echo.

if %MISSING_TOOLS% equ 1 (
    echo [!] Some tools are missing:
    echo.
    echo   1. Download Android SDK Platform Tools from:
    echo      https://developer.android.com/studio/releases/platform-tools
    echo.
    echo   2. Extract and copy:
    echo      - adb.exe → tools\adb.exe
    echo      - fastboot.exe → tools\fastboot.exe
    echo.
    echo   3. Download payload-dumper-go from:
    echo      https://github.com/ssut/payload-dumper-go/releases
    echo.
    echo   4. Copy payload-dumper-go.exe → tools\payload-dumper-go.exe
    echo.
) else (
    echo   All tools found!
)

echo [5] Verification...

REM Try to import PyQt5
python -c "import PyQt5; print('   [✓] PyQt5 imported successfully')" 2>nul
if errorlevel 1 (
    echo   [✗] PyQt5 import failed
    echo      Try: pip install PyQt5==5.15.9
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Next steps:
echo   1. Ensure all tools are in tools\ directory
echo   2. Run: run.bat
echo   3. Read README.md for usage instructions
echo.

pause
