"""Normalize server quotas without guessing unknown or expired allowances."""
from __future__ import annotations

import math
import time
from typing import Any


def number(value: Any) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def normalize_limits(result: dict, limit_id: str = "codex") -> dict:
    buckets = result.get("rateLimitsByLimitId")
    if isinstance(buckets, dict) and buckets:
        bucket = buckets.get(limit_id)
        if not isinstance(bucket, dict):
            raise ValueError("Requested quota bucket is unavailable")
    else:
        bucket = result.get("rateLimits")
        if not isinstance(bucket, dict) or bucket.get("limitId", "codex") != limit_id:
            raise ValueError("Requested quota bucket is unavailable")
    windows = {"five_hour": None, "seven_day": None}
    for name in ("primary", "secondary"):
        item = bucket.get(name)
        if not isinstance(item, dict):
            continue
        minutes = item.get("windowDurationMins")
        key = {300: "five_hour", 10080: "seven_day"}.get(minutes) if number(minutes) else None
        used = item.get("usedPercent")
        if key is None or not number(used):
            continue
        reset = item.get("resetsAt")
        used = min(100, max(0, used))
        windows[key] = {"used_percent": used, "remaining_percent": 100 - used,
                        "duration_minutes": minutes,
                        "resets_at": reset if number(reset) and reset > 0 else None}
    plan = bucket.get("planType")
    return {"limit_id": limit_id, "plan": plan if isinstance(plan, str) else None, "windows": windows}


def window_percent(window: dict | None, remaining: bool = True, now: float | None = None):
    if not isinstance(window, dict):
        return None
    now = time.time() if now is None else now
    reset = window.get("resets_at")
    if number(reset) and now >= reset:
        return None
    value = window.get("remaining_percent" if remaining else "used_percent")
    return min(100, max(0, value)) if number(value) else None


def snapshot_status(snapshot: dict, now: float | None = None, stale_after: int = 600) -> str:
    now = time.time() if now is None else now
    if snapshot.get("status") != "ok":
        return "error" if snapshot.get("status") == "error" else "unknown"
    updated = snapshot.get("updated_at")
    if not number(updated) or now - updated > stale_after or updated > now + 60:
        return "stale"
    return "ok"
