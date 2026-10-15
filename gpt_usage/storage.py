"""Portable private storage and profile validation. Never store credentials in snapshots."""
from __future__ import annotations

import json
import os
import re
import tempfile
import sys
from pathlib import Path

PROFILE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,47}$")


def profile_id(value: str) -> str:
    if not isinstance(value, str) or not PROFILE.fullmatch(value):
        raise ValueError("Account id must be 1–48 letters, digits, hyphens or underscores")
    return value


def default_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        app = next((parent for parent in executable.parents if parent.suffix == ".app"), None)
        return (app.parent if app else executable.parent) / ".runtime"
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
