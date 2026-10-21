#!/usr/bin/env python3
"""Install/remove the separately distributed, user-local D-Bus companion. No root."""
import argparse
import os
from pathlib import Path
import shutil

NAME = 'io.github.Ruochen0513.GptUsage'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-home', type=Path, default=Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')))
    parser.add_argument('--remove', action='store_true', help='Remove companion files, preserving all account data')
    args = parser.parse_args()
    base = args.data_home.expanduser().absolute()
    destination = base / 'gpt-usage-companion'
    service = base / 'dbus-1' / 'services' / f'{NAME}.service'
    if destination.is_symlink() or service.is_symlink():
        raise SystemExit('Refusing to replace symlinked installation files')
    if args.remove:
        if service.exists():
            expected = str(destination / 'companion' / 'service.js')
            if expected not in service.read_text():
                raise SystemExit('Service file belongs to another installation')
            service.unlink()
        if destination.exists():
            shutil.rmtree(destination)
        print('Companion removed. Account data was preserved. Finish any active account operation before removing it.')
        return
    source = Path(__file__).resolve().parent
    if not (source / 'backend' / 'vendor' / 'codex').is_file():
        raise SystemExit('Use the complete companion archive, not the repository source directory')
    for name in ('gjs', 'python3'):
        if shutil.which(name) is None:
            raise SystemExit(f'Install {name} before installing the companion')
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('companion', 'backend'):
        shutil.copytree(source / name, destination / name, dirs_exist_ok=True)
    for name in ('LICENSE', 'README.txt'):
        shutil.copy2(source / name, destination / name)
    binary = destination / 'backend' / 'vendor' / 'codex'
    binary.chmod(binary.stat().st_mode | 0o100)
    service.parent.mkdir(parents=True, exist_ok=True)
    # D-Bus Exec follows desktop-entry quoting, not shell command parsing.
    path = str(destination / 'companion' / 'service.js')
    escaped = path.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
    if '\n' in escaped or '\r' in escaped:
        raise SystemExit('Installation path cannot contain line breaks')
    gjs = shutil.which('gjs')
    service.write_text(f'[D-BUS Service]\nName={NAME}\nExec={gjs} -m "{escaped}"\n', encoding='utf-8')
    print(f'Installed companion in {destination}')
    print('It starts on demand through the session bus and exits after 60 idle seconds. No autostart or root access is used.')


if __name__ == '__main__':
    main()
