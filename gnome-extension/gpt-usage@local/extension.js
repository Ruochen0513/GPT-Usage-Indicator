import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {view, color, percentText, resetText, validAccount} from './ui.mjs';

export default class GPTUsageExtension extends Extension {
    enable() {
        this._enabled = true;
        this._generation = 0;
        this._process = null;
        this._timer = 0;
        this._watchdog = 0;
        this._settings = this.getSettings();
        this._button = new PanelMenu.Button(0, 'GPT Usage', false);
        this._box = new St.BoxLayout({style_class: 'gpt-usage-box', y_align: Clutter.ActorAlign.CENTER});
        this._drawing = new St.DrawingArea({style_class: 'gpt-usage-graph', y_align: Clutter.ActorAlign.CENTER});
        this._drawing.connect('repaint', area => this._paint(area));
        this._label = new St.Label({y_align: Clutter.ActorAlign.CENTER});
        this._box.add_child(this._drawing);
        this._box.add_child(this._label);
        this._button.add_child(this._box);
        Main.panel.addToStatusArea(this.uuid, this._button, 0, 'left');
        this._menuSignal = this._button.menu.connect('open-state-changed', (_menu, open) => {
            if (open) this._render();
        });
        this._settingsSignal = this._settings.connect('changed', () => this._configure());
        this._configure();
    }

    _dataDir() {
        return this._settings.get_string('data-directory') || GLib.build_filenamev([GLib.get_user_data_dir(), 'gpt-usage-indicator']);
    }

    _read(path) {
        try {
            const file = Gio.File.new_for_path(path);
            if (file.query_info('standard::size', Gio.FileQueryInfoFlags.NONE, null).get_size() > 65536)
                return {};
            const [ok, bytes] = file.load_contents(null);
            const value = ok ? JSON.parse(new TextDecoder().decode(bytes)) : {};
            return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
        } catch (_) {
            return {};
        }
    }

    _cancelRefresh() {
        if (this._watchdog) GLib.source_remove(this._watchdog);
        this._watchdog = 0;
        if (this._process) {
            try { this._process.send_signal(15); } catch (_) { /* Already finished. */ }
        }
        this._process = null;
    }

    _configure() {
        this._generation++;
        this._cancelRefresh();
        if (this._timer) GLib.source_remove(this._timer);
        this._timer = 0;
        this._localError = '';
        this._render();
        this._refresh();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, this._settings.get_int('refresh-seconds'), () => {
            this._render();
            this._refresh();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _render() {
        const account = this._settings.get_string('account');
        const snapshot = validAccount(account)
            ? this._read(GLib.build_filenamev([this._dataDir(), 'snapshots', `${account}.json`])) : {};
        const remaining = this._settings.get_boolean('show-remaining');
        const staleAfter = Math.max(600, this._settings.get_int('refresh-seconds') * 2 + 120);
        this._view = view(snapshot, account, remaining, Date.now() / 1000, staleAfter);
        if (this._localError) this._view = {...this._view, status: 'error', values: [null, null], text: '5h — · 7d —'};
        const mode = this._settings.get_string('display-mode');
        this._drawing.visible = mode !== 'text';
        this._label.visible = mode === 'text' || mode === 'combined';
        this._label.text = this._view.text + (this._view.status === 'ok' ? '' : ' !');
        this._drawing.queue_repaint();
        const statusText = this._view.status === 'ok' ? 'Live quota' : this._view.status === 'stale' ? 'Stale · refresh required' : 'Unavailable · check login and configuration';
        this._button.set_accessible_name(`GPT ${this._view.label}: ${this._view.text}, ${remaining ? 'remaining' : 'used'}, ${statusText}`);
        const menu = this._button.menu;
        menu.removeAll();
        const info = text => menu.addMenuItem(new PopupMenu.PopupMenuItem(text, {reactive: false, can_focus: false}));
        info(`${this._view.label} · ${remaining ? 'Remaining' : 'Used'}`);
        info(snapshot.identity?.email || 'No verified account');
        info(statusText);
        if (this._localError || snapshot.error?.message)
            info(String(this._localError || snapshot.error.message));
        for (const [index, key] of ['five_hour', 'seven_day'].entries()) {
            info(`${index === 0 ? '5 hours' : '7 days'}: ${percentText(this._view.values[index])}`);
            info(resetText(snapshot.windows?.[key]?.resets_at));
        }
        if (snapshot.updated_at)
            info(`Updated ${new Date(snapshot.updated_at * 1000).toLocaleString()}`);
        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        const accounts = this._read(GLib.build_filenamev([this._dataDir(), 'accounts.json'])).accounts || {};
        for (const [id, profile] of Object.entries(accounts)) {
            if (!validAccount(id)) continue;
            const item = new PopupMenu.PopupMenuItem(`${id === account ? '✓ ' : ''}${profile?.label || id}`);
            item.connect('activate', () => this._settings.set_string('account', id));
            menu.addMenuItem(item);
        }
        const refresh = new PopupMenu.PopupMenuItem(this._process ? 'Refreshing…' : 'Refresh now');
        refresh.setSensitive(!this._process);
        refresh.connect('activate', () => this._refresh());
        menu.addMenuItem(refresh);
        const preferences = new PopupMenu.PopupMenuItem('Preferences');
        preferences.connect('activate', () => this.openPreferences());
        menu.addMenuItem(preferences);
    }

    _refresh() {
        if (!this._enabled || this._process) return;
        const account = this._settings.get_string('account');
        if (!validAccount(account) || !GLib.path_is_absolute(this._dataDir())) {
            this._localError = 'Set an account id and an absolute data directory in Preferences';
            this._render();
            return;
        }
        const generation = this._generation;
        try {
            const command = [this._settings.get_string('python-binary'), '-B',
                GLib.build_filenamev([this.path, 'backend', 'run.py']), '--data-dir', this._dataDir(),
                '--codex', this._settings.get_string('codex-binary'), 'refresh', '--account', account];
            const proc = Gio.Subprocess.new(command, Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE);
            this._process = proc;
            this._localError = '';
            this._watchdog = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 115, () => {
                this._watchdog = 0;
                if (this._process === proc) {
                    try { proc.send_signal(15); } catch (_) { /* Already finished. */ }
                    this._localError = 'Refresh timed out';
                    this._render();
                }
                return GLib.SOURCE_REMOVE;
            });
            proc.wait_async(null, (process, result) => {
                let success = false;
                try { process.wait_finish(result); success = process.get_successful(); } catch (_) { /* Display below. */ }
                if (!this._enabled || generation !== this._generation) return;
                if (this._watchdog) GLib.source_remove(this._watchdog);
                this._watchdog = 0;
                this._process = null;
                if (!success && !this._localError) {
                    const state = this._read(GLib.build_filenamev([this._dataDir(), 'snapshots', `${account}.json`]));
                    this._localError = state.error?.message || 'Refresh failed; check Python, Codex path and account login';
                }
                this._render();
            });
            this._render();
        } catch (_) {
            this._localError = 'Cannot start helper; check Python executable in Preferences';
            this._render();
        }
    }

    _paint(area) {
        const cr = area.get_context();
        try {
            const [width, height] = area.get_surface_size();
            const values = this._view?.values || [null, null];
            const remaining = this._settings.get_boolean('show-remaining');
            const bars = this._settings.get_string('display-mode') === 'bars';
            for (let i = 0; i < 2; i++) {
                const value = values[i];
                cr.setSourceRGBA(0.5, 0.55, 0.6, 0.28);
                if (bars) {
                    const y = 3 + i * 9;
                    cr.rectangle(1, y, width - 2, 5); cr.fill();
                    cr.setSourceRGB(...color(value, remaining));
                    if (value !== null) { cr.rectangle(1, y, (width - 2) * value / 100, 5); cr.fill(); }
                    else { cr.moveTo(width / 2 - 3, y + 2.5); cr.lineTo(width / 2 + 3, y + 2.5); cr.stroke(); }
                } else {
                    const x = width * (i === 0 ? 0.25 : 0.75);
                    const y = height / 2;
                    const radius = Math.min(width / 4 - 2, height / 2 - 3);
                    cr.setLineWidth(3);
                    cr.arc(x, y, radius, 0, 2 * Math.PI); cr.stroke();
                    cr.setSourceRGB(...color(value, remaining));
                    if (value !== null && value > 0) {
                        cr.arc(x, y, radius, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * value / 100); cr.stroke();
                    } else if (value === null) {
                        cr.moveTo(x - 3, y); cr.lineTo(x + 3, y); cr.stroke();
                    }
                }
            }
        } finally {
            cr.$dispose();
        }
    }

    disable() {
        this._enabled = false;
        this._generation++;
        this._cancelRefresh();
        if (this._timer) GLib.source_remove(this._timer);
        this._timer = 0;
        if (this._settingsSignal) this._settings.disconnect(this._settingsSignal);
        this._settingsSignal = 0;
        this._button?.destroy();
        this._button = null;
        this._settings = null;
        this._drawing = null;
        this._label = null;
        this._box = null;
        this._view = null;
    }
}
