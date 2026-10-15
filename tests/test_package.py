from pathlib import Path
import json
import subprocess
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent.parent

class PackageTests(unittest.TestCase):
    def test_self_contained_private_package(self):
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/package_extension.py')], check=True, capture_output=True)
        with zipfile.ZipFile(ROOT / 'dist/gpt-usage@local.shell-extension.zip') as archive:
            names = archive.namelist()
            for expected in ('metadata.json', 'schemas/gschemas.compiled', 'extension.js', 'prefs.js',
                             'backend/gpt_usage/provider.py', 'backend/run.py'):
                self.assertIn(expected, names)
            self.assertFalse(any('auth.json' in name or 'runtime/' in name or '__pycache__' in name for name in names))
            self.assertEqual(json.loads(archive.read('metadata.json'))['uuid'], 'gpt-usage@local')
        subprocess.run([sys.executable, '-B', str(ROOT / 'build/gpt-usage@local/backend/run.py'), '--help'], check=True, capture_output=True)

if __name__ == '__main__':
    unittest.main()
