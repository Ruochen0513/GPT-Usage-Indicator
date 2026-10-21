import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import {CompanionClient, DOWNLOAD_URL} from './companion.js';
import {resolveNetwork} from './proxy-resolver.js';
import {validAccount} from './ui.js';
import {authEvent} from './auth-ui.js';

export default class Preferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const lifetime = new Gio.Cancellable();
        let client = new CompanionClient();
        let active = null;
        let diagnostic = null;
        let ready = false;
        let loading = false;
        let ids = [];
        const page = new Adw.PreferencesPage({title: 'GPT Usage', icon_name: 'view-statistics-symbolic'});
        const companion = new Adw.PreferencesGroup({title: 'Linux companion',
            description: 'Install the separate companion once. It handles official sign-in and quota queries; the extension contains no runtime or account credentials.'});
        const setup = new Adw.ActionRow({title: 'Companion connection', subtitle: 'Checking…'});
        const download = new Gtk.LinkButton({label: 'Installation guide', uri: DOWNLOAD_URL, valign: Gtk.Align.CENTER});
        const check = new Gtk.Button({label: 'Check connection', valign: Gtk.Align.CENTER});
        setup.add_suffix(download);
        setup.add_suffix(check);
        companion.add(setup);
        const accounts = new Adw.PreferencesGroup({title: 'Accounts'});
        const selected = new Adw.ComboRow({title: 'Selected account'});
        const id = new Adw.EntryRow({title: 'New profile id (letters, digits, _ or -)'});
        const label = new Adw.EntryRow({title: 'Display name (optional)'});
        const email = new Adw.EntryRow({title: 'Expected ChatGPT email (optional)'});
        for (const row of [selected, id, label, email]) accounts.add(row);
        const addRow = new Adw.ActionRow({title: 'Create profile'});
        const add = new Gtk.Button({label: 'Add account', valign: Gtk.Align.CENTER});
        addRow.add_suffix(add);
        accounts.add(addRow);
        const loginRow = new Adw.ActionRow({title: 'Official ChatGPT authorization'});
        const login = new Gtk.Button({label: 'Sign in', valign: Gtk.Align.CENTER});
        const device = new Gtk.Button({label: 'Device code', valign: Gtk.Align.CENTER});
        const signout = new Gtk.Button({label: 'Sign out', valign: Gtk.Align.CENTER});
        for (const button of [login, device, signout]) loginRow.add_suffix(button);
        accounts.add(loginRow);
        const status = new Adw.ActionRow({title: 'Ready'});
        const cancel = new Gtk.Button({label: 'Cancel', sensitive: false, valign: Gtk.Align.CENTER});
        status.add_suffix(cancel);
        accounts.add(status);
        const authorization = new Adw.ActionRow({title: 'Authorization page', visible: false});
        const open = new Gtk.LinkButton({label: 'Open in browser', uri: 'https://chatgpt.com', valign: Gtk.Align.CENTER});
        authorization.add_suffix(open);
        accounts.add(authorization);
        const code = new Gtk.Label({selectable: true, visible: false, margin_top: 8, margin_bottom: 8});
        accounts.add(code);
        const appearance = new Adw.PreferencesGroup({title: 'Appearance'});
        const modes = ['text', 'rings', 'bars', 'combined'];
        const mode = new Adw.ComboRow({title: 'Presentation',
            model: Gtk.StringList.new(['Percentages', 'Dual rings', 'Progress bars', 'Rings + percentages']),
            selected: Math.max(0, modes.indexOf(settings.get_string('display-mode')))});
        mode.connect('notify::selected', () => settings.set_string('display-mode', modes[mode.selected]));
        appearance.add(mode);
        const remaining = new Adw.SwitchRow({title: 'Show remaining quota', subtitle: 'Turn off to show used percentage'});
        settings.bind('show-remaining', remaining, 'active', Gio.SettingsBindFlags.DEFAULT);
        appearance.add(remaining);
        const interval = new Adw.SpinRow({title: 'Refresh interval (seconds)', value: settings.get_int('refresh-seconds'),
            adjustment: new Gtk.Adjustment({lower: 30, upper: 3600, step_increment: 30, page_increment: 120})});
        interval.connect('notify::value', () => settings.set_int('refresh-seconds', interval.value));
        appearance.add(interval);
        const network = new Adw.PreferencesGroup({title: 'Network proxy',
            description: 'Applies to companion sign-in and quota queries. System and browser settings are unchanged.'});
        const proxyModes = ['system', 'manual', 'environment'];
        const proxyMode = new Adw.ComboRow({title: 'Proxy mode',
            model: Gtk.StringList.new(['GNOME system proxy / PAC', 'Manual proxy URL', 'Inherited launch environment']),
            selected: Math.max(0, proxyModes.indexOf(settings.get_string('proxy-mode')))});
        proxyMode.connect('notify::selected', () => settings.set_string('proxy-mode', proxyModes[proxyMode.selected]));
        network.add(proxyMode);
        const address = new Adw.EntryRow({title: 'Manual URL (e.g. http://127.0.0.1:7897)',
            text: settings.get_string('proxy-url'), show_apply_button: true});
        address.connect('apply', () => settings.set_string('proxy-url', address.text.trim()));
        network.add(address);
        const route = new Adw.ActionRow({title: 'Selected route', subtitle: 'Checks configuration only, not connectivity or IP location.'});
        const routeCheck = new Gtk.Button({label: 'Check route', valign: Gtk.Align.CENTER});
        route.add_suffix(routeCheck);
        network.add(route);
        for (const group of [companion, accounts, appearance, network]) page.add(group);
        window.add(page);
        const controls = [selected, id, label, email, add, login, device, signout];
        const updateControls = () => {
            for (const control of controls) control.sensitive = ready && !active;
            network.sensitive = !active;
            check.sensitive = !active;
            cancel.sensitive = Boolean(active);
        };
        const notifyPanel = () => settings.set_int('refresh-request', (settings.get_int('refresh-request') + 1) % 2147483647);
        const load = async () => {
            const current = client;
            try {
                const state = await current.read(settings.get_string('account'));
                if (lifetime.is_cancelled() || current !== client) return;
                ready = true;
                setup.subtitle = 'Connected. The companion starts on demand and exits when idle.';
                loading = true;
                ids = Object.keys(state.accounts).filter(validAccount);
                selected.model = Gtk.StringList.new(ids.map(key => `${state.accounts[key].label || key} (${key})`));
                let index = ids.indexOf(settings.get_string('account'));
                if (index < 0 && ids.length) {
                    index = 0;
                    settings.set_string('account', ids[0]);
                }
                selected.selected = index < 0 ? Gtk.INVALID_LIST_POSITION : index;
                if (!ids.length) id.text = 'personal';
                loading = false;
            } catch (error) {
                if (lifetime.is_cancelled() || current !== client) return;
                ready = false;
                setup.subtitle = error.message;
            }
            if (!lifetime.is_cancelled()) updateControls();
        };
        selected.connect('notify::selected', () => {
            if (!loading && ids[selected.selected]) settings.set_string('account', ids[selected.selected]);
        });
        const stop = () => {
            active?.cancellable.cancel();
            active = null;
            client.close();
            client = new CompanionClient();
            authorization.visible = false;
            code.visible = false;
            status.title = 'Operation cancelled';
            status.subtitle = '';
            updateControls();
            notifyPanel();
        };
        const perform = async request => {
            if (active || !ready) return;
            const task = {cancellable: new Gio.Cancellable(), failed: false};
            active = task;
            updateControls();
            status.title = 'Working…';
            status.subtitle = '';
            authorization.visible = false;
            code.visible = false;
            try {
                const routes = request.action === 'add' ? {env: {}} : await resolveNetwork(
                    settings.get_string('proxy-mode'), settings.get_string('proxy-url'), task.cancellable);
                if (active !== task) return;
                const success = await client.run({...request, env: routes.env}, value => {
                    if (active !== task) return;
                    const event = authEvent(JSON.stringify(value));
                    if (event?.event === 'authorization') {
                        open.uri = event.url;
                        authorization.visible = true;
                        code.label = event.code;
                        code.visible = Boolean(event.code);
                        status.title = 'Complete sign-in in your browser';
                        Gio.AppInfo.launch_default_for_uri_async(event.url, null, task.cancellable, (_app, result) => {
                            try { Gio.AppInfo.launch_default_for_uri_finish(result); } catch (_) { /* The explicit link remains available. */ }
                        });
                    } else if (event?.event === 'complete') {
                        status.title = `Signed in: ${event.email}`;
                        status.subtitle = event.quota_status === 'ok' ? 'Quota updated.' : 'Signed in; quota is not available yet.';
                    } else if (event?.event === 'error') {
                        task.failed = true;
                        status.title = 'Sign-in failed';
                        status.subtitle = event.message;
                    }
                });
                if (active !== task) return;
                if (!success && !task.failed) status.title = 'Operation failed; check the profile and companion';
                if (success && request.action === 'add') {
                    settings.set_string('account', request.account);
                    id.text = '';
                    label.text = '';
                    email.text = '';
                    status.title = 'Account added. Click Sign in.';
                } else if (success && request.action === 'logout') {
                    status.title = 'Signed out';
                }
            } catch (error) {
                if (active !== task) return;
                status.title = 'Operation failed';
                status.subtitle = error.message;
            } finally {
                if (active === task) {
                    active = null;
                    authorization.visible = false;
                    code.visible = false;
                    updateControls();
                    await load();
                    if (!lifetime.is_cancelled()) notifyPanel();
                }
            }
        };
        add.connect('clicked', () => {
            const account = id.text.trim();
            if (!validAccount(account) || ids.includes(account)) {
                status.title = 'Choose a new, valid profile id';
                return;
            }
            perform({action: 'add', account, label: label.text.trim(), email: email.text.trim()});
        });
        for (const [button, action, useDevice] of [[login, 'login', false], [device, 'login', true], [signout, 'logout', false]]) {
            button.connect('clicked', () => {
                const account = ids[selected.selected];
                if (!account) { status.title = 'Add or select an account first'; return; }
                perform({action, account, device: useDevice});
            });
        }
        cancel.connect('clicked', stop);
        check.connect('clicked', () => {
            client.close();
            client = new CompanionClient();
            load();
        });
        routeCheck.connect('clicked', async () => {
            diagnostic?.cancel();
            const current = new Gio.Cancellable();
            diagnostic = current;
            routeCheck.sensitive = false;
            try {
                const result = await resolveNetwork(settings.get_string('proxy-mode'), settings.get_string('proxy-url'), current);
                if (!lifetime.is_cancelled() && diagnostic === current) route.subtitle = result.summary;
            } catch (_) {
                if (!lifetime.is_cancelled() && diagnostic === current) route.subtitle = 'Cannot resolve proxy; try your local HTTP / mixed port in Manual mode.';
            } finally {
                if (!lifetime.is_cancelled() && diagnostic === current) routeCheck.sensitive = true;
            }
        });
        window.connect('close-request', () => {
            lifetime.cancel();
            active?.cancellable.cancel();
            active = null;
            diagnostic?.cancel();
            client.close();
            return false;
        });
        updateControls();
        load();
    }
}
