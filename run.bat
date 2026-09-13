@echo off
REM POCO F7 ROM Flasher - Windows Batch Runner
REM This script sets up environment and runs the application

echo.
echo ========================================
echo POCO F7 ROM Flasher v1.0
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [✓] Python found
echo.

REM Check if requirements are installed
echo Checking dependencies...
pip list | findstr PyQt5 >nul 2>&1
if errorlevel 1 (
    echo [!] PyQt5 not found, installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo [✓] Dependencies ready
echo.

REM Verify bundled tools
echo Verifying bundled tools...
if not exist "tools\adb.exe" (
    echo WARNING: tools\adb.exe not found
)
if not exist "tools\fastboot.exe" (
    echo WARNING: tools\fastboot.exe not found
)
if not exist "tools\payload-dumper-go.exe" (
    echo WARNING: tools\payload-dumper-go.exe not found
)

REM Create logs directory
if not exist "logs" mkdir logs

echo.
echo Starting application...
echo.

REM Run the application
python app.py

REM Show error if app failed
if errorlevel 1 (
    echo.
    echo ERROR: Application failed to start
    echo Check logs/ folder for details
    pause
)

pause
