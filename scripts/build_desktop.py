#!/usr/bin/env python3
"""Build native GUI and console executables, optionally including verified Codex."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def target():
    family = {'Windows': 'win32', 'Darwin': 'darwin', 'Linux': 'linux'}[platform.system()]
    arch = 'arm64' if platform.machine().lower() in ('arm64', 'aarch64') else 'x64'
    return f'{family}-{arch}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-codex', action='store_true', help='Include verified runtime from build/vendor for the host OS')
    args = parser.parse_args()
    if importlib.util.find_spec('PyInstaller') is None:
        raise SystemExit('Install PyInstaller in a project-local venv first; see README.')
    vendor = ROOT / 'build' / 'vendor' / target()
    executable = 'codex.exe' if sys.platform == 'win32' else 'codex'
    if args.bundle_codex:
        manifest = json.loads((vendor / 'codex-manifest.json').read_text(encoding='utf-8'))
        if hashlib.sha256((vendor / executable).read_bytes()).hexdigest() != manifest['binary_sha256']:
            raise SystemExit('Codex binary does not match its verified manifest')
    env = os.environ.copy()
    env['PYINSTALLER_CONFIG_DIR'] = str(ROOT / 'build' / 'pyinstaller-cache')
    for name, entry, gui in [('gpt-usage', 'run.py', False), ('gpt-usage-desktop', 'desktop_entry.py', True)]:
        command = [sys.executable, '-B', '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
                   '--name', name, '--paths', str(ROOT), '--distpath', str(ROOT / 'dist' / 'desktop'),
                   '--workpath', str(ROOT / 'build' / name), '--specpath', str(ROOT / 'build')]
        if gui:
            command.append('--windowed')
        if args.bundle_codex:
            command += ['--add-binary', f'{vendor / executable}{os.pathsep}vendor']
            for item in ['CODEX-LICENSE', 'CODEX-NOTICE', 'codex-manifest.json']:
                command += ['--add-data', f'{vendor / item}{os.pathsep}vendor']
        subprocess.run([*command, str(ROOT / 'bin' / entry)], check=True, cwd=ROOT, env=env)
    print(ROOT / 'dist' / 'desktop')

if __name__ == '__main__':
    main()
