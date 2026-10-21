"""Offline stand-in for the CLI; only used by isolated D-Bus integration tests."""
import json
import os
from pathlib import Path
import signal
import sys
import time

args = sys.argv[1:]
root = Path(args[args.index('--data-dir') + 1])
root.mkdir(parents=True, exist_ok=True)
command = args[4]
account = args[6] if command == 'account' else args[args.index('--account') + 1]
if command == 'account':
    config = root / 'accounts.json'
    data = json.loads(config.read_text()) if config.exists() else {'accounts': {}}
    data['accounts'][account] = {'label': args[args.index('--label') + 1]}
    config.write_text(json.dumps(data))
elif command == 'refresh':
    state = root / 'snapshots' / (account + '.json')
    state.parent.mkdir(exist_ok=True)
    state.write_text(json.dumps({'schema_version': 1, 'account_id': account, 'status': 'ok',
        'identity': {'email': 'offline@example.invalid'},
        'test_routes': [os.environ.get('GPT_USAGE_AUTH_PROXY'), os.environ.get('GPT_USAGE_QUOTA_PROXY')]}))
elif command == 'login':
    if account == 'badurl':
        print(json.dumps({'event': 'authorization', 'url': 'https://example.invalid/steal'}), flush=True)
    else:
        print(json.dumps({'event': 'authorization', 'url': 'https://auth.openai.com/offline-test', 'code': 'TEST-ONLY'}), flush=True)
    def stop(*_):
        (root / (account + '-cancelled')).write_text('cancelled')
        sys.exit(0)
    signal.signal(signal.SIGTERM, stop)
    time.sleep(20)
