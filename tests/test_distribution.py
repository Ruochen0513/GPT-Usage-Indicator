import base64
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from gpt_usage.provider import codex_command
from gpt_usage.storage import default_data_dir
from test_core import ROOT, TEST_ROOT

spec = importlib.util.spec_from_file_location('fetch_codex', ROOT / 'scripts/fetch_codex.py')
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)

class DistributionTests(unittest.TestCase):
    def test_verified_download_rejects_modified_payload(self):
        data = b'official package bytes'
        integrity = 'sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode()
        fetcher.verify(data, integrity)
        with self.assertRaises(ValueError): fetcher.verify(data + b'tampered', integrity)
        with self.assertRaises(ValueError): fetcher.verify(data, 'sha1-unsupported')

    def test_download_rejects_untrusted_hosts_before_network(self):
        for url in ['http://registry.npmjs.org/x', 'https://evil.invalid/package', 'https://raw.githubusercontent.com/other/repo/main/LICENSE']:
            with self.assertRaises(ValueError): fetcher.download(url)

    def test_frozen_binary_prefers_its_bundled_runtime(self):
        temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        executable = root / 'vendor' / ('codex.exe' if __import__('os').name == 'nt' else 'codex')
        executable.parent.mkdir()
        executable.write_bytes(b'test')
        with patch('sys._MEIPASS', str(root), create=True), patch('gpt_usage.provider.shutil.which', side_effect=AssertionError('must not depend on PATH')):
            self.assertEqual(codex_command('codex'), str(executable))

    def test_frozen_windows_data_does_not_require_executable_folder_writes(self):
        temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.addCleanup(temp.cleanup)
        with patch('sys.frozen', True, create=True), patch('sys.platform', 'win32'), patch.dict('os.environ', {'LOCALAPPDATA': temp.name}):
            self.assertEqual(default_data_dir(), Path(temp.name) / 'gpt-usage-indicator')
