import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {CompanionClient, MISSING_COMPANION} from './companion.js';
import {resolveNetwork} from './proxy-resolver.js';
import {view, validAccount, percentText, resetText} from './ui.js';
import {createGraph, paintGraph} from './graph.js';

export default class GPTUsageExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._timer = 0;
        this._session = null;
        this._state = {accounts: {}, snapshot: {}};
        this._error = '';
        this._button = new PanelMenu.Button(0, 'GPT Usage', false);
        const box = new St.BoxLayout({style_class: 'gpt-usage-box', y_align: Clutter.ActorAlign.CENTER});
        this._graph = createGraph();
        this._label = new St.Label({y_align: Clutter.ActorAlign.CENTER});
        this._graph.connect('repaint', area => paintGraph(area, this._view.values,
            this._settings.get_string('display-mode'), this._settings.get_boolean('show-remaining')));
        box.add_child(this._graph);
        box.add_child(this._label);
        this._button.add_child(box);
        Main.panel.addToStatusArea(this.uuid, this._button, 0, 'left');
        this._button.menu.connect('open-state-changed', (_menu, open) => {
            if (open) this._render();
        });
        this._settingsSignal = this._settings.connect('changed', () => this._configure());
        this._configure();
    }

    disable() {
        if (this._timer) GLib.source_remove(this._timer);
        this._timer = 0;
        this._endSession();
        this._settings.disconnect(this._settingsSignal);
        this._settingsSignal = 0;
        this._button.destroy();
        this._button = null;
        this._graph = null;
        this._label = null;
        this._settings = null;
        this._state = null;
        this._view = null;
    }

    _endSession() {
        if (this._session) {
            this._session.cancellable.cancel();
            this._session.client.close();
            this._session = null;
        }
    }

    _configure() {
        this._endSession();
        if (this._timer) GLib.source_remove(this._timer);
        this._error = '';
        // Drop the previous account immediately; never show its email or values.
        this._state = {accounts: this._state.accounts, snapshot: {}};
        this._render();
        this._refresh();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, this._settings.get_int('refresh-seconds'), () => {
            this._render();
            this._refresh();
            return GLib.SOURCE_CONTINUE;
        });
    }

    async _refresh() {
        if (this._session) return;
        const account = this._settings.get_string('account');
        if (!validAccount(account)) {
            this._error = 'Choose a valid account in Preferences';
            this._render();
            return;
        }
        const session = {client: new CompanionClient(), cancellable: new Gio.Cancellable()};
        this._session = session;
        try {
            let state = await session.client.read(account);
            if (this._session !== session) return;
            this._state = state;
            this._error = '';
            this._render();
            if (this._state.accounts[account]) {
                const network = await resolveNetwork(this._settings.get_string('proxy-mode'), this._settings.get_string('proxy-url'), session.cancellable);
                if (this._session !== session) return;
                await session.client.run({action: 'refresh', account, env: network.env});
                if (this._session !== session) return;
                state = await session.client.read(account);
                if (this._session !== session) return;
                this._state = state;
            }
        } catch (error) {
            if (this._session !== session) return;
            this._error = error.message || MISSING_COMPANION;
        } finally {
            if (this._session === session) {
                this._endSession();
                this._render();
            }
        }
    }

    _render() {
        const account = this._settings.get_string('account');
        const remaining = this._settings.get_boolean('show-remaining');
        const mode = this._settings.get_string('display-mode');
        const snapshot = this._state.snapshot;
        this._view = view(snapshot, account, remaining, Date.now() / 1000,
            Math.max(600, 2 * this._settings.get_int('refresh-seconds') + 120));
        if (this._error) this._view = {...this._view, status: 'error', values: [null, null], text: '5h — · 7d —'};
        this._graph.visible = mode !== 'text';
        this._label.visible = mode === 'text' || mode === 'combined';
        this._label.text = this._view.text + (this._view.status === 'ok' ? '' : ' !');
        this._graph.queue_repaint();
        this._button.set_accessible_name(`GPT ${this._view.label}: ${this._view.text}, ${remaining ? 'remaining' : 'used'}`);
        const menu = this._button.menu;
        menu.removeAll();
        const info = text => menu.addMenuItem(new PopupMenu.PopupMenuItem(String(text), {reactive: false, can_focus: false}));
        info(`${this._view.label} · ${remaining ? 'Remaining' : 'Used'}`);
        info(snapshot.identity?.email || 'No verified account');
        info(this._error || snapshot.error?.message || (this._view.status === 'ok' ? 'Live quota' : 'Open Preferences to set up your account'));
        for (const [index, key] of ['five_hour', 'seven_day'].entries()) {
            info(`${index === 0 ? '5 hours' : '7 days'}: ${percentText(this._view.values[index])}`);
            info(resetText(snapshot.windows?.[key]?.resets_at));
        }
        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        for (const [id, profile] of Object.entries(this._state.accounts)) {
            if (!validAccount(id)) continue;
            const item = new PopupMenu.PopupMenuItem(profile.label || id);
            item.setOrnament(id === account ? PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
            item.connect('activate', () => this._settings.set_string('account', id));
            menu.addMenuItem(item);
        }
        const refresh = new PopupMenu.PopupMenuItem(this._session ? 'Refreshing…' : 'Refresh now');
        refresh.setSensitive(!this._session);
        refresh.connect('activate', () => this._refresh());
        menu.addMenuItem(refresh);
        const preferences = new PopupMenu.PopupMenuItem('Preferences');
        preferences.connect('activate', () => this.openPreferences());
        menu.addMenuItem(preferences);
    }
}
