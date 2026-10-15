#!/usr/bin/env python3
"""Optional native standalone executables. Run on each target OS with PyInstaller installed."""
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

def main():
    if importlib.util.find_spec("PyInstaller") is None:
        raise SystemExit("Install PyInstaller in a project-local venv first; see README.")
    for name, entry, gui in (("gpt-usage", "run.py", False), ("gpt-usage-desktop", "desktop_entry.py", True)):
        args = [sys.executable, "-B", "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
                "--name", name, "--paths", str(ROOT), "--distpath", str(ROOT / "dist" / "desktop"),
                "--workpath", str(ROOT / "build" / name), "--specpath", str(ROOT / "build")]
        if gui:
            args.append("--windowed")
        subprocess.run([*args, str(ROOT / "bin" / entry)], check=True, cwd=ROOT)
    print(ROOT / "dist" / "desktop")

if __name__ == "__main__":
    main()
