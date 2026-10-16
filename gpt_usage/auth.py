"""Official managed ChatGPT authorization for both graphical clients."""
from __future__ import annotations
import time
from urllib.parse import urlsplit
from .provider import AppServer, ProviderError, codex_command, refresh, verify_account
from .storage import Store, atomic_json
from .network import service_error


def authorization_url(value):
    if not isinstance(value, str) or len(value) > 16384 or any(char.isspace() or char == '\\' for char in value):
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
    try:
        args = [codex_command(binary), '-c', 'cli_auth_credentials_store="file"', 'app-server']
        with store.authorization_lock(account):
            with store.operation_lock(account, wait=True, cancel_event=cancel_event):
                clear_snapshot(store, account)
                with server_factory(args, home, 25, cancel_event=cancel_event, purpose='auth') as server:
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
                        classified = service_error(completed.get('error'))
                        if classified:
                            raise ProviderError(*classified)
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
    home = store.home(account)
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    args = [codex_command(binary), '-c', 'cli_auth_credentials_store="file"', 'app-server']
    with store.authorization_lock(account):
        with store.operation_lock(account, wait=True, cancel_event=cancel_event):
            clear_snapshot(store, account)
            with server_factory(args, home, 25, cancel_event=cancel_event, purpose='auth') as server:
                server.request('account/logout', {})

class AuthTask:
    """Cancellable UI-independent worker, with a small public event queue."""
    def __init__(self, store, account, binary='codex', action='login', device=False):
        import queue
        import threading
        self.events = queue.Queue()
        self.cancel_event = threading.Event()
        self.account = account
        def work():
            success = False
            try:
                if action == 'logout':
                    logout(store, account, binary, cancel_event=self.cancel_event)
                    self.events.put({'event': 'logged_out'})
                else:
                    graphical_login(store, account, binary, emit=self.events.put,
                                    cancel_event=self.cancel_event, device=device)
                success = True
            except ProviderError as error:
                self.events.put({'event': 'error', 'message': str(error)})
            except Exception:
                self.events.put({'event': 'error', 'message': 'Cannot complete account operation; check the runtime and private data directory'})
            finally:
                self.events.put({'event': 'finished', 'success': success})
        self.thread = threading.Thread(target=work, daemon=False)
        self.thread.start()

    def cancel(self):
        self.cancel_event.set()
