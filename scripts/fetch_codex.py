#!/usr/bin/env python3
"""Fetch a pinned official OpenAI native package and verify npm's SHA-512 integrity.

Only the native Codex executable and its upstream LICENSE are redistributed.
All outputs stay in build/vendor inside this checkout.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import hmac
import io
import json
from pathlib import Path
import re
import tarfile
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
VERSION = '0.163.0'
TARGETS = ('linux-x64', 'linux-arm64', 'win32-x64', 'win32-arm64', 'darwin-x64', 'darwin-arm64')


def download(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'registry.npmjs.org', 'raw.githubusercontent.com'}:
        raise ValueError('Only official package/source HTTPS downloads are allowed')
    if parsed.hostname == 'raw.githubusercontent.com' and not parsed.path.startswith('/openai/codex/rust-v'):
        raise ValueError('Unexpected upstream source path')
    request = urllib.request.Request(url, headers={'User-Agent': 'gpt-usage-release-builder'})
    with urllib.request.urlopen(request, timeout=120) as response:
        if urlsplit(response.url).hostname != parsed.hostname:
            raise ValueError('Unexpected registry redirect')
        return response.read(250 * 1024 * 1024 + 1)


def verify(data, integrity):
    if len(data) > 250 * 1024 * 1024:
        raise ValueError('Package exceeds size limit')
    if not isinstance(integrity, str) or not integrity.startswith('sha512-'):
        raise ValueError('Upstream package must provide SHA-512 integrity')
    digest = base64.b64encode(hashlib.sha512(data).digest()).decode()
    if not hmac.compare_digest(digest, integrity.removeprefix('sha512-')):
        raise ValueError('Codex package integrity mismatch')


def fetch(target, version=VERSION):
    if target not in TARGETS or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Unsupported platform or version')
    package_version = f'{version}-{target}'
    metadata = json.loads(download(f'https://registry.npmjs.org/@openai/codex/{package_version}'))
    if metadata.get('name') != '@openai/codex' or metadata.get('version') != package_version:
        raise ValueError('Unexpected upstream package identity')
    dist = metadata['dist']
    data = download(dist['tarball'])
    verify(data, dist['integrity'])
    executable = 'codex.exe' if target.startswith('win32-') else 'codex'
    output = ROOT / 'build' / 'vendor' / target
    output.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        members = [member for member in archive.getmembers() if member.isfile() and
                   (member.name.endswith('/bin/' + executable) or member.name.endswith('/codex/' + executable))]
        if len(members) != 1:
            raise ValueError('Native executable is missing or ambiguous')
        licenses = [m for m in archive.getmembers() if m.isfile() and m.name in ('package/LICENSE', 'package/LICENSE.txt')]
        license_data = (archive.extractfile(licenses[0]).read() if licenses else
                        download(f'https://raw.githubusercontent.com/openai/codex/rust-v{version}/LICENSE'))
        notice = download(f'https://raw.githubusercontent.com/openai/codex/rust-v{version}/NOTICE')
        if b'Apache License' not in license_data:
            raise ValueError('Unexpected upstream license')
        binary = output / executable
        binary.write_bytes(archive.extractfile(members[0]).read())
        binary.chmod(0o755)
        (output / 'CODEX-LICENSE').write_bytes(license_data)
        (output / 'CODEX-NOTICE').write_bytes(notice)
    (output / 'codex-manifest.json').write_text(json.dumps({
        'package': metadata['name'], 'version': package_version, 'source': dist['tarball'],
        'integrity': dist['integrity'], 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest()
    }, indent=2) + '\n', encoding='utf-8')
    print(output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=TARGETS, required=True)
    parser.add_argument('--version', default=VERSION)
    args = parser.parse_args()
    fetch(args.target, args.version)

if __name__ == '__main__':
    main()
