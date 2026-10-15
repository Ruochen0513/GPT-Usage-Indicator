import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from gpt_usage.model import normalize_limits, snapshot_status, window_percent
from gpt_usage.provider import AppServer, ProviderError, account_env, refresh, verify_account
from gpt_usage.storage import Store, atomic_json, profile_id

ROOT = Path(__file__).resolve().parent.parent
TEST_ROOT = ROOT / ".runtime" / "tests"
TEST_ROOT.mkdir(parents=True, exist_ok=True)


def quota(used=25, minutes=300, reset=2000000000):
    return {"usedPercent": used, "windowDurationMins": minutes, "resetsAt": reset}


class LimitsTests(unittest.TestCase):
    def test_duration_mapping_and_remaining(self):
        result = normalize_limits({"rateLimits": {"primary": quota(40, 10080), "secondary": quota(25)}})
        self.assertEqual(result["windows"]["five_hour"]["remaining_percent"], 75)
        self.assertEqual(result["windows"]["seven_day"]["used_percent"], 40)

    def test_prefer_selected_bucket_never_mix(self):
        result = normalize_limits({"rateLimitsByLimitId": {"codex": {"primary": quota(80)}},
                                   "rateLimits": {"secondary": quota(10, 10080)}})
        self.assertEqual(result["windows"]["five_hour"]["used_percent"], 80)
        self.assertIsNone(result["windows"]["seven_day"])
        with self.assertRaises(ValueError):
            normalize_limits({"rateLimitsByLimitId": {"other": {"primary": quota()}}})

    def test_unknown_durations_and_invalid_numbers(self):
        for value in (None, True, "50", float("nan"), float("inf")):
            self.assertIsNone(normalize_limits({"rateLimits": {"primary": quota(value)}})["windows"]["five_hour"])
        self.assertIsNone(normalize_limits({"rateLimits": {"primary": quota(10, 60)}})["windows"]["five_hour"])
        self.assertEqual(normalize_limits({"rateLimits": {"primary": quota(130)}})["windows"]["five_hour"]["used_percent"], 100)

    def test_expired_not_assumed_reset_and_stale(self):
        window = normalize_limits({"rateLimits": {"primary": quota(reset=100)}})["windows"]["five_hour"]
        self.assertIsNone(window_percent(window, now=100))
        self.assertEqual(window_percent(window, now=99), 75)
        self.assertEqual(snapshot_status({"status": "ok", "updated_at": 1}, now=800), "stale")
        self.assertEqual(snapshot_status({"status": "ok", "updated_at": 900}, now=800), "stale")

    def test_identity(self):
        for result in ({"account": None}, {"account": {"type": "apiKey"}}):
            with self.assertRaises(ProviderError):
                verify_account(result, "")
        with self.assertRaises(ProviderError):
            verify_account({"account": {"type": "chatgpt", "email": "other@test"}}, "me@test")


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name))

    def test_profiles_private_atomic_and_isolated(self):
        self.store.add("work", "Work", "me@test")
        self.store.add("personal", "Personal")
        self.assertNotEqual(self.store.home("work"), self.store.home("personal"))
        if os.name != "nt":
            self.assertEqual((self.store.root / "accounts.json").stat().st_mode & 0o777, 0o600)
        for invalid in ("../bad", "a/b", "", "x y"):
            with self.assertRaises(ValueError):
                profile_id(invalid)
        atomic_json(self.store.state_path("work"), {"schema_version": 1, "account_id": "other"})
        self.assertEqual(self.store.snapshot("work"), {})

    def test_failure_clears_cached_identity(self):
        self.store.add("work", "Work")
        atomic_json(self.store.state_path("work"), {"schema_version": 1, "account_id": "work", "identity": {"email": "private@test"}})
        result = refresh(self.store, "work", binary="__not_a_codex_binary__")
        self.assertEqual(result["error"]["code"], "cli_missing")
        self.assertNotIn("identity", result)
        self.assertEqual(result["windows"], {"five_hour": None, "seven_day": None})

    def test_success_and_account_switch(self):
        self.store.add("work", "Work", "me@test")
        class Server:
            def __init__(self, *args): self.reads = 0
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def request(self, method, params):
                if method == "account/read":
                    self.reads += 1
                    return {"account": {"type": "chatgpt", "email": "me@test"}}
                return {"rateLimits": {"primary": quota()}}
        with patch("gpt_usage.provider.codex_command", return_value="codex"):
            result = refresh(self.store, "work", server_factory=Server)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["windows"]["five_hour"]["used_percent"], 25)

    def test_env_isolated(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret", "CODEX_HOME": "elsewhere"}):
            env = account_env(self.store.home("work"))
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertEqual(env["CODEX_HOME"], str(self.store.home("work")))

    def test_jsonl_transport_and_cleanup(self):
        script = ROOT / "tests" / "fixtures" / "app_server.py"
        with AppServer([sys.executable, "-B", str(script)], self.store.root, timeout=2) as server:
            response = server.request("account/rateLimits/read", {})
            self.assertIn("rateLimits", response)
        self.assertIsNotNone(server.process.poll())

    def test_transport_timeout(self):
        script = ROOT / "tests" / "fixtures" / "app_server.py"
        with AppServer([sys.executable, "-B", str(script)], self.store.root, timeout=0.2) as server:
            with self.assertRaises(ProviderError) as caught:
                server.request("hang", {})
            self.assertEqual(caught.exception.code, "timeout")
        self.assertIsNotNone(server.process.poll())


if __name__ == "__main__":
    unittest.main()
