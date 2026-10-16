import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from gpt_usage.auth import graphical_login, logout, authorization_url
from gpt_usage.provider import AppServer, ProviderError
from gpt_usage.storage import Store
from test_core import ROOT, TEST_ROOT


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name))
        self.store.add('personal', 'Personal', 'me@example.invalid')

    def server(self, email='me@example.invalid', success=True, device=False):
        calls = []
        class Server:
            def __init__(self, *args, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def request(self, method, params):
                calls.append((method, params))
                if method == 'account/login/start':
                    return {'loginId': 'login-1', 'authUrl': 'https://auth.openai.com/authorize?state=private',
                            'verificationUrl': 'https://auth.openai.com/codex/device', 'userCode': 'TEST-1234'}
                if method == 'account/read':
                    return {'account': {'type': 'chatgpt', 'email': email}}
                return {}
            def wait_notification(self, method, predicate, timeout):
                result = {'loginId': 'login-1', 'success': success, 'error': 'SECRET_DIAGNOSTIC'}
                if not predicate(result): raise AssertionError('wrong login id')
                return result
        return Server, calls

    def test_browser_login_only_emits_public_events_and_refreshes(self):
        factory, calls = self.server()
        events = []
        with patch('gpt_usage.auth.codex_command', return_value='mock'), patch('gpt_usage.auth.refresh', return_value={'status': 'ok'}) as refreshed:
            identity = graphical_login(self.store, 'personal', emit=events.append, server_factory=factory)
        self.assertEqual(identity['email'], 'me@example.invalid')
        self.assertEqual(events[0]['event'], 'authorization')
        self.assertEqual(events[1]['event'], 'complete')
        self.assertNotIn('token', json.dumps(events))
        refreshed.assert_called_once()

    def test_device_code(self):
        factory, calls = self.server()
        events = []
        with patch('gpt_usage.auth.codex_command', return_value='mock'), patch('gpt_usage.auth.refresh', return_value={'status': 'ok'}):
            graphical_login(self.store, 'personal', emit=events.append, device=True, server_factory=factory)
        self.assertEqual(events[0]['code'], 'TEST-1234')
        self.assertEqual(calls[0][1]['type'], 'chatgptDeviceCode')

    def test_wrong_identity_is_signed_out_and_snapshot_cleared(self):
        factory, calls = self.server(email='other@example.invalid')
        with patch('gpt_usage.auth.codex_command', return_value='mock'):
            with self.assertRaises(ProviderError) as error:
                graphical_login(self.store, 'personal', server_factory=factory)
        self.assertEqual(error.exception.code, 'account_mismatch')
        self.assertIn(('account/logout', {}), calls)
        self.assertEqual(self.store.snapshot('personal')['windows']['five_hour'], None)

    def test_failure_redacts_server_error(self):
        factory, calls = self.server(success=False)
        with patch('gpt_usage.auth.codex_command', return_value='mock'):
            with self.assertRaises(ProviderError) as error:
                graphical_login(self.store, 'personal', server_factory=factory)
        self.assertNotIn('SECRET_DIAGNOSTIC', str(error.exception))

    def test_url_allowlist(self):
        for bad in ('http://auth.openai.com', 'https://evil.invalid', 'https://auth.openai.com.evil.invalid',
                    'https://evil@auth.openai.com', 'https://auth.openai.com:1234', 'file:///tmp/local'):
            with self.assertRaises(ProviderError): authorization_url(bad)

    def test_logout_clears_quota(self):
        factory, calls = self.server()
        with patch('gpt_usage.auth.codex_command', return_value='mock'):
            logout(self.store, 'personal', server_factory=factory)
        self.assertIn(('account/logout', {}), calls)
        self.assertEqual(self.store.snapshot('personal')['status'], 'unknown')

    def test_notification_before_response_is_preserved(self):
        import sys
        with AppServer([sys.executable, '-B', str(ROOT / 'tests/fixtures/app_server.py')], self.store.root) as server:
            server.request('early_login', {})
            result = server.wait_notification('account/login/completed', lambda event: event['loginId'] == 'early', timeout=1)
        self.assertTrue(result['success'])

class WorkerTests(unittest.TestCase):
    def test_worker_reports_errors_and_always_finishes(self):
        from gpt_usage.auth import AuthTask
        with patch('gpt_usage.auth.graphical_login', side_effect=RuntimeError('SECRET')):
            task = AuthTask(None, 'personal')
            task.thread.join(timeout=2)
        self.assertFalse(task.thread.is_alive())
        events = [task.events.get_nowait(), task.events.get_nowait()]
        self.assertEqual([item['event'] for item in events], ['error', 'finished'])
        self.assertNotIn('SECRET', json.dumps(events))

    def test_worker_forwards_cancellation(self):
        from gpt_usage.auth import AuthTask
        def login(*args, **kwargs):
            kwargs['cancel_event'].wait(timeout=2)
            raise ProviderError('cancelled', 'Login cancelled')
        with patch('gpt_usage.auth.graphical_login', side_effect=login):
            task = AuthTask(None, 'personal')
            task.cancel()
            task.thread.join(timeout=2)
        self.assertFalse(task.thread.is_alive())
