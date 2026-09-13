#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="${ROOT}_backup_${STAMP}"

echo
echo "============================================================"
echo "        ONYX ROM FLASHER — PROFESSIONAL REPAIR"
echo "============================================================"
echo
echo "ROOT   : $ROOT"
echo "BACKUP : $BACKUP"
echo

# ------------------------------------------------------------
# 0. Safety backup
# ------------------------------------------------------------
echo "[1/8] Creating filesystem backup..."

mkdir -p "$BACKUP"

cp -a \
  main.py \
  launcher.py \
  build_windows.py \
  OnyxROMFlasher.spec \
  README.md \
  requirements.txt \
  .github \
  bin \
  tools \
  work \
  "$BACKUP/" 2>/dev/null || true

echo "OK: backup created"
echo

# ------------------------------------------------------------
# 1. Remove obsolete web GUI / accidental junk
# ------------------------------------------------------------
echo "[2/8] Cleaning obsolete files..."

rm -f index.html
rm -f "bin/Apply from ADB"
rm -f bin/.gitkeep

echo "OK: obsolete GUI/junk removed"
echo

# ------------------------------------------------------------
# 2. Write professional deterministic build_windows.py
# ------------------------------------------------------------
echo "[3/8] Rebuilding build_windows.py..."

cat > build_windows.py <<'PY'
"""
Onyx ROM Flasher — deterministic Windows build.

Native Tkinter GUI.
PyInstaller onedir portable build.

Expected output:

dist/
└── OnyxROMFlasher/
    ├── OnyxROMFlasher.exe
    ├── bin/
    │   ├── adb.exe
    │   ├── fastboot.exe
    │   ├── payload-dumper-go.exe
    │   ├── AdbWinApi.dll
    │   └── AdbWinUsbApi.dll
    └── ...
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "OnyxROMFlasher"
APP_DIR = DIST / APP_NAME

REQUIRED_SOURCE = [
    ROOT / "main.py",
    ROOT / "launcher.py",
]

REQUIRED_TOOLS = [
    ROOT / "bin" / "adb.exe",
    ROOT / "bin" / "fastboot.exe",
    ROOT / "bin" / "payload-dumper-go.exe",
    ROOT / "bin" / "AdbWinApi.dll",
    ROOT / "bin" / "AdbWinUsbApi.dll",
]


def fail(message: str) -> int:
    print()
    print("=" * 60)
    print("BUILD ERROR")
    print("=" * 60)
    print(message)
    print()
    return 1


def check_project() -> bool:
    missing = [
        str(path.relative_to(ROOT))
        for path in REQUIRED_SOURCE
        if not path.is_file()
    ]

    missing_tools = [
        str(path.relative_to(ROOT))
        for path in REQUIRED_TOOLS
        if not path.is_file()
    ]

    if missing:
        print("Missing source files:")
        for item in missing:
            print(f"  - {item}")
        return False

    if missing_tools:
        print("Missing bundled tools:")
        for item in missing_tools:
            print(f"  - {item}")
        return False

    return True


def clean_output() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD, ignore_errors=True)

    if DIST.exists():
        shutil.rmtree(DIST, ignore_errors=True)


def run_pyinstaller() -> int:
    pyinstaller = shutil.which("pyinstaller")

    if not pyinstaller:
        return fail(
            "PyInstaller is not installed. "
            "Install it with: python -m pip install pyinstaller"
        )

    command = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",

        # Keep bundled data at the application root instead
        # of PyInstaller's default _internal directory.
        "--contents-directory",
        ".",

        "--name",
        APP_NAME,

        # Explicitly bundle the complete tools directory.
        "--add-data",
        f"{ROOT / 'bin'};bin",

        # Explicitly collect Tkinter runtime pieces.
        "--collect-all",
        "tkinter",

        # Build from the launcher.
        str(ROOT / "launcher.py"),
    ]

    print()
    print("PyInstaller command:")
    print(" ".join(f'"{x}"' if " " in x else x for x in command))
    print()

    return subprocess.run(command, cwd=ROOT).returncode


def verify_output() -> bool:
    exe = APP_DIR / f"{APP_NAME}.exe"

    if not exe.is_file():
        print(f"Missing executable: {exe}")
        return False

    expected = [
        APP_DIR / "bin" / "adb.exe",
        APP_DIR / "bin" / "fastboot.exe",
        APP_DIR / "bin" / "payload-dumper-go.exe",
        APP_DIR / "bin" / "AdbWinApi.dll",
        APP_DIR / "bin" / "AdbWinUsbApi.dll",
    ]

    missing = [str(p) for p in expected if not p.is_file()]

    if missing:
        print("Missing files from final package:")
        for item in missing:
            print(f"  - {item}")
        return False

    print()
    print("Final package verification:")
    print(f"  EXE : {exe}")

    for item in expected:
        print(f"  OK  : {item.relative_to(APP_DIR)}")

    return True


def main() -> int:
    if not check_project():
        return fail("Project validation failed.")

    clean_output()

    code = run_pyinstaller()

    if code != 0:
        return fail(
            f"PyInstaller returned exit code {code}."
        )

    if not verify_output():
        return fail(
            "Build completed but final portable package is incomplete."
        )

    print()
    print("=" * 60)
    print("BUILD SUCCESS")
    print("=" * 60)
    print(f"Output directory: {APP_DIR}")
    print()
    print("Native Tkinter GUI")
    print("Portable onedir package")
    print("ADB/Fastboot/payload-dumper bundled")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

echo "OK: build_windows.py replaced"
echo

# ------------------------------------------------------------
# 3. Remove conflicting .spec build path
# ------------------------------------------------------------
echo "[4/8] Making build configuration deterministic..."

rm -f OnyxROMFlasher.spec

echo "OK: obsolete conflicting .spec removed"
echo

# ------------------------------------------------------------
# 4. Professional requirements file
# ------------------------------------------------------------
echo "[5/8] Updating requirements.txt..."

cat > requirements.txt <<'EOF'
# Runtime GUI:
# Tkinter/ttk is included with the official Windows Python distribution.
#
# Build dependency is installed explicitly by GitHub Actions.
EOF

echo "OK: requirements.txt cleaned"
echo

# ------------------------------------------------------------
# 5. Professional GitHub Actions workflow
# ------------------------------------------------------------
echo "[6/8] Rebuilding GitHub Actions workflow..."

mkdir -p .github/workflows

cat > .github/workflows/build-windows.yml <<'YAML'
name: Build Windows

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    name: Build Onyx ROM Flasher
    runs-on: windows-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install build tools
        shell: pwsh
        run: |
          python -m pip install --upgrade pip
          python -m pip install pyinstaller

      - name: Verify repository tools
        shell: pwsh
        run: |
          $files = @(
            "main.py",
            "launcher.py",
            "build_windows.py",
            "bin/adb.exe",
            "bin/fastboot.exe",
            "bin/payload-dumper-go.exe",
            "bin/AdbWinApi.dll",
            "bin/AdbWinUsbApi.dll"
          )

          foreach ($file in $files) {
            if (!(Test-Path $file -PathType Leaf)) {
              throw "Required repository file missing: $file"
            }
          }

      - name: Python syntax check
        shell: pwsh
        run: |
          python -m py_compile main.py launcher.py build_windows.py

      - name: Build Onyx ROM Flasher
        shell: pwsh
        run: |
          python build_windows.py

      - name: Verify final portable package
        shell: pwsh
        run: |
          $root = "dist/OnyxROMFlasher"

          $files = @(
            "$root/OnyxROMFlasher.exe",
            "$root/bin/adb.exe",
            "$root/bin/fastboot.exe",
            "$root/bin/payload-dumper-go.exe",
            "$root/bin/AdbWinApi.dll",
            "$root/bin/AdbWinUsbApi.dll"
          )

          foreach ($file in $files) {
            if (!(Test-Path $file -PathType Leaf)) {
              throw "Final package file missing: $file"
            }
          }

          Write-Host "Final package verified successfully."

      - name: Package portable ZIP
        shell: pwsh
        run: |
          Compress-Archive `
            -Path "dist/OnyxROMFlasher/*" `
            -DestinationPath "dist/OnyxROMFlasher-Windows.zip" `
            -Force

      - name: Upload Windows build
        uses: actions/upload-artifact@v4
        with:
          name: OnyxROMFlasher-Windows
          path: dist/OnyxROMFlasher-Windows.zip
          if-no-files-found: error
YAML

echo "OK: workflow rebuilt"
echo

# ------------------------------------------------------------
# 6. .gitignore
# ------------------------------------------------------------
echo "[7/8] Updating .gitignore..."

cat > .gitignore <<'EOF'
__pycache__/
*.py[cod]
build/
dist/
work/*
!work/.gitkeep
*.log
.DS_Store
Thumbs.db
EOF

echo "OK: .gitignore updated"
echo

# ------------------------------------------------------------
# 7. Final audit
# ------------------------------------------------------------
echo "[8/8] Running repository audit..."

echo
echo "===== FILE TREE ====="
find . -maxdepth 3 -type f \
  ! -path './.git/*' \
  | sort

echo
echo "===== WEB GUI CHECK ====="

if [ -e index.html ]; then
    echo "ERROR: index.html still exists"
    exit 1
else
    echo "OK: no index.html"
fi

echo
echo "===== BUNDLED TOOLS ====="

for f in \
    bin/adb.exe \
    bin/fastboot.exe \
    bin/payload-dumper-go.exe \
    bin/AdbWinApi.dll \
    bin/AdbWinUsbApi.dll
do
    if [ -f "$f" ]; then
        ls -lh "$f"
    else
        echo "ERROR: missing $f"
        exit 1
    fi
done

echo
echo "===== PYTHON GUI CHECK ====="

if grep -q 'import tkinter' main.py; then
    echo "OK: tkinter detected"
else
    echo "ERROR: tkinter import not detected"
    exit 1
fi

if grep -q 'class OnyxApp(tk.Tk)' main.py; then
    echo "OK: native Tkinter application detected"
else
    echo "ERROR: OnyxApp Tk root not detected"
    exit 1
fi

if grep -qi 'pywebview\|webview' main.py launcher.py requirements.txt; then
    echo "ERROR: WebView reference detected"
    exit 1
else
    echo "OK: no WebView dependency"
fi

echo
echo "===== BUILD CONFIG CHECK ====="

grep -n -A25 'command = \[' build_windows.py

echo
echo "===== GIT STATUS ====="

git status --short

echo
echo "===== DIFF STAT ====="

git diff --stat

echo
echo "============================================================"
echo "REPAIR COMPLETE"
echo "============================================================"
echo
echo "Backup:"
echo "  $BACKUP"
echo
echo "IMPORTANT:"
echo "  No git commit was created."
echo "  No git push was performed."
echo
echo "Review 'git diff' before committing."
echo
