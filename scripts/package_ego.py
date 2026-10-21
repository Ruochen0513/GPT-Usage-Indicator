#!/usr/bin/env python3
"""Build the source-only EGO submission candidate; never bundle the companion."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent
UUID = 'gpt-usage@ruochen0513.github.io'


def main():
    source = ROOT / 'gnome-extension' / UUID
    metadata = json.loads((source / 'metadata.json').read_text())
    if metadata['uuid'] != UUID or not metadata.get('url'):
        raise SystemExit('Invalid publication metadata')
    subprocess.run(['glib-compile-schemas', '--strict', '--dry-run', str(source / 'schemas')], check=True)
    files = sorted(path for path in source.rglob('*') if path.is_file())
    for path in files:
        if path.suffix not in {'.js', '.json', '.xml', '.css'}:
            raise SystemExit(f'Unexpected submission file: {path.name}')
        if path.suffix == '.js':
            subprocess.run(['node', '--input-type=module', '--check'], input=path.read_bytes(), check=True)
    output = ROOT / 'dist' / 'ego' / f'{UUID}.shell-extension.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(source))
        archive.write(ROOT / 'LICENSE', 'LICENSE')
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name(output.name + '.sha256').write_text(f'{digest}  {output.name}\n')
    print(output)


if __name__ == '__main__':
    main()
