"""Deterministic local JSONL protocol peer: never reads credentials or accesses network."""
import json
import sys
requested, ready = False, False
for line in sys.stdin:
    msg = json.loads(line)
    method = msg.get('method')
    if method == 'initialized':
        ready = requested
        continue
    if 'id' not in msg:
        continue
    if method == 'initialize':
        requested = True
        result = {}
    elif not ready:
        print(json.dumps({'id': msg['id'], 'error': {'message': 'Not initialized'}}), flush=True)
        continue
    elif method == 'hang':
        continue
    elif method == 'raw_error':
        print(json.dumps({'id': msg['id'], 'error': {'message': 'SECRET_TOKEN_MUST_NOT_ESCAPE'}}), flush=True)
        continue
    elif method == 'early_login':
        print(json.dumps({'method': 'account/login/completed', 'params': {'loginId': 'early', 'success': True}}), flush=True)
        result = {'loginId': 'early'}
    else:
        result = {'rateLimits': {'primary': {'usedPercent': 25, 'windowDurationMins': 300}}}
    print(json.dumps({'method': 'ignored/notification', 'params': {}}), flush=True)
    print(json.dumps({'id': msg['id'], 'result': result}), flush=True)
