#!/usr/bin/env python3
"""Portable source distribution. No writes outside the repository."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent

def main():
    output = ROOT / "dist" / "gpt-usage-desktop-portable.zip"
    output.parent.mkdir(exist_ok=True)
    files = [ROOT / "README.md", ROOT / "LICENSE", ROOT / "pyproject.toml"]
    for folder in ("gpt_usage", "bin", "docs", "scripts", "tests", "gnome-extension"):
        files += [path for path in (ROOT / folder).rglob("*")
                  if path.is_file() and "__pycache__" not in path.parts and "runtime" not in path.parts
                  and path.name != "gschemas.compiled"]
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, Path("gpt-usage") / path.relative_to(ROOT))
    print(output)

if __name__ == "__main__":
    main()
