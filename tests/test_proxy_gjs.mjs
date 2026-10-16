import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {resolveNetwork, launchHelper} from '../gnome-extension/gpt-usage@local/proxy-resolver.js';
function check(value, text) { if (!value) throw new Error(text); }
const resolver = {
    lookup_async(url, cancellable, callback) {
        GLib.idle_add(GLib.PRIORITY_DEFAULT, () => { callback(this, url); return GLib.SOURCE_REMOVE; });
    },
    lookup_finish(url) {
        return [url.includes('auth.openai.com') ? 'http://127.0.0.1:7897' : 'socks5h://127.0.0.1:7898'];
    },
};
const routed = await resolveNetwork('system', '', new Gio.Cancellable(), resolver);
check(routed.env.GPT_USAGE_AUTH_PROXY === 'http://127.0.0.1:7897', 'auth proxy from resolver');
check(routed.env.GPT_USAGE_QUOTA_PROXY === 'socks5h://127.0.0.1:7898', 'quota proxy from resolver');
const manual = await resolveNetwork('manual', 'http://127.0.0.1:7897', new Gio.Cancellable(), resolver);
check(manual.env.GPT_USAGE_AUTH_PROXY === manual.env.GPT_USAGE_QUOTA_PROXY, 'manual route consistent');
const inherited = await resolveNetwork('environment', '', new Gio.Cancellable(), resolver);
check(Object.keys(inherited.env).length === 0, 'inherited mode untouched');
const child = launchHelper(['python3', '-B', '-c', 'import os; print(os.environ["GPT_USAGE_AUTH_PROXY"])'], manual.env, Gio.SubprocessFlags.STDOUT_PIPE);
const [ok, stdout] = child.communicate_utf8(null, null);
check(ok && child.get_successful() && stdout.trim() === 'http://127.0.0.1:7897', 'Gio launcher passes proxy to helper');
const cancelled = new Gio.Cancellable();
const badResolver = {...resolver, lookup_finish() { throw new Error('SECRET_DIAGNOSTIC'); }};
try {
    await resolveNetwork('system', '', cancelled, badResolver);
    throw new Error('expected resolver failure');
} catch (error) {
    check(cancelled.is_cancelled(), 'failed lookup cancels sibling lookup');
    check(!error.message.includes('SECRET_DIAGNOSTIC'), 'resolver error redacted');
}
print('GJS asynchronous proxy resolution and real helper environment checks passed');
