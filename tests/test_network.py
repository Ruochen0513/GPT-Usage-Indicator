import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from gpt_usage.network import apply_proxy, proxy_url, service_error, PROXY_KEYS
from gpt_usage.provider import account_env, AppServer
from test_core import ROOT, TEST_ROOT

class NetworkTests(unittest.TestCase):
    def test_manual_proxy_overrides_stale_environment_and_bypass(self):
        env = {'GPT_USAGE_AUTH_PROXY': 'http://127.0.0.1:7897', 'HTTPS_PROXY': 'http://old.invalid:1234', 'NO_PROXY': '*'}
        apply_proxy(env, 'auth')
        for key in PROXY_KEYS: self.assertEqual(env[key], 'http://127.0.0.1:7897')
        self.assertEqual(env['NO_PROXY'], 'localhost,127.0.0.1,::1')
        self.assertEqual(env['no_proxy'], env['NO_PROXY'])

    def test_auth_and_quota_routes_are_selected_separately(self):
        env = {'GPT_USAGE_AUTH_PROXY': 'http://127.0.0.1:7897', 'GPT_USAGE_QUOTA_PROXY': 'socks5h://127.0.0.1:7898'}
        self.assertEqual(apply_proxy(dict(env), 'auth')['HTTPS_PROXY'], 'http://127.0.0.1:7897')
        self.assertEqual(apply_proxy(dict(env), 'quota')['HTTPS_PROXY'], 'socks5h://127.0.0.1:7898')

    def test_system_direct_removes_inherited_proxy(self):
        env = dict.fromkeys(PROXY_KEYS, 'http://stale.invalid:1')
        env['GPT_USAGE_AUTH_PROXY'] = 'direct'
        apply_proxy(env, 'auth')
        self.assertFalse(any(key in env for key in PROXY_KEYS))

    def test_environment_mode_keeps_existing_values(self):
        env = {'HTTPS_PROXY': 'http://127.0.0.1:7897', 'NO_PROXY': 'company.invalid'}
        self.assertEqual(apply_proxy(dict(env)), env)

    def test_rejects_invalid_and_credentialed_proxy_urls(self):
        for value in ['file:///tmp/proxy', 'http://user:SECRET@localhost:7897', 'http://localhost:99999', 'http://localhost/path', 'http://localhost?token=SECRET', 'https://bad\\host', 'http://host\n:7897']:
            with self.assertRaises(ValueError): proxy_url(value)

    def test_known_region_error_is_specific_but_redacted(self):
        error = 'Token exchange failed: 403 Country, region, or territory not supported (request id: a4b54dbcfc1c20dd-HKG) SECRET_TOKEN'
        code, message = service_error(error)
        self.assertEqual(code, 'unsupported_region')
        self.assertIn('a4b54dbcfc1c20dd-HKG', message)
        self.assertNotIn('SECRET_TOKEN', message)
        self.assertIsNone(service_error('arbitrary SECRET_TOKEN response'))

    def test_actual_child_environment_receives_the_proxy(self):
        import json, subprocess, sys
        temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.addCleanup(temp.cleanup)
        with patch.dict(os.environ, {'GPT_USAGE_AUTH_PROXY': 'http://127.0.0.1:7897'}):
            env = account_env(Path(temp.name), 'auth')
            output = subprocess.check_output([sys.executable, '-B', '-c', 'import os,json; print(json.dumps({k:os.environ.get(k) for k in ["HTTPS_PROXY","NO_PROXY"]}))'], env=env, cwd=temp.name)
        value = json.loads(output)
        self.assertEqual(value['HTTPS_PROXY'], 'http://127.0.0.1:7897')
        self.assertIn('127.0.0.1', value['NO_PROXY'])
