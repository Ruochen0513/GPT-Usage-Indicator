"""Real private-session-bus tests; no system settings, credentials or network."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parent.parent


class CompanionIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('gjs') and shutil.which('dbus-run-session'), 'GJS and private D-Bus runner required')
    def test_installer_activation_and_removal(self):
        base = ROOT / '.runtime' / 'tests'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='activation-', dir=base) as temporary:
            stage = Path(temporary)
            bundle = stage / 'bundle'
            shutil.copytree(ROOT / 'companion', bundle / 'companion')
            shutil.copy2(ROOT / 'companion' / 'install.py', bundle / 'install.py')
            (bundle / 'backend' / 'vendor').mkdir(parents=True)
            (bundle / 'backend' / 'vendor' / 'codex').touch()
            shutil.copy2(ROOT / 'tests' / 'fixtures' / 'companion_helper.py', bundle / 'backend' / 'run.py')
            for name in ('LICENSE', 'README.txt'):
                (bundle / name).write_text('Offline test fixture')
            data_home = stage / 'installed files'
            installer = ['python3', '-B', str(bundle / 'install.py'), '--data-home', str(data_home)]
            subprocess.run(installer, capture_output=True, text=True, check=True)
            service_dir = data_home / 'dbus-1' / 'services'
            config = stage / 'bus.conf'
            config.write_text(f'<busconfig><type>session</type><listen>unix:abstract=gpt-usage-test-{uuid.uuid4().hex}</listen>'
                              f'<servicedir>{service_dir}</servicedir><auth>EXTERNAL</auth><policy context="default">'
                              '<allow send_destination="*"/><allow receive_sender="*"/><allow own="*"/></policy></busconfig>')
            env = os.environ.copy()
            env.update(XDG_DATA_HOME=str(data_home), XDG_CACHE_HOME=str(stage / 'cache'), TMPDIR=str(stage))
            result = subprocess.run(['dbus-run-session', '--config-file', str(config), '--', 'gjs', '-m',
                                     str(ROOT / 'tests' / 'test_companion_gjs.mjs'), str(ROOT)],
                                    env=env, capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((data_home / 'gpt-usage-indicator' / 'accounts.json').exists())
            subprocess.run([*installer, '--remove'], capture_output=True, text=True, check=True)
            self.assertFalse((data_home / 'gpt-usage-companion').exists())
            self.assertFalse(any(service_dir.glob('*.service')))
            self.assertTrue((data_home / 'gpt-usage-indicator' / 'accounts.json').exists())

    @unittest.skipUnless(shutil.which('gjs') and shutil.which('dbus-run-session'), 'GJS and private D-Bus runner required')
    def test_private_bus(self):
        base = ROOT / '.runtime' / 'tests'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='bus-', dir=base) as temporary:
            stage = Path(temporary)
            shutil.copytree(ROOT / 'companion', stage / 'companion')
            (stage / 'backend').mkdir()
            shutil.copy2(ROOT / 'tests' / 'fixtures' / 'companion_helper.py', stage / 'backend' / 'run.py')
            config = stage / 'bus.conf'
            config.write_text(f'<busconfig><type>session</type><listen>unix:abstract=gpt-usage-test-{uuid.uuid4().hex}</listen>'
                              '<auth>EXTERNAL</auth><policy context="default"><allow send_destination="*"/>'
                              '<allow receive_sender="*"/><allow own="*"/></policy></busconfig>')
            env = os.environ.copy()
            env.update(XDG_DATA_HOME=str(stage / 'data'), XDG_CACHE_HOME=str(stage / 'cache'), TMPDIR=str(stage))
            # Start the actual companion and test client on one isolated bus.
            runner = stage / 'runner.py'
            runner.write_text('import subprocess, sys\n'
                              'service = subprocess.Popen(["gjs", "-m", sys.argv[1]])\n'
                              'try:\n'
                              ' result = subprocess.run(["gjs", "-m", sys.argv[2], sys.argv[3]], timeout=30)\n'
                              'finally:\n'
                              ' service.terminate()\n'
                              ' service.wait(timeout=10)\n'
                              'raise SystemExit(result.returncode)\n')
            result = subprocess.run(['dbus-run-session', '--config-file', str(config), '--',
                                     'python3', '-B', str(runner), str(stage / 'companion' / 'service.js'),
                                     str(ROOT / 'tests' / 'test_companion_gjs.mjs'), str(ROOT)],
                                    env=env, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('D-Bus integration:', result.stdout)
