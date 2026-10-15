from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from gpt_usage.presentation import display, percent, preferences, reset_text
from gpt_usage.storage import Store
from test_core import TEST_ROOT

class PresentationTests(unittest.TestCase):
    def test_preferences_validate_persisted_values(self):
        prefs = preferences({"mode": "injected", "interval": -20, "opacity": 4, "remaining": "false", "x": True})
        self.assertEqual(prefs["mode"], "combined")
        self.assertEqual(prefs["interval"], 30)
        self.assertEqual(prefs["opacity"], 1)
        self.assertTrue(prefs["remaining"])
        self.assertIsNone(prefs["x"])

    def test_unknown_stale_expired_and_account_isolation(self):
        snapshot = {"schema_version": 1, "account_id": "work", "status": "ok", "updated_at": 100,
                    "windows": {"five_hour": {"used_percent": 25, "remaining_percent": 75, "resets_at": 300}}}
        self.assertEqual(display(snapshot, "work", now=200), ("ok", [75, None]))
        self.assertEqual(display(snapshot, "other", now=200), ("unknown", [None, None]))
        self.assertEqual(display(snapshot, "work", now=900), ("stale", [None, None]))
        self.assertEqual(display(snapshot, "work", now=300), ("ok", [None, None]))
        self.assertEqual(percent(12.5), "13%")
        self.assertEqual(reset_text({"resets_at": 10}, now=20), "Awaiting reset refresh")


class WindowTests(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
            self.root.withdraw()
        except Exception as exc:
            self.skipTest(f"Tk/display unavailable: {exc}")
        self.temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: self.root.destroy() if self.root.winfo_exists() else None)

    def test_views_and_settings_without_network(self):
        from gpt_usage.desktop import UsageWindow
        store = Store(Path(self.temp.name))
        store.add("work", "Work")
        window = UsageWindow(self.root, store, auto_refresh=False)
        window.snapshot = {"schema_version": 1, "account_id": "work", "status": "ok", "updated_at": time.time(),
                           "windows": {"five_hour": {"remaining_percent": 75, "used_percent": 25}}}
        for mode in ("text", "rings", "bars", "combined"):
            window.set_mode(mode)
            self.root.update_idletasks()
            self.assertGreater(len(window.canvas.find_all()), 4)
        window.toggle_basis()
        self.assertFalse(window.prefs["remaining"])
        window.open_settings()
        self.root.update_idletasks()
        self.assertTrue(window.settings_window.winfo_exists())
        window.close()
        self.assertTrue(window.closed)
        self.root.after_cancel(window.tick_id)

if __name__ == "__main__":
    unittest.main()
