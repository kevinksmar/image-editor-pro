#!/usr/bin/env python3
"""Build Image Editor Pro into a single executable using PyInstaller.

Usage:
    pip install pyinstaller
    python build_exe.py

Output: dist/Image Editor Pro/Image Editor Pro.exe (or dist/Image Editor Pro.exe for one-file)
"""

import os
import subprocess
import sys


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    # Entry script
    main_script = os.path.join(root, "main.py")
    if not os.path.isfile(main_script):
        print("Error: main.py not found")
        sys.exit(1)

    # Icon (optional): assets/icon.ico or assets/icon.png
    icon_path = None
    for name in ("icon.ico", "icon.png"):
        p = os.path.join(root, "assets", name)
        if os.path.isfile(p):
            icon_path = p
            break

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Image Editor Pro",
        "--windowed",  # No console window
        "--clean",
        # Bundle src as module (main.py does sys.path to src)
        "--add-data", f"src{os.pathsep}src",
        main_script,
    ]
    if icon_path:
        cmd.extend(["--icon", icon_path])
    # Include assets folder if present
    assets = os.path.join(root, "assets")
    if os.path.isdir(assets):
        cmd.extend(["--add-data", f"assets{os.pathsep}assets"])

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
