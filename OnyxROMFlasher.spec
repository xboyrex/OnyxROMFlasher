# -*- mode: python ; coding: utf-8 -*-
"""
Onyx ROM Flasher native GUI PyInstaller spec.
This file is authoritative for local/manual builds.
"""

from pathlib import Path

ROOT = Path(SPEC).resolve().parent

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / "bin"), "bin")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["webview", "PySide6", "PyQt5"],
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
