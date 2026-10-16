"""Portable private storage and profile validation. Never store credentials in snapshots."""
from __future__ import annotations

import json
import os
import re
import tempfile
import sys
import time
import errno
from contextlib import contextmanager
from pathlib import Path

PROFILE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,47}$")


class OperationBusy(ValueError):
    pass


def profile_id(value: str) -> str:
    if not isinstance(value, str) or not PROFILE.fullmatch(value):
        raise ValueError("Account id must be 1–48 letters, digits, hyphens or underscores")
    return value


def default_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        if sys.platform == 'win32':
            base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library' / 'Application Support'
        else:
            base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
        return base / 'gpt-usage-indicator'
    return Path(__file__).resolve().parent.parent / ".runtime"


def read_json(path: Path, default=None):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else default
    except (OSError, ValueError):
        return default


def atomic_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Store:
    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()

    def config(self) -> dict:
        result = read_json(self.root / "accounts.json", {})
        accounts = result.get("accounts", {})
        if not isinstance(accounts, dict):
            accounts = {}
        safe = {}
        for key, value in accounts.items():
            try:
                profile_id(key)
            except ValueError:
                continue
            if isinstance(value, dict):
                safe[key] = {"label": str(value.get("label", key))[:100],
                             "expected_email": str(value.get("expected_email", ""))[:254],
                             "limit_id": str(value.get("limit_id", "codex"))[:100]}
        return {"accounts": safe}

    def add(self, account: str, label: str, expected_email: str = "", limit_id: str = "codex"):
        profile_id(account)
        config = self.config()
        if account in config["accounts"]:
            raise ValueError("Account already exists; choose another id")
        config["accounts"][account] = {"label": label[:100], "expected_email": expected_email.strip(),
                                          "limit_id": limit_id}
        atomic_json(self.root / "accounts.json", config)
        self.home(account).mkdir(parents=True, exist_ok=True, mode=0o700)

    def account(self, account: str) -> dict:
        profile_id(account)
        try:
            return self.config()["accounts"][account]
        except KeyError:
            raise ValueError("Unknown account; run account add first") from None

    def home(self, account: str) -> Path:
        return self.root / "accounts" / profile_id(account) / "codex-home"

    def state_path(self, account: str) -> Path:
        return self.root / "snapshots" / f"{profile_id(account)}.json"

    def snapshot(self, account: str) -> dict:
        data = read_json(self.state_path(account), {})
        if data.get("schema_version") != 1 or data.get("account_id") != account:
            return {}
        return data

    def authorizing(self, account: str) -> bool:
        path = self.root / 'accounts' / profile_id(account) / 'authorization.lock'
        value = read_json(path, {})
        expires = value.get('expires_at')
        now = time.time()
        if isinstance(expires, (int, float)) and not isinstance(expires, bool):
            return now < expires <= now + 600
        try:
            # An exclusive marker may still be in its short initial write.
            return 0 <= now - path.stat().st_mtime < 5
        except OSError:
            return False

    @contextmanager
    def authorization_lock(self, account: str):
        path = self.root / 'accounts' / profile_id(account) / 'authorization.lock'
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            if self.authorizing(account):
                raise ValueError('Authorization is already in progress for this account') from None
            path.unlink(missing_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'expires_at': time.time() + 420}, stream)
            yield
        finally:
            path.unlink(missing_ok=True)

    @contextmanager
    def operation_lock(self, account: str, wait=False, cancel_event=None):
        """Kernel-released lock shared by refresh/login/logout, including across clients."""
        path = self.root / 'accounts' / profile_id(account) / 'operation.lock'
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        acquired = False
        try:
            if os.fstat(fd).st_size == 0:
                os.write(fd, b'0')
            deadline = time.monotonic() + (110 if wait else 0)
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise InterruptedError('Account operation cancelled')
                try:
                    if os.name == 'nt':
                        import msvcrt
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except OSError as error:
                    if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                        raise
                    if time.monotonic() >= deadline:
                        raise OperationBusy('Another operation is using this account; retry shortly') from None
                    time.sleep(0.05)
            yield
        finally:
            if acquired:
                if os.name == 'nt':
                    import msvcrt
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
