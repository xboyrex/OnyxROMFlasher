"""
ROM Flasher Onyx — launcher

Starts the desktop application from the project root.
The actual flashing/API logic lives in main.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> int:
    # Keep relative paths predictable when launching from a shortcut,
    # PowerShell, CMD, or the generated Windows executable.
    os.chdir(ROOT)

    try:
        from main import main as app_main
    except ImportError as exc:
        print("ERROR: Could not import main.py.")
        print(f"Details: {exc}")
        print()
        print("Install dependencies with:")
        print("  python -m pip install -r requirements.txt")
        return 1

    try:
        app_main()
        return 0
    except KeyboardInterrupt:
        print("\nApplication stopped.")
        return 130
    except Exception as exc:
        print(f"ERROR: Application failed to start: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
