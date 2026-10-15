"""UI preferences and quota formatting independent of Tk/display availability."""
from __future__ import annotations
import time
from .model import number, snapshot_status, window_percent

MODES = ("text", "rings", "bars", "combined")
DEFAULTS = {"account": "", "mode": "combined", "remaining": True, "interval": 120,
            "topmost": True, "opacity": 0.98, "x": None, "y": None}


def preferences(data: dict | None) -> dict:
    data = data if isinstance(data, dict) else {}
    result = dict(DEFAULTS)
    for key, value in result.items():
        candidate = data.get(key, value)
        if key in ("remaining", "topmost"):
            result[key] = candidate if isinstance(candidate, bool) else value
        elif key == "mode":
            result[key] = candidate if candidate in MODES else value
        elif key in ("opacity", "interval"):
            if number(candidate):
                result[key] = max(0.5, min(1, candidate)) if key == "opacity" else int(max(30, min(3600, candidate)))
        elif key in ("x", "y"):
            result[key] = candidate if isinstance(candidate, int) and not isinstance(candidate, bool) else None
        elif key == "account":
            result[key] = candidate if isinstance(candidate, str) else ""
    return result


def percent(value) -> str:
    # Match JavaScript rounding for nonnegative percentages.
    return "—" if value is None else f"{int(value + 0.5)}%"


def color(value, remaining=True) -> str:
    if value is None:
        return "#8c96a6"
    available = value if remaining else 100 - value
    return "#f55c66" if available <= 10 else "#faba4a" if available <= 25 else "#59d4ad"


def reset_text(window, now=None):
    reset = window.get("resets_at") if isinstance(window, dict) else None
    if not number(reset):
        return "Reset unavailable"
    now = time.time() if now is None else now
    if reset <= now:
        return "Awaiting reset refresh"
    seconds = int(reset - now)
    days, hours = seconds // 86400, seconds // 3600 % 24
    minutes = seconds // 60 % 60
    return f"Resets in {days}d {hours}h" if days else f"Resets in {hours}h {minutes}m"


def display(snapshot: dict, account: str, remaining=True, now=None, stale_after=600):
    if snapshot.get("schema_version") != 1 or snapshot.get("account_id") != account:
        snapshot = {}
    status = snapshot_status(snapshot, now, stale_after)
    windows = snapshot.get("windows")
    windows = windows if isinstance(windows, dict) else {}
    values = [window_percent(windows.get(key), remaining, now) if status == "ok" else None
              for key in ("five_hour", "seven_day")]
    return status, values
