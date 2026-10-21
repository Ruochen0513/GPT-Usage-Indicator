"""Validate the actual source-only upload archive, including its import closure."""
from pathlib import Path, PurePosixPath
import json
import re
import shutil
import subprocess
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent.parent


class EgoPackageTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node') and shutil.which('glib-compile-schemas'), 'Node and GLib schema compiler required')
    def test_submission_contains_only_reviewable_sources(self):
        subprocess.run(['python3', '-B', 'scripts/package_ego.py'], cwd=ROOT, capture_output=True, check=True)
        path = ROOT / 'dist' / 'ego' / 'gpt-usage@ruochen0513.github.io.shell-extension.zip'
        self.assertLess(path.stat().st_size, 200_000)
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            metadata = json.loads(archive.read('metadata.json'))
            self.assertEqual(metadata['uuid'], 'gpt-usage@ruochen0513.github.io')
            self.assertEqual(metadata['shell-version'], ['46'])
            self.assertEqual(metadata['url'], 'https://github.com/Ruochen0513/GPT-Usage-Indicator')
            self.assertNotIn('version', metadata)
            self.assertIn('LICENSE', names)
            self.assertIn('prefs.js', names)
            for name in names:
                self.assertNotIn('..', PurePosixPath(name).parts)
                self.assertNotIn('backend', PurePosixPath(name).parts)
                self.assertNotIn('runtime', PurePosixPath(name).parts)
                source = archive.read(name).decode('utf-8')
                self.assertFalse(name.endswith(('.py', '.so', '.exe', '.compiled')))
                if name.endswith('.js'):
                    self.assertNotIn('Gio.Subprocess', source)
                    self.assertNotIn('load_contents(', source)
                    for target in re.findall(r"from ['\"](\./[^'\"]+)['\"]", source):
                        self.assertIn(str(PurePosixPath(name).parent / target), names)
