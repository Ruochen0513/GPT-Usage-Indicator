#!/usr/bin/env python3
"""Build a self-contained extension ZIP, with no account data or credentials."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent
UUID = "gpt-usage@local"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=['linux-x64', 'linux-arm64'], help='Include a verified runtime from build/vendor/TARGET')
    args = parser.parse_args()
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
    if args.target:
        vendor = ROOT / 'build' / 'vendor' / args.target
        manifest = json.loads((vendor / 'codex-manifest.json').read_text(encoding='utf-8'))
        if hashlib.sha256((vendor / 'codex').read_bytes()).hexdigest() != manifest['binary_sha256']:
            raise ValueError('Bundled runtime digest does not match its manifest')
        destination = backend / 'vendor'
        destination.mkdir()
        for name in ['codex', 'CODEX-LICENSE', 'CODEX-NOTICE', 'codex-manifest.json']:
            shutil.copy2(vendor / name, destination / name)
    subprocess.run(["glib-compile-schemas", "--strict", str(build / "schemas")], check=True)
    name = f'gpt-usage-{args.target}' if args.target else UUID
    output = ROOT / "dist" / f"{name}.shell-extension.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(build.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(build))
    print(output)

if __name__ == "__main__":
    main()
