import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import {validAccount} from './ui.mjs';
import {authEvent} from './auth-ui.mjs';

export default class Preferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        let closed = false, active = null, ids = [], loading = false;
        const dataDir = () => settings.get_string('data-directory') || GLib.build_filenamev([GLib.get_user_data_dir(), 'gpt-usage-indicator']);
        const page = new Adw.PreferencesPage({title: 'GPT Usage', icon_name: 'view-statistics-symbolic'});
        const accounts = new Adw.PreferencesGroup({title: 'Accounts', description: 'Add a profile and sign in here. Authorization opens the official ChatGPT page in your browser.'});
        const appearance = new Adw.PreferencesGroup({title: 'Appearance'});
        const connection = new Adw.PreferencesGroup({title: 'Advanced', description: 'The full distribution includes Codex. Leave executable names unchanged to use the bundled runtime.'});
        page.add(accounts); page.add(appearance); page.add(connection); window.add(page);
        const selected = new Adw.ComboRow({title: 'Selected account'});
        accounts.add(selected);
        const id = new Adw.EntryRow({title: 'New profile id (letters, digits, _ or -)'});
        const label = new Adw.EntryRow({title: 'Display name (optional)'});
        const email = new Adw.EntryRow({title: 'Expected ChatGPT email (optional)'});
        for (const row of [id, label, email]) accounts.add(row);
        const actions = new Adw.ActionRow({title: 'Profile setup'});
        const add = new Gtk.Button({label: 'Add account', valign: Gtk.Align.CENTER});
        actions.add_suffix(add); accounts.add(actions);
        const loginRow = new Adw.ActionRow({title: 'Sign in to selected account'});
        const login = new Gtk.Button({label: 'Sign in', valign: Gtk.Align.CENTER});
        const device = new Gtk.Button({label: 'Device code', valign: Gtk.Align.CENTER});
        loginRow.add_suffix(login); loginRow.add_suffix(device); accounts.add(loginRow);
        const status = new Adw.ActionRow({title: 'Ready', subtitle: 'No terminal commands or repository checkout required.'});
        const cancel = new Gtk.Button({label: 'Cancel', sensitive: false, valign: Gtk.Align.CENTER});
        status.add_suffix(cancel); accounts.add(status);
        const authorization = new Adw.ActionRow({title: 'Authorization page', visible: false});
        const open = new Gtk.LinkButton({label: 'Open in browser', uri: 'https://chatgpt.com', valign: Gtk.Align.CENTER});
        authorization.add_suffix(open); accounts.add(authorization);
        const code = new Gtk.Label({selectable: true, visible: false, margin_top: 8, margin_bottom: 8});
        accounts.add(code);
        const signoutRow = new Adw.ActionRow({title: 'Sign out', subtitle: 'Clears this profile’s credentials and displayed quotas.'});
        const signout = new Gtk.Button({label: 'Sign out', valign: Gtk.Align.CENTER});
        signoutRow.add_suffix(signout); accounts.add(signoutRow);
        const controls = [selected, id, label, email, add, login, device, signout];
        const sensitive = busy => {
            for (const control of controls) control.set_sensitive(!busy);
            connection.set_sensitive(!busy);
            cancel.set_sensitive(busy);
        };
        const notifyPanel = () => settings.set_int('refresh-request', (settings.get_int('refresh-request') + 1) % 2147483647);
        const load = () => {
            loading = true;
            let profiles = {};
            try {
                const file = Gio.File.new_for_path(GLib.build_filenamev([dataDir(), 'accounts.json']));
                if (file.query_info('standard::size', Gio.FileQueryInfoFlags.NONE, null).get_size() < 65536) {
                    const [ok, bytes] = file.load_contents(null);
                    const value = ok ? JSON.parse(new TextDecoder().decode(bytes)) : {};
                    profiles = value?.accounts || {};
                }
            } catch (_) { /* Fresh install has no accounts yet. */ }
            ids = Object.keys(profiles).filter(validAccount);
            selected.model = Gtk.StringList.new(ids.map(key => `${profiles[key]?.label || key} (${key})`));
            selected.selected = ids.includes(settings.get_string('account')) ? ids.indexOf(settings.get_string('account')) : Gtk.INVALID_LIST_POSITION;
            if (!ids.length) id.text = 'personal';
            loading = false;
        };
        selected.connect('notify::selected', () => {
            if (!loading && ids[selected.selected]) settings.set_string('account', ids[selected.selected]);
        });
        const stop = (message = 'Sign-in cancelled') => {
            if (!active) return;
            const task = active;
            active = null;
            if (task.timer) GLib.source_remove(task.timer);
            task.cancellable.cancel();
            try { task.process.send_signal(15); } catch (_) { /* Already exited. */ }
            if (!closed) {
                sensitive(false); status.title = message; status.subtitle = 'You can try again.';
                authorization.visible = false; code.visible = false;
            }
        };
        const run = (args, kind, done = () => {}) => {
            if (active || closed) return;
            const dir = dataDir();
            if (!GLib.path_is_absolute(dir)) { status.title = 'Data directory must be absolute'; return; }
            const argv = [settings.get_string('python-binary'), '-B', GLib.build_filenamev([this.path, 'backend', 'run.py']),
                '--data-dir', dir, '--codex', settings.get_string('codex-binary'), ...args];
            try {
                const proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
                const task = {process: proc, cancellable: new Gio.Cancellable(), timer: 0, eof: false, exited: false, success: false, complete: false, failed: false};
                active = task;
                sensitive(true); status.title = kind === 'login' ? 'Starting secure sign-in…' : 'Working…'; status.subtitle = '';
                authorization.visible = false; code.visible = false;
                const finish = () => {
                    if (active !== task || closed || !task.eof || !task.exited) return;
                    active = null;
                    if (task.timer) GLib.source_remove(task.timer);
                    sensitive(false);
                    if (!task.success || (kind === 'login' && !task.complete)) {
                        if (!task.failed) { status.title = 'Operation failed'; status.subtitle = 'Check the runtime, account and data directory, then retry.'; }
                    } else {
                        done();
                    }
                    authorization.visible = false; code.visible = false;
                    load(); notifyPanel();
                };
                const stream = new Gio.DataInputStream({base_stream: proc.get_stdout_pipe()});
                const read = () => stream.read_line_async(GLib.PRIORITY_DEFAULT, task.cancellable, (source, result) => {
                    try {
                        const [line] = source.read_line_finish_utf8(result);
                        if (active !== task || closed) return;
                        if (line === null) { task.eof = true; finish(); return; }
                        if (kind === 'login') {
                            const event = authEvent(line);
                            if (event?.event === 'authorization') {
                                open.uri = event.url; authorization.visible = true;
                                code.label = event.code; code.visible = Boolean(event.code);
                                status.title = 'Complete sign-in in your browser';
                                status.subtitle = event.code ? 'Enter the device code shown below.' : 'Return here after authorizing your account.';
                                Gio.AppInfo.launch_default_for_uri_async(event.url, null, task.cancellable, (app, launched) => {
                                    try { Gio.AppInfo.launch_default_for_uri_finish(launched); } catch (_) { /* Link remains available. */ }
                                });
                            } else if (event?.event === 'complete') {
                                task.complete = true; status.title = `Signed in: ${event.email}`;
                                status.subtitle = event.quota_status === 'ok' ? 'Quota updated.' : 'Signed in; quota could not be loaded yet.';
                            } else if (event?.event === 'error') {
                                task.failed = true; status.title = 'Sign-in failed'; status.subtitle = event.message;
                            }
                        }
                        read();
                    } catch (_) { if (active === task && !closed) stop('Cannot read sign-in response'); }
                });
                read();
                proc.wait_async(null, (process, result) => {
                    try { process.wait_finish(result); task.success = process.get_successful(); } catch (_) { /* Failure shown below. */ }
                    task.exited = true; finish();
                });
                task.timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 420, () => {
                    task.timer = 0;
                    if (active === task) stop('Authorization timed out');
                    return GLib.SOURCE_REMOVE;
                });
            } catch (_) { sensitive(false); status.title = 'Cannot start account helper'; status.subtitle = 'Check the Python executable in Advanced.'; }
        };
        add.connect('clicked', () => {
            const key = id.text.trim();
            if (!validAccount(key)) { status.title = 'Invalid profile id'; return; }
            if (ids.includes(key)) { status.title = 'Profile id already exists'; return; }
            run(['account', 'add', key, '--label', label.text.trim() || key, '--email', email.text.trim()], 'add', () => {
                settings.set_string('account', key); id.text = ''; label.text = ''; email.text = '';
                status.title = 'Account added'; status.subtitle = 'Click Sign in to authorize this account.';
            });
        });
        const begin = useDevice => {
            const account = ids[selected.selected];
            if (!account) { status.title = 'Add or select an account first'; return; }
            run(['login', '--account', account, '--gui', ...(useDevice ? ['--device-auth'] : [])], 'login');
        };
        login.connect('clicked', () => begin(false)); device.connect('clicked', () => begin(true));
        signout.connect('clicked', () => {
            const account = ids[selected.selected];
            if (!account) { status.title = 'Select an account first'; return; }
            run(['logout', '--account', account], 'logout', () => { status.title = 'Signed out'; status.subtitle = 'Quota cleared.'; });
        });
        cancel.connect('clicked', () => stop());
        window.connect('close-request', () => { closed = true; stop(); return false; });
        load();
        const modes = ['text', 'rings', 'bars', 'combined'];
        const mode = new Adw.ComboRow({title: 'Presentation', model: Gtk.StringList.new(['Percentages', 'Dual rings', 'Progress bars', 'Rings + percentages']),
            selected: Math.max(0, modes.indexOf(settings.get_string('display-mode')))});
        mode.connect('notify::selected', () => settings.set_string('display-mode', modes[mode.selected])); appearance.add(mode);
        const remaining = new Adw.SwitchRow({title: 'Show remaining quota', subtitle: 'Turn off to show used percentage'});
        settings.bind('show-remaining', remaining, 'active', Gio.SettingsBindFlags.DEFAULT); appearance.add(remaining);
        for (const [key, title] of [['data-directory', 'Data directory (empty: persistent user data)'], ['codex-binary', 'Codex executable (codex: use bundled runtime)'], ['python-binary', 'Python executable']]) {
            const row = new Adw.EntryRow({title, show_apply_button: true, text: settings.get_string(key)});
            row.connect('apply', () => { settings.set_string(key, row.text.trim()); load(); }); connection.add(row);
        }
        const interval = new Adw.SpinRow({title: 'Refresh interval (seconds)', adjustment: new Gtk.Adjustment({lower: 30, upper: 3600, step_increment: 30, page_increment: 120}), value: settings.get_int('refresh-seconds')});
        interval.connect('notify::value', () => settings.set_int('refresh-seconds', interval.value)); connection.add(interval);
    }
}
