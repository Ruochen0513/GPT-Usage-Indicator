"""Bounded JSONL app-server client; account APIs only, no inference requests."""
from __future__ import annotations

import json
import os
import platform
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .model import normalize_limits
from .storage import Store, atomic_json


class ProviderError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def codex_command(binary: str) -> str:
    resolved = shutil.which(binary)
    if not resolved:
        raise ProviderError("cli_missing", "Codex CLI not found; configure an absolute executable path")
    # npm on Windows exposes a .cmd shim. Resolve only known native package
    # layouts instead of executing shell text. Also bypass POSIX Node shims.
    path = Path(resolved).resolve()
    arch = platform.machine().lower()
    arm = arch in {"aarch64", "arm64"}
    family = "win32" if platform.system() == "Windows" else "darwin" if platform.system() == "Darwin" else "linux"
    triple = ("aarch64" if arm else "x86_64") + {"win32": "-pc-windows-msvc", "darwin": "-apple-darwin", "linux": "-unknown-linux-musl"}[family]
    package = f"codex-{family}-{'arm64' if arm else 'x64'}"
    roots = [path.parent.parent, path.parent / "node_modules" / "@openai" / "codex"]
    executable = "codex.exe" if family == "win32" else "codex"
    for root in roots:
        vendors = [root / "vendor", root / "node_modules" / "@openai" / package / "vendor",
                   root.parent / package / "vendor"]
        for vendor in vendors:
            for folder in ("bin", "codex"):
                candidate = vendor / triple / folder / executable
                if candidate.is_file():
                    return str(candidate)
    # Batch wrappers require cmd.exe parsing; avoid a shell and quote ambiguity.
    if Path(resolved).suffix.lower() in {".cmd", ".bat"}:
        raise ProviderError("cli_wrapper", "Choose codex.exe (native Codex binary), not the npm .cmd wrapper")
    return resolved


def account_env(home: Path) -> dict:
    env = os.environ.copy()
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"):
        env.pop(key, None)
    env["CODEX_HOME"] = str(home)
    return env


class AppServer:
    def __init__(self, command: list[str], home: Path, timeout: float = 25, cancel_event=None):
        self.command, self.home, self.timeout = command, home, timeout
        self.process = None
        self.messages = queue.Queue(maxsize=128)
        self.stop = threading.Event()
        self.next_id = 0
        self.cancel_event = cancel_event

    def __enter__(self):
        try:
            self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, env=account_env(self.home),
                                            cwd=self.home, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError:
            raise ProviderError("cli_start", "Unable to start Codex app-server") from None
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            self.request("initialize", {"clientInfo": {"name": "gpt_usage_indicator", "version": "0.1.0"}})
            self.send({"method": "initialized", "params": {}})
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def _read(self):
        try:
            while not self.stop.is_set():
                line = self.process.stdout.readline(1024 * 1024 + 1)
                if not line or len(line) > 1024 * 1024:
                    break
                try:
                    item = json.loads(line)
                except (ValueError, UnicodeError):
                    continue
                try:
                    self.messages.put(item, timeout=0.2)
                except queue.Full:
                    break
        finally:
            try:
                self.messages.put(None, timeout=0.2)
            except queue.Full:
                pass

    def send(self, message):
        try:
            self.process.stdin.write((json.dumps(message) + "\n").encode())
            self.process.stdin.flush()
        except (OSError, ValueError):
            raise ProviderError("disconnected", "Codex app-server disconnected") from None

    def request(self, method: str, params: dict):
        self.next_id += 1
        ident = self.next_id
        self.send({"id": ident, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            if self.cancel_event is not None and self.cancel_event.is_set():
                raise ProviderError("cancelled", "Refresh cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderError("timeout", "Codex request timed out; retry later")
            try:
                message = self.messages.get(timeout=min(remaining, 0.2))
            except queue.Empty:
                continue
            if message is None:
                raise ProviderError("disconnected", "Codex app-server closed unexpectedly")
            if not isinstance(message, dict):
                continue
            if "method" in message and "id" in message:
                self.send({"id": message["id"], "error": {"code": -32601, "message": "Unsupported client request"}})
            if message.get("id") != ident or "method" in message:
                continue
            if "error" in message:
                # Do not echo arbitrary server diagnostics: they could include credentials.
                raise ProviderError("server_error", "Codex rejected the quota request; check login or retry")
            result = message.get("result")
            if not isinstance(result, dict):
                raise ProviderError("invalid_response", "Invalid Codex response")
            return result

    def __exit__(self, *_):
        self.stop.set()
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        for stream in (self.process.stdin, self.process.stdout):
            if stream:
                stream.close()
        self.reader.join(timeout=1)


def verify_account(result: dict, expected: str) -> dict:
    account = result.get("account")
    if not isinstance(account, dict) or account.get("type") != "chatgpt":
        raise ProviderError("login_required", "ChatGPT subscription login required; run login for this profile")
    email = account.get("email")
    if not isinstance(email, str) or not email:
        raise ProviderError("identity_missing", "Codex did not return an account email")
    if expected and email.casefold() != expected.casefold():
        raise ProviderError("account_mismatch", "Logged-in account differs from the expected email")
    return {"email": email, "plan": account.get("planType")}


def refresh(store: Store, account_id: str, binary: str = "codex", timeout: float = 25,
            server_factory=AppServer, cancel_event=None) -> dict:
    profile = store.account(account_id)
    attempt = time.time()
    try:
        home = store.home(account_id)
        home.mkdir(parents=True, exist_ok=True, mode=0o700)
        server_args = ([codex_command(binary), "-c", 'cli_auth_credentials_store="file"', "app-server"], home, timeout)
        with server_factory(*server_args, **({"cancel_event": cancel_event} if cancel_event is not None else {})) as server:
            identity = verify_account(server.request("account/read", {"refreshToken": False}), profile["expected_email"])
            limits = normalize_limits(server.request("account/rateLimits/read", {}), profile["limit_id"])
            after = verify_account(server.request("account/read", {"refreshToken": False}), profile["expected_email"])
            if identity["email"].casefold() != after["email"].casefold():
                raise ProviderError("account_changed", "Account changed during refresh; retry")
        snapshot = {"schema_version": 1, "account_id": account_id, "label": profile["label"],
                    "status": "ok", "updated_at": time.time(), "attempted_at": attempt,
                    "identity": identity, **limits}
    except (ProviderError, ValueError) as error:
        if getattr(error, "code", "") == "cancelled":
            raise
        # Deliberately clear previous quotas on an error; never show another identity's data.
        snapshot = {"schema_version": 1, "account_id": account_id, "label": profile["label"],
                    "status": "error", "attempted_at": attempt, "updated_at": None,
                    "error": {"code": getattr(error, "code", "unsupported_limits"), "message": str(error)},
                    "windows": {"five_hour": None, "seven_day": None}}
    atomic_json(store.state_path(account_id), snapshot)
    return snapshot
