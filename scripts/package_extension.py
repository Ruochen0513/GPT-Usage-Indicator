#!/usr/bin/env python3
"""Build a self-contained extension ZIP, with no account data or credentials."""
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent
UUID = "gpt-usage@local"

def main():
    source = ROOT / "gnome-extension" / UUID
    build = ROOT / "build" / UUID
    if build.exists():
        shutil.rmtree(build)
    shutil.copytree(source, build, ignore=shutil.ignore_patterns("runtime", "gschemas.compiled", "__pycache__"))
    backend = build / "backend"
    backend.mkdir()
    shutil.copytree(ROOT / "gpt_usage", backend / "gpt_usage", ignore=shutil.ignore_patterns("__pycache__"))
    (backend / "run.py").write_text("from gpt_usage.cli import main\nraise SystemExit(main())\n", encoding="utf-8")
    shutil.copy2(ROOT / "LICENSE", build / "LICENSE")
    subprocess.run(["glib-compile-schemas", "--strict", str(build / "schemas")], check=True)
    output = ROOT / "dist" / f"{UUID}.shell-extension.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(build.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(build))
    print(output)

if __name__ == "__main__":
    main()
