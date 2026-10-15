import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class Preferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const page = new Adw.PreferencesPage({title: 'GPT Usage', icon_name: 'view-statistics-symbolic'});
        const appearance = new Adw.PreferencesGroup({title: 'Appearance'});
        const connection = new Adw.PreferencesGroup({title: 'Account and connection',
            description: 'Create and log in to a profile with the CLI first. Each profile owns a separate Codex login. Use the same data directory here and in the CLI.'});
        page.add(appearance); page.add(connection); window.add(page);
        const modes = ['text', 'rings', 'bars', 'combined'];
        const mode = new Adw.ComboRow({title: 'Presentation', model: Gtk.StringList.new(['Percentages', 'Dual rings', 'Progress bars', 'Rings + percentages']),
            selected: Math.max(0, modes.indexOf(settings.get_string('display-mode')))});
        mode.connect('notify::selected', () => settings.set_string('display-mode', modes[mode.selected]));
        appearance.add(mode);
        const remaining = new Adw.SwitchRow({title: 'Show remaining quota', subtitle: 'Turn off to show used percentage'});
        settings.bind('show-remaining', remaining, 'active', Gio.SettingsBindFlags.DEFAULT);
        appearance.add(remaining);
        for (const [key, title] of [['account', 'Account profile id'], ['data-directory', 'Absolute data directory (empty: extension/runtime)'],
            ['codex-binary', 'Codex executable (absolute path recommended)'], ['python-binary', 'Python executable']]) {
            const row = new Adw.EntryRow({title, show_apply_button: true, text: settings.get_string(key)});
            row.connect('apply', () => settings.set_string(key, row.text.trim()));
            connection.add(row);
        }
        const interval = new Adw.SpinRow({title: 'Refresh interval (seconds)',
            adjustment: new Gtk.Adjustment({lower: 30, upper: 3600, step_increment: 30, page_increment: 120}),
            value: settings.get_int('refresh-seconds')});
        interval.connect('notify::value', () => settings.set_int('refresh-seconds', interval.value));
        connection.add(interval);
    }
}
