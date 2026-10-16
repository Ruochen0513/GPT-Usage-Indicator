"""Official managed ChatGPT authorization for both graphical clients."""
from __future__ import annotations
import time
from urllib.parse import urlsplit
from .provider import AppServer, ProviderError, codex_command, refresh, verify_account
from .storage import Store, atomic_json


def authorization_url(value):
    if not isinstance(value, str) or len(value) > 16384:
        raise ProviderError('invalid_auth_url', 'Invalid authorization URL')
    try:
        url = urlsplit(value)
        valid = (url.scheme == 'https' and url.hostname in {'auth.openai.com', 'auth0.openai.com', 'chatgpt.com'}
                 and url.port in (None, 443) and not url.username and not url.password)
    except ValueError:
        valid = False
    if not valid:
        raise ProviderError('invalid_auth_url', 'Authorization must use an official OpenAI HTTPS address')
    return value


def clear_snapshot(store, account, status='unknown', message=None):
    value = {'schema_version': 1, 'account_id': account, 'status': status,
             'updated_at': None, 'attempted_at': time.time(),
             'windows': {'five_hour': None, 'seven_day': None}}
    if message:
        value['error'] = {'code': 'authorization', 'message': message}
    atomic_json(store.state_path(account), value)


def graphical_login(store: Store, account: str, binary='codex', emit=lambda _: None,
                    cancel_event=None, device=False, server_factory=AppServer, timeout=300):
    profile = store.account(account)
    home = store.home(account)
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    clear_snapshot(store, account)
    try:
        args = [codex_command(binary), '-c', 'cli_auth_credentials_store="file"', 'app-server']
        with server_factory(args, home, 25, cancel_event=cancel_event) as server:
            started = server.request('account/login/start', {'type': 'chatgptDeviceCode' if device else 'chatgpt'})
            login_id = started.get('loginId')
            if not isinstance(login_id, str) or not login_id:
                raise ProviderError('login_protocol', 'Codex did not start a managed login')
            url = authorization_url(started.get('verificationUrl' if device else 'authUrl'))
            event = {'event': 'authorization', 'url': url}
            if device:
                code = started.get('userCode')
                if not isinstance(code, str) or not 1 <= len(code) <= 128:
                    raise ProviderError('login_protocol', 'Codex did not return a device code')
                event['code'] = code
            emit(event)
            completed = server.wait_notification('account/login/completed', lambda item: item.get('loginId') == login_id, timeout)
            if completed.get('success') is not True:
                raise ProviderError('login_failed', 'Authorization was declined or failed; try again')
            try:
                identity = verify_account(server.request('account/read', {'refreshToken': False}), profile['expected_email'])
            except ProviderError:
                # Do not retain credentials for an unexpected identity.
                server.request('account/logout', {})
                raise
        # Publish fresh quota before notifying the UI that login is complete.
        snapshot = refresh(store, account, binary, server_factory=server_factory, cancel_event=cancel_event)
        emit({'event': 'complete', 'email': identity['email'], 'quota_status': snapshot['status']})
        return identity
    except (ProviderError, OSError, ValueError):
        clear_snapshot(store, account, 'unknown')
        raise


def logout(store: Store, account: str, binary='codex', cancel_event=None, server_factory=AppServer):
    store.account(account)
    clear_snapshot(store, account)
    home = store.home(account)
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    args = [codex_command(binary), '-c', 'cli_auth_credentials_store="file"', 'app-server']
    with server_factory(args, home, 25, cancel_event=cancel_event) as server:
        server.request('account/logout', {})
