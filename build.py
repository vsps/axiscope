"""Build a standalone .exe with PyInstaller.

Usage:  python build.py
Output: dist/AxisScope.exe
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

NAME = "AxisScope"
ENTRY = str(ROOT / "axiscope" / "main.py")
ICON = None  # str(ROOT / "icon.ico")  -- add an icon file if available


def clean() -> None:
    for d in ("build", "dist"):
        p = ROOT / d
        if p.exists():
            shutil.rmtree(p)
    for spec in ROOT.glob("*.spec"):
        spec.unlink()


def build() -> None:
    clean()

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onedir",
        "--windowed",
        f"--name={NAME}",
        "--add-data",
        f"{ROOT / 'axiscope'}{';' if sys.platform == 'win32' else ':'}axiscope",
        "--clean",
        "--noconfirm",
    ]

    if ICON:
        cmd.append(f"--icon={ICON}")

    # Collect Qt plugins so OpenGL/SVG work in the bundle
    cmd += [
        "--hidden-import=PySide6.QtOpenGLWidgets",
        "--hidden-import=PySide6.QtSvg",
        "--hidden-import=PySide6.QtSvgWidgets",
        "--hidden-import=serial.tools.list_ports_windows",
        "--hidden-import=numpy",
    ]

    cmd.append(ENTRY)

    print(f"[build] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print(f"[build] Done → {ROOT / 'dist' / NAME / (NAME + '.exe')}")


if __name__ == "__main__":
    build()
