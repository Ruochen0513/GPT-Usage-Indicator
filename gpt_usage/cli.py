"""Portable CLI. All application data defaults to the checkout's .runtime directory."""
from __future__ import annotations
import argparse
import json
import signal
import subprocess
import sys
from pathlib import Path
from .provider import ProviderError, account_env, codex_command, refresh
from .storage import Store, default_data_dir


def main(argv=None):
    # GNOME sends SIGTERM on disable/account switch. Unwind AppServer's context
    # so its child is terminated too, instead of leaving an orphan process.
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    parser = argparse.ArgumentParser(description="Codex subscription quota indicator")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    parser.add_argument("--codex", default="codex", help="Codex executable (Windows: native codex.exe)")
    sub = parser.add_subparsers(dest="command", required=True)
    accounts = sub.add_parser("account").add_subparsers(dest="action", required=True)
    add = accounts.add_parser("add")
    add.add_argument("id")
    add.add_argument("--label", default="")
    add.add_argument("--email", default="", help="Expected ChatGPT email; checked on every refresh")
    add.add_argument("--limit-id", default="codex")
    accounts.add_parser("list")
    for name in ("login", "logout", "refresh", "show"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--account", required=True)
        if name == "login":
            cmd.add_argument("--device-auth", action="store_true")
            cmd.add_argument("--gui", action="store_true", help="Stream managed authorization events as JSONL")
    sub.add_parser("desktop")
    args = parser.parse_args(argv)
    store = Store(args.data_dir)
    try:
        if args.command == "account":
            if args.action == "add":
                store.add(args.id, args.label or args.id, args.email, args.limit_id)
            print(json.dumps(store.config(), indent=2, ensure_ascii=False))
        elif args.command == "login":
            if args.gui:
                from .auth import graphical_login
                def emit(event):
                    print(json.dumps(event, ensure_ascii=False), flush=True)
                try:
                    graphical_login(store, args.account, args.codex, emit, device=args.device_auth)
                except (ProviderError, ValueError, OSError) as error:
                    emit({'event': 'error', 'message': str(error) if isinstance(error, ProviderError) else 'Cannot complete login; check profile and data directory'})
                    return 1
                return 0
            store.account(args.account)
            home = store.home(args.account)
            home.mkdir(parents=True, exist_ok=True, mode=0o700)
            command = [codex_command(args.codex), "-c", 'cli_auth_credentials_store="file"', "login"]
            if args.device_auth:
                command.append("--device-auth")
            return subprocess.call(command, env=account_env(home), cwd=home)
        elif args.command == "logout":
            from .auth import logout
            logout(store, args.account, args.codex)
            print(json.dumps({'event': 'logged_out'}))
        elif args.command == "refresh":
            result = refresh(store, args.account, args.codex)
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
            return 0 if result["status"] == "ok" else 1
        elif args.command == "show":
            print(json.dumps(store.snapshot(args.account), indent=2, ensure_ascii=False))
        else:
            from .desktop import launch
            launch(store, args.codex)
        return 0
    except (ProviderError, ValueError, OSError) as error:
        # OS diagnostics may contain private paths, but never include server response bodies.
        print(f"gpt-usage: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
