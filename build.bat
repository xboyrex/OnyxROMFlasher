@echo off
REM POCO F7 ROM Flasher - Build & Package Script
REM Creates distribution package

setlocal enabledelayedexpansion

echo.
echo ========================================
echo POCO F7 ROM Flasher - Build Script
echo ========================================
echo.

REM Get version from user or use default
set VERSION=1.0.0
if not "%1"=="" set VERSION=%1

set PACKAGE_NAME=onyx-rom-flasher-v%VERSION%
set PACKAGE_DIR=build\%PACKAGE_NAME%

echo Building package: %PACKAGE_NAME%
echo.

REM Step 1: Clean previous build
echo [1] Cleaning previous build...
if exist "build" (
    rmdir /s /q build
    echo   Removed: build\
)
mkdir build
mkdir "%PACKAGE_DIR%"
echo   Created: %PACKAGE_DIR%\
echo.

REM Step 2: Copy project files
echo [2] Copying project files...

copy app.py "%PACKAGE_DIR%\" >nul
copy requirements.txt "%PACKAGE_DIR%\" >nul
copy README.md "%PACKAGE_DIR%\" >nul
copy QUICKSTART.md "%PACKAGE_DIR%\" >nul
copy LICENSE "%PACKAGE_DIR%\" >nul
copy run.bat "%PACKAGE_DIR%\" >nul
copy setup.bat "%PACKAGE_DIR%\" >nul
copy build.bat "%PACKAGE_DIR%\" >nul
copy .gitignore "%PACKAGE_DIR%\" >nul
copy DISTRIBUTION_CHECKLIST.md "%PACKAGE_DIR%\" >nul

echo   Copied: Main files
echo.

REM Step 3: Copy Python modules
echo [3] Copying Python modules...

mkdir "%PACKAGE_DIR%\core"
copy core\*.py "%PACKAGE_DIR%\core\" >nul
echo   Copied: core/

mkdir "%PACKAGE_DIR%\ui"
copy ui\*.py "%PACKAGE_DIR%\ui\" >nul
echo   Copied: ui/

echo.

REM Step 4: Create tools directory
echo [4] Setting up tools directory...
mkdir "%PACKAGE_DIR%\tools"

echo. > "%PACKAGE_DIR%\tools\README.txt"
echo TOOLS DIRECTORY>> "%PACKAGE_DIR%\tools\README.txt"
echo ================>> "%PACKAGE_DIR%\tools\README.txt"
echo.>> "%PACKAGE_DIR%\tools\README.txt"
echo Download and extract these tools here:>> "%PACKAGE_DIR%\tools\README.txt"
echo.>> "%PACKAGE_DIR%\tools\README.txt"
echo 1. adb.exe>> "%PACKAGE_DIR%\tools\README.txt"
echo    From: https://developer.android.com/studio/releases/platform-tools>> "%PACKAGE_DIR%\tools\README.txt"
echo.>> "%PACKAGE_DIR%\tools\README.txt"
echo 2. fastboot.exe>> "%PACKAGE_DIR%\tools\README.txt"
echo    From: https://developer.android.com/studio/releases/platform-tools>> "%PACKAGE_DIR%\tools\README.txt"
echo.>> "%PACKAGE_DIR%\tools\README.txt"
echo 3. payload-dumper-go.exe>> "%PACKAGE_DIR%\tools\README.txt"
echo    From: https://github.com/ssut/payload-dumper-go/releases>> "%PACKAGE_DIR%\tools\README.txt"
echo.>> "%PACKAGE_DIR%\tools\README.txt"
echo Run setup.bat after placing tools here.>> "%PACKAGE_DIR%\tools\README.txt"

echo   Created: tools\ directory with README
echo.

REM Step 5: Create logs directory
echo [5] Setting up logs directory...
mkdir "%PACKAGE_DIR%\logs"
echo. > "%PACKAGE_DIR%\logs\.gitkeep"
echo   Created: logs\ directory
echo.

REM Step 6: Verify structure
echo [6] Verifying package structure...

set ERROR_COUNT=0

if not exist "%PACKAGE_DIR%\app.py" (
    echo   ERROR: app.py missing
    set /a ERROR_COUNT+=1
)

if not exist "%PACKAGE_DIR%\core\models.py" (
    echo   ERROR: core\models.py missing
    set /a ERROR_COUNT+=1
)

if not exist "%PACKAGE_DIR%\ui\main_window.py" (
    echo   ERROR: ui\main_window.py missing
    set /a ERROR_COUNT+=1
)

if not exist "%PACKAGE_DIR%\tools" (
    echo   ERROR: tools\ directory missing
    set /a ERROR_COUNT+=1
)

if not exist "%PACKAGE_DIR%\README.md" (
    echo   ERROR: README.md missing
    set /a ERROR_COUNT+=1
)

if %ERROR_COUNT% equ 0 (
    echo   [✓] All files present
) else (
    echo   [✗] %ERROR_COUNT% files missing!
    echo   Build incomplete
    pause
    exit /b 1
)

echo.

REM Step 7: Create ZIP file
echo [7] Creating distribution ZIP...

REM Check if 7-Zip is available
7z.exe --help >nul 2>&1
if errorlevel 1 (
    echo   WARNING: 7-Zip not found
    echo   Install from: https://www.7-zip.org/
    echo   Or use: tar -a -c -f %PACKAGE_NAME%.zip %PACKAGE_NAME%
    echo.
    echo   Skipping ZIP creation
) else (
    cd build
    7z.exe a -tzip %PACKAGE_NAME%.zip %PACKAGE_NAME%
    cd ..
    
    if exist "build\%PACKAGE_NAME%.zip" (
        for /f %%A in ('dir /b "build\%PACKAGE_NAME%.zip" ^| find /v /c """"') do set SIZE=%%A
        echo   [✓] Created: build\%PACKAGE_NAME%.zip
    ) else (
        echo   [!] ZIP creation failed
    )
)

echo.

REM Step 8: Summary
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Package: %PACKAGE_NAME%
echo Location: %PACKAGE_DIR%\
echo.
echo Contents:
echo   - app.py
echo   - requirements.txt
echo   - README.md
echo   - QUICKSTART.md
echo   - setup.bat
echo   - run.bat
echo   - core\ (modules)
echo   - ui\ (GUI)
echo   - tools\ (user setup)
echo   - logs\ (auto-created)
echo.
echo Next steps:
echo   1. Review all files in: %PACKAGE_DIR%\
echo   2. Test with: %PACKAGE_DIR%\setup.bat
echo   3. Test with: %PACKAGE_DIR%\run.bat
echo   4. Create ZIP for distribution
echo.
echo For distribution:
echo   - Upload build\%PACKAGE_NAME%.zip to GitHub
echo   - Or compress %PACKAGE_DIR%\ folder
echo.

pause
