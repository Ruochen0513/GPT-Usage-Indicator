#!/usr/bin/env python3
"""Package the independent Linux companion, never part of an EGO extension ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=['linux-x64', 'linux-arm64'], required=True)
    args = parser.parse_args()
    name = f'gpt-usage-companion-{args.target}'
    stage = ROOT / 'build' / name
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    shutil.copytree(ROOT / 'companion', stage / 'companion', ignore=shutil.ignore_patterns('install.py'))
    shutil.copy2(ROOT / 'companion' / 'install.py', stage / 'install.py')
    backend = stage / 'backend'
    shutil.copytree(ROOT / 'gpt_usage', backend / 'gpt_usage', ignore=shutil.ignore_patterns('__pycache__'))
    (backend / 'run.py').write_text('from gpt_usage.cli import main\nraise SystemExit(main())\n', encoding='utf-8')
    vendor = ROOT / 'build' / 'vendor' / args.target
    manifest = json.loads((vendor / 'codex-manifest.json').read_text())
    if hashlib.sha256((vendor / 'codex').read_bytes()).hexdigest() != manifest['binary_sha256']:
        raise SystemExit('Codex runtime checksum mismatch')
    (backend / 'vendor').mkdir()
    for filename in ('codex', 'CODEX-LICENSE', 'CODEX-NOTICE', 'codex-manifest.json'):
        shutil.copy2(vendor / filename, backend / 'vendor' / filename)
    shutil.copy2(ROOT / 'LICENSE', stage / 'LICENSE')
    (stage / 'README.txt').write_text(
        'GPT Usage companion for Linux\n\nRequires GJS and Python 3.10+, normally available on GNOME.\n'
        'Install: python3 -B install.py\nRemove: python3 -B install.py --remove\n'
        'No root, source checkout or build is needed. Install separately from the GNOME extension.\n'
        'The session D-Bus service starts on demand and exits after 60 idle seconds.\n'
        'Update while no authorization is running. Restart the desktop session after updating an active service.\n'
        'Account data: $XDG_DATA_HOME/gpt-usage-indicator (default ~/.local/share/gpt-usage-indicator).\n'
        'The existing full extension shares this data; disable it before enabling the EGO edition.\n'
        'Source and issues: https://github.com/Ruochen0513/GPT-Usage-Indicator\n'
        'This is an unofficial app. OpenAI credentials stay in private per-profile storage.\n', encoding='utf-8')
    output = ROOT / 'dist' / 'release' / f'{name}.tar.gz'
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, 'w:gz') as archive:
        archive.add(stage, arcname=name)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name(output.name + '.sha256').write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
