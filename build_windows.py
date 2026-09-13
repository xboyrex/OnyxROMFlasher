"""
ROM Flasher Onyx — Windows build helper

Builds the desktop application with PyInstaller.

Expected project layout:
    index.html
    main.py
    launcher.py
    requirements.txt
    bin/
        adb.exe
        fastboot.exe
        payload-dumper-go.exe

Usage:
    python build_windows.py

The script deliberately does not download binaries. Android platform-tools
and payload-dumper-go must be supplied by the project maintainer.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "OnyxROMFlasher.spec"
APP_NAME = "OnyxROMFlasher"


REQUIRED_FILES = [
    ROOT / "index.html",
    ROOT / "main.py",
    ROOT / "launcher.py",
]

REQUIRED_TOOLS = [
    ROOT / "bin" / "adb.exe",
    ROOT / "bin" / "fastboot.exe",
    ROOT / "bin" / "payload-dumper-go.exe",
]


def fail(message: str) -> int:
    print(f"\nERROR: {message}")
    return 1


def check_project() -> bool:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.exists()]
    if missing:
        print("Missing project files:")
        for item in missing:
            print(f"  - {item}")
        return False

    missing_tools = [
        str(p.relative_to(ROOT)) for p in REQUIRED_TOOLS if not p.exists()
    ]
    if missing_tools:
        print("Missing required bundled tools:")
        for item in missing_tools:
            print(f"  - {item}")
        print("\nCreate bin/ and add the exact required executables before building.")
        return False

    return True


def run(command: list[str]) -> int:
    print("\n>", " ".join(command))
    proc = subprocess.run(command, cwd=ROOT)
    return proc.returncode


def main() -> int:
    if sys.platform != "win32":
        print("WARNING: This helper is intended to build the Windows release.")
        print("Run it on Windows for the final .exe packaging.\n")

    if not check_project():
        return 1

    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        return fail(
            "PyInstaller is not installed. Run: "
            "python -m pip install pyinstaller"
        )

    # Remove stale build output so old files cannot accidentally be packaged.
    if BUILD.exists():
        shutil.rmtree(BUILD, ignore_errors=True)
    if DIST.exists():
        shutil.rmtree(DIST, ignore_errors=True)
    if SPEC.exists():
        SPEC.unlink()

    add_data = [
        f"{ROOT / 'index.html'};.",
        f"{ROOT / 'bin'};bin",
    ]

    command = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
    ]

    for item in add_data:
        command.extend(["--add-data", item])

    # launcher.py is the actual executable entry point.
    command.append(str(ROOT / "launcher.py"))

    code = run(command)
    if code != 0:
        return fail("PyInstaller returned a non-zero exit code.")

    exe = DIST / APP_NAME / f"{APP_NAME}.exe"

    if not exe.exists():
        return fail(f"Build finished but expected executable was not found: {exe}")

    print("\nBUILD SUCCESS")
    print(f"Output: {exe}")
    print("\nImportant:")
    print("- Keep adb.exe, fastboot.exe and payload-dumper-go.exe bundled.")
    print("- Test the generated executable on a clean Windows machine.")
    print("- Do not ship a build until the onyx device check and flash flow are tested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
