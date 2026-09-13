"""
Onyx ROM Flasher — native Windows launcher.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    os.chdir(ROOT)
    try:
        from main import main as app_main
        app_main()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        # A windowed PyInstaller build has no console, so show startup errors.
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Onyx ROM Flasher — Startup Error", str(exc))
            root.destroy()
        except Exception:
            print(f"ERROR: Application failed to start: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
