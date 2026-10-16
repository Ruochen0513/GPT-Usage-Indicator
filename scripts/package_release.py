#!/usr/bin/env python3
"""Collect end-user binaries, notices and SHA-256 checksums after a native build."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, choices=['win32-x64', 'win32-arm64', 'darwin-x64', 'darwin-arm64', 'linux-x64', 'linux-arm64'])
    args = parser.parse_args()
    target = args.target
    output = ROOT / 'dist' / 'release'
    output.mkdir(parents=True, exist_ok=True)
    if target.startswith('win32-'):
        name = f'GPT-Usage-windows-{target.split("-")[1]}.exe'
        shutil.copy2(ROOT / 'dist' / 'desktop' / 'gpt-usage-desktop.exe', output / name)
    elif target.startswith('darwin-'):
        name = f'GPT-Usage-macos-{target.split("-")[1]}.zip'
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                        str(ROOT / 'dist' / 'desktop' / 'gpt-usage-desktop.app'), str(output / name)], check=True)
    else:
        name = f'gpt-usage-{target}.shell-extension.zip'
        shutil.copy2(ROOT / 'dist' / name, output / name)
    vendor = ROOT / 'build' / 'vendor' / target
    for item in ['CODEX-LICENSE', 'CODEX-NOTICE', 'codex-manifest.json']:
        shutil.copy2(vendor / item, output / f'{target}-{item}')
    shutil.copy2(ROOT / 'LICENSE', output / 'LICENSE')
    digest = hashlib.sha256((output / name).read_bytes()).hexdigest()
    (output / f'{name}.sha256').write_text(f'{digest}  {name}\n', encoding='utf-8')
    print(output / name)

if __name__ == '__main__':
    main()
