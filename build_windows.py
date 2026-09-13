"""
Onyx ROM Flasher — deterministic Windows build helper.
The repository uses one authoritative build path: this script.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "OnyxROMFlasher"

REQUIRED_FILES = [
    ROOT / "main.py",
    ROOT / "launcher.py",
    ROOT / "runtime_safety.py",
]

REQUIRED_TOOLS = [
    ROOT / "bin" / "adb.exe",
    ROOT / "bin" / "fastboot.exe",
    ROOT / "bin" / "payload-dumper-go.exe",
    ROOT / "bin" / "AdbWinApi.dll",
    ROOT / "bin" / "AdbWinUsbApi.dll",
]


def fail(message: str) -> int:
    print(f"\nERROR: {message}")
    return 1


def check_project() -> bool:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.exists()]
    missing_tools = [str(p.relative_to(ROOT)) for p in REQUIRED_TOOLS if not p.exists()]
    if missing or missing_tools:
        if missing:
            print("Missing project files:")
            for item in missing:
                print(f"  - {item}")
        if missing_tools:
            print("Missing bundled Windows tools:")
            for item in missing_tools:
                print(f"  - {item}")
        return False
    return True


def main() -> int:
    if not check_project():
        return 1

    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        return fail("PyInstaller is not installed.")

    if BUILD.exists():
        shutil.rmtree(BUILD, ignore_errors=True)
    if DIST.exists():
        shutil.rmtree(DIST, ignore_errors=True)

    command = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--contents-directory", ".",
        "--name", APP_NAME,
        "--add-data", f"{ROOT / 'bin'};bin",
        str(ROOT / "launcher.py"),
    ]

    print("\n>", " ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        return fail("PyInstaller returned a non-zero exit code.")

    app_dir = DIST / APP_NAME
    exe = app_dir / f"{APP_NAME}.exe"
    if not exe.exists():
        return fail(f"Executable was not created: {exe}")

    if (app_dir / "_internal").exists():
        return fail("Unexpected _internal directory detected.")

    for tool in REQUIRED_TOOLS:
        bundled = app_dir / "bin" / tool.name
        if not bundled.exists():
            return fail(f"Bundled tool missing from final output: {bundled}")

    print("\nBUILD SUCCESS")
    print(f"Output: {exe}")
    print("Portable onedir layout: EXE + bin/ at the same application root.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
