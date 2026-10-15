"""Deterministic local JSONL protocol peer: never reads credentials or accesses network."""
import json
import sys
for line in sys.stdin:
    msg = json.loads(line)
    if "id" not in msg or msg.get("method") == "hang":
        continue
    print(json.dumps({"method": "ignored/notification", "params": {}}), flush=True)
    result = {"rateLimits": {"primary": {"usedPercent": 25, "windowDurationMins": 300}}}
    print(json.dumps({"id": msg["id"], "result": result}), flush=True)
