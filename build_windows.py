"""
Onyx ROM Flasher — Windows build helper.

Uses the native Tkinter GUI. The project intentionally builds onedir so the
ADB/Fastboot/payload-dumper binaries remain visible and replaceable.
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

REQUIRED_FILES = [
    ROOT / "main.py",
    ROOT / "launcher.py",
    ROOT / "requirements.txt",
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
    missing_tools = [str(p.relative_to(ROOT)) for p in REQUIRED_TOOLS if not p.exists()]
    if missing:
        print("Missing project files:")
        for x in missing:
            print(f"  - {x}")
        return False
    if missing_tools:
        print("Missing required bundled tools:")
        for x in missing_tools:
            print(f"  - {x}")
        return False
    return True


def main() -> int:
    if not check_project():
        return 1

    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        return fail("PyInstaller is not installed. Run: python -m pip install pyinstaller")

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
        "--noupx",
        str(ROOT / "launcher.py"),
    ]

    print("\n>", " ".join(command))
    code = subprocess.run(command, cwd=ROOT).returncode
    if code != 0:
        return fail("PyInstaller returned a non-zero exit code.")

    app_dir = DIST / APP_NAME
    exe = app_dir / f"{APP_NAME}.exe"
    if not exe.exists():
        return fail(f"Build finished but executable was not found: {exe}")

    # PyInstaller normally collects the MSVC runtime. Verify the two runtime
    # DLLs explicitly because missing VCRUNTIME140_1.dll produces the misleading
    # Windows error: "Failed to load Python DLL ... specified module could not be found."
    for runtime_name in ("VCRUNTIME140.dll", "VCRUNTIME140_1.dll"):
        if not (app_dir / runtime_name).exists():
            source = Path(sys.base_prefix) / runtime_name
            if source.exists():
                shutil.copy2(source, app_dir / runtime_name)
            else:
                return fail(f"Required Microsoft runtime missing: {runtime_name}")

    required = [
        app_dir / "python312.dll",
        app_dir / "VCRUNTIME140.dll",
        app_dir / "VCRUNTIME140_1.dll",
        app_dir / "bin" / "adb.exe",
        app_dir / "bin" / "fastboot.exe",
        app_dir / "bin" / "payload-dumper-go.exe",
    ]
    missing = [str(p.relative_to(app_dir)) for p in required if not p.exists()]
    if missing:
        return fail("Final bundle is missing: " + ", ".join(missing))

    if (app_dir / "_internal").exists():
        return fail("Unexpected _internal directory detected.")

    print("\nBUILD SUCCESS")
    print(f"Output: {exe}")
    print("\nNative Tkinter GUI build — no pywebview/WebView2 dependency.")
    print("Test the generated executable on a clean Windows machine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
