"""Compact Windows/macOS/Linux Tk client. Network work never runs on the UI thread."""
from __future__ import annotations
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from .model import number
from .presentation import MODES, color, display, percent, preferences, reset_text
from .provider import ProviderError, refresh
from .storage import Store, atomic_json, default_data_dir, read_json

BG, CARD, FG, MUTED = "#111722", "#1b2433", "#edf3fc", "#94a3b8"


class UsageWindow:
    def __init__(self, root: tk.Tk, store: Store, binary="codex", auto_refresh=True):
        self.root, self.store, self.binary = root, store, binary
        self.prefs = preferences(read_json(store.root / "desktop.json", {}))
        self.accounts = store.config()["accounts"]
        if self.prefs["account"] not in self.accounts:
            self.prefs["account"] = next(iter(self.accounts), "")
        self.closed = False
        self.worker = None
        self.cancel = threading.Event()
        self.results = queue.Queue()
        self.generation = 0
        self.pending = False
        self.next_refresh = 0
        self.auto_refresh = auto_refresh
        self.snapshot = {}
        self.local_error = ""
        self.drag = None
        self.settings_window = None
        root.title("GPT Usage")
        root.configure(bg=BG)
        root.geometry("420x390")
        root.minsize(380, 370)
        if self.prefs["x"] is not None and self.prefs["y"] is not None:
            x = max(0, min(root.winfo_screenwidth() - 200, self.prefs["x"]))
            y = max(0, min(root.winfo_screenheight() - 100, self.prefs["y"]))
            root.geometry(f"+{x}+{y}")
        self._attributes()
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        if "clam" in style.theme_names(): style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=CARD, background=CARD, foreground=FG)
        style.map("TCombobox", fieldbackground=[("readonly", CARD)], foreground=[("readonly", FG)])
        top = tk.Frame(root, bg=BG)
        top.pack(fill="x", padx=18, pady=(16, 8))
        title = tk.Label(top, text="GPT  /  USAGE", bg=BG, fg=FG, font=("Arial", 12, "bold"), cursor="fleur")
        title.pack(side="left")
        title.bind("<ButtonPress-1>", self._drag_start)
        title.bind("<B1-Motion>", self._drag_move)
        self.badge = tk.Label(top, text="WAITING", bg=BG, fg=MUTED, font=("Arial", 9, "bold"))
        self.badge.pack(side="right")
        selector = tk.Frame(root, bg=BG)
        selector.pack(fill="x", padx=18)
        self.account_var = tk.StringVar(value=self.prefs["account"])
        self.selector = ttk.Combobox(selector, state="readonly", textvariable=self.account_var, values=list(self.accounts))
        self.selector.pack(side="left", fill="x", expand=True)
        self.selector.bind("<<ComboboxSelected>>", self._account_changed)
        self.basis_button = self._button(selector, "Remaining", self.toggle_basis)
        self.basis_button.pack(side="right", padx=(8, 0))
        self.identity = tk.Label(root, text="", bg=BG, fg=MUTED, anchor="w", font=("Arial", 9))
        self.identity.pack(fill="x", padx=18, pady=(8, 4))
        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0, height=180)
        self.canvas.pack(fill="both", expand=True, padx=12)
        self.canvas.bind("<Configure>", lambda _: self.render())
        switcher = tk.Frame(root, bg=BG)
        switcher.pack(fill="x", padx=18, pady=(6, 8))
        self.mode_buttons = {}
        for mode in MODES:
            button = self._button(switcher, mode.title(), lambda choice=mode: self.set_mode(choice))
            button.pack(side="left", expand=True, fill="x", padx=2)
            self.mode_buttons[mode] = button
        self.detail = tk.Label(root, text="", bg=BG, fg=MUTED, anchor="w", wraplength=380, font=("Arial", 9))
        self.detail.pack(fill="x", padx=18, pady=(0, 6))
        footer = tk.Frame(root, bg=BG)
        footer.pack(fill="x", padx=18, pady=(0, 14))
        self.refresh_button = self._button(footer, "↻  Refresh", self.start_refresh)
        self.refresh_button.pack(side="left")
        self._button(footer, "Settings", self.open_settings).pack(side="right")
        self.read_snapshot()
        self.render()
        if auto_refresh: self.start_refresh()
        self.tick_id = root.after(150, self.tick)

    def _button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=CARD, fg=FG, relief="flat", borderwidth=0,
                         activebackground="#2a3a50", activeforeground=FG, padx=9, pady=5, cursor="hand2")

    def _attributes(self):
        self.root.attributes("-topmost", self.prefs["topmost"])
        try: self.root.attributes("-alpha", self.prefs["opacity"])
        except tk.TclError: pass

    def _drag_start(self, event):
        self.drag = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def _drag_move(self, event):
        if self.drag:
            x, y = event.x_root - self.drag[0], event.y_root - self.drag[1]
            self.root.geometry(f"{x:+d}{y:+d}")

    def save(self):
        self.prefs.update(x=self.root.winfo_x(), y=self.root.winfo_y())
        try: atomic_json(self.store.root / "desktop.json", self.prefs)
        except OSError as error: self.local_error = f"Cannot save settings: {error}"

    def read_snapshot(self):
        account = self.prefs["account"]
        self.snapshot = self.store.snapshot(account) if account else {}

    def _account_changed(self, *_):
        self.cancel.set()
        self.generation += 1
        self.prefs["account"] = self.account_var.get()
        self.local_error = ""
        self.save()
        self.read_snapshot()
        self.render()
        if self.worker:
            self.pending = True
        else:
            self.start_refresh()

    def set_mode(self, mode):
        self.prefs["mode"] = mode
        self.save()
        self.render()

    def toggle_basis(self):
        self.prefs["remaining"] = not self.prefs["remaining"]
        self.save()
        self.render()

    def start_refresh(self):
        if self.closed or self.worker or not self.prefs["account"]:
            return
        self.cancel = threading.Event()
        event, generation, account = self.cancel, self.generation, self.prefs["account"]
        self.local_error = ""
        self.next_refresh = time.monotonic() + self.prefs["interval"]
        def work():
            result, error = None, ""
            try:
                result = refresh(self.store, account, self.binary, cancel_event=event)
            except ProviderError as exc:
                if exc.code != "cancelled": error = str(exc)
            except (OSError, ValueError):
                error = "Refresh failed; check data directory permissions and account configuration"
            self.results.put((generation, result, error))
        self.worker = threading.Thread(target=work, daemon=False)
        self.worker.start()
        self.render()

    def tick(self):
        try:
            generation, result, error = self.results.get_nowait()
            if self.worker:
                self.worker.join(timeout=0.01)
            self.worker = None
            if generation == self.generation:
                if result is not None: self.snapshot = result
                self.local_error = error
            if self.pending and not self.closed:
                self.pending = False
                self.start_refresh()
        except queue.Empty:
            pass
        if self.closed:
            if self.worker is None:
                self.root.destroy()
                return
        else:
            if self.auto_refresh and time.monotonic() >= self.next_refresh and not self.worker:
                self.start_refresh()
            self.render()
        self.tick_id = self.root.after(150 if self.worker else 1000, self.tick)

    def render(self):
        if self.closed: return
        remaining, mode = self.prefs["remaining"], self.prefs["mode"]
        status, values = display(self.snapshot, self.prefs["account"], remaining,
                                 stale_after=max(600, self.prefs["interval"] * 2 + 120))
        if self.local_error: status, values = "error", [None, None]
        if not self.prefs["account"]: status = "setup"
        labels = {"ok": "LIVE", "stale": "STALE", "error": "OFFLINE", "unknown": "WAITING", "setup": "SETUP"}
        self.badge.configure(text="SYNCING" if self.worker else labels.get(status, "WAITING"),
                             fg="#59d4ad" if status == "ok" else "#faba4a")
        identity = self.snapshot.get("identity")
        identity = identity if isinstance(identity, dict) else {}
        label = self.accounts.get(self.prefs["account"], {}).get("label", "Add an account in Settings")
        self.identity.configure(text=f'{label}  ·  {identity.get("email", "No verified login")}')
        self.basis_button.configure(text="Remaining" if remaining else "Used")
        self.refresh_button.configure(state="disabled" if self.worker else "normal")
        for key, button in self.mode_buttons.items():
            button.configure(bg="#2d4b51" if key == mode else CARD)
        error = self.snapshot.get("error")
        error = error if isinstance(error, dict) else {}
        detail = self.local_error or error.get("message")
        if not detail:
            detail = "Create a profile, then log in using the CLI." if status == "setup" else "Data is stale · refresh to verify quota." if status == "stale" else "Codex subscription · " + ("remaining" if remaining else "used") + " allowance"
        self.detail.configure(text=str(detail))
        canvas = self.canvas
        canvas.delete("all")
        width, height = max(350, canvas.winfo_width()), max(150, canvas.winfo_height())
        gap, pad = 10, 6
        card_w = (width - 2 * pad - gap) / 2
        windows = self.snapshot.get("windows")
        windows = windows if isinstance(windows, dict) else {}
        for i, (name, key) in enumerate((("5 HOURS", "five_hour"), ("7 DAYS", "seven_day"))):
            x0, x1 = pad + i * (card_w + gap), pad + i * (card_w + gap) + card_w
            center, value = (x0 + x1) / 2, values[i]
            tint = color(value, remaining)
            canvas.create_rectangle(x0, 4, x1, height - 4, fill=CARD, outline="")
            canvas.create_text(center, 24, text=name, fill=MUTED, font=("Arial", 9, "bold"))
            if mode in ("rings", "combined"):
                radius = min(35, (height - 90) / 2)
                cy = 40 + radius
                box = (center - radius, cy - radius, center + radius, cy + radius)
                canvas.create_oval(*box, outline="#303e50", width=7)
                if value is not None and value > 0:
                    if value >= 100: canvas.create_oval(*box, outline=tint, width=7)
                    else: canvas.create_arc(*box, start=90, extent=-360 * value / 100, style="arc", outline=tint, width=7)
                canvas.create_text(center, cy, text=percent(value), fill=FG, font=("Arial", 17, "bold"))
                if mode == "combined":
                    canvas.create_text(center, cy + radius + 15, text="remaining" if remaining else "used", fill=tint, font=("Arial", 9))
            else:
                canvas.create_text(center, height / 2 - 4, text=percent(value), fill=FG, font=("Arial", 30, "bold"))
                if mode == "bars":
                    y, bar_w = height / 2 + 27, card_w - 30
                    canvas.create_rectangle(center - bar_w / 2, y, center + bar_w / 2, y + 7, fill="#303e50", outline="")
                    if value is not None:
                        canvas.create_rectangle(center - bar_w / 2, y, center - bar_w / 2 + bar_w * value / 100, y + 7, fill=tint, outline="")
            canvas.create_text(center, height - 20, text=reset_text(windows.get(key)), fill=MUTED, font=("Arial", 8))

    def open_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift(); return
        win = tk.Toplevel(self.root)
        self.settings_window = win
        win.title("GPT Usage · Settings")
        win.configure(bg=BG)
        win.resizable(False, False)
        topmost = tk.BooleanVar(value=self.prefs["topmost"])
        interval = tk.StringVar(value=str(self.prefs["interval"]))
        opacity = tk.DoubleVar(value=self.prefs["opacity"])
        frame = tk.Frame(win, bg=BG, padx=18, pady=16)
        frame.pack(fill="both", expand=True)
        def label(text):
            tk.Label(frame, text=text, bg=BG, fg=FG, anchor="w", wraplength=420, justify="left").pack(fill="x", pady=(7, 4))
        label("Window")
        tk.Checkbutton(frame, text="Always on top", variable=topmost, bg=BG, fg=FG, selectcolor=CARD,
                       activebackground=BG, activeforeground=FG).pack(anchor="w")
        label("Refresh interval (30–3600 seconds)")
        ttk.Entry(frame, textvariable=interval).pack(fill="x")
        label("Opacity")
        tk.Scale(frame, from_=0.5, to=1, resolution=0.01, orient="horizontal", variable=opacity,
                 bg=BG, fg=FG, highlightthickness=0).pack(fill="x")
        def apply():
            try:
                seconds = int(interval.get())
                if not 30 <= seconds <= 3600: raise ValueError
            except ValueError:
                messagebox.showerror("Invalid interval", "Enter a whole number from 30 to 3600.", parent=win); return
            self.prefs.update(topmost=topmost.get(), interval=seconds, opacity=opacity.get())
            self._attributes(); self.save()
            self.next_refresh = time.monotonic() + seconds
            win.destroy()
        self._button(frame, "Save window settings", apply).pack(fill="x", pady=8)
        label("Add an isolated account profile")
        entries = {}
        for key, title in (("id", "Profile id (e.g. personal)"), ("label", "Display label"), ("email", "Expected ChatGPT email (optional)")):
            label(title)
            entries[key] = tk.StringVar()
            ttk.Entry(frame, textvariable=entries[key]).pack(fill="x")
        def add():
            try:
                key = entries["id"].get().strip()
                self.store.add(key, entries["label"].get().strip() or key, entries["email"].get().strip())
                self.accounts = self.store.config()["accounts"]
                self.selector.configure(values=list(self.accounts))
                self.account_var.set(key)
                self._account_changed()
                show_login()
            except (ValueError, OSError) as exc:
                messagebox.showerror("Cannot add profile", str(exc), parent=win)
        self._button(frame, "Add profile", add).pack(fill="x", pady=8)
        def show_login():
            # Render an argv array, not a shell string with unsafe path interpolation.
            import json
            args = ["python", "-m", "gpt_usage", "--data-dir", str(self.store.root), "--codex", self.binary,
                    "login", "--account", self.prefs["account"], "--device-auth"]
            messagebox.showinfo("Account login", "From the project directory, run the login command in a terminal.\n"
                "Arguments (JSON array; quote paths for your shell):\n\n" + json.dumps(args, ensure_ascii=False)
                + "\n\nThen click Refresh. See README for copyable platform commands.", parent=win)
        self._button(frame, "How to log in to selected account", show_login).pack(fill="x", pady=4)
        label(f"Private data: {self.store.root}")

    def close(self):
        if self.closed: return
        self.save()
        self.closed = True
        self.pending = False
        self.cancel.set()
        self.root.withdraw()
        if self.settings_window and self.settings_window.winfo_exists(): self.settings_window.destroy()
        # tick waits for bounded provider cleanup before destroying Tk.


def launch(store=None, binary="codex"):
    root = tk.Tk()
    UsageWindow(root, store or Store(default_data_dir()), binary)
    root.mainloop()


def main():
    from .cli import main as cli_main
    import sys
    return cli_main([*sys.argv[1:], "desktop"])


if __name__ == "__main__":
    main()
