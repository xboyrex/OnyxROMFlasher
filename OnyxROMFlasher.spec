# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller production spec for Onyx ROM Flasher.

Expected layout:
    index.html
    main.py
    launcher.py
    bin/
        adb.exe
        fastboot.exe
        payload-dumper-go.exe

The bundled Android tools are placed under the application's _internal/bin
directory in the onedir build. main.py resolves them relative to the app root.
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPEC).resolve().parent

datas = [
    (str(ROOT / "index.html"), "."),
    (str(ROOT / "bin"), "bin"),
]

# pywebview can use platform-specific backend modules. Collecting its
# submodules avoids an incomplete GUI bundle when the environment changes.
hiddenimports = collect_submodules("webview")


a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="OnyxROMFlasher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

# onedir is intentional for V1:
# - Android tools remain separate and replaceable.
# - Web assets are easy to inspect.
# - Startup/debugging is simpler than a one-file self-extracting bundle.
