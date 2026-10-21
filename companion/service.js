import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import System from 'system';
import {BUS_NAME, OBJECT_PATH, INTERFACE_XML, requestArguments} from './protocol.js';
import {validAccount} from './ui.js';
import {authEvent} from './auth-ui.js';

// Older GNOME 46 installations expose Unix signal functions through GLib;
// newer introspection runtimes moved them into GLibUnix.
let addUnixSignal;
try {
    const {default: unix} = await import('gi://GLibUnix');
    addUnixSignal = unix.signal_add_full;
} catch (_) {
    addUnixSignal = GLib.unix_signal_add;
}

const root = Gio.File.new_for_uri(import.meta.url).get_parent().get_parent().get_path();
const dataDir = GLib.build_filenamev([GLib.get_user_data_dir(), 'gpt-usage-indicator']);
const loop = new GLib.MainLoop(null, false);
const jobs = new Map();
let connection = null;
let exported = null;
let idleTimer = 0;
let stopRequested = false;

function readJson(path) {
    try {
        const file = Gio.File.new_for_path(path);
        if (file.query_info('standard::size', Gio.FileQueryInfoFlags.NONE, null).get_size() > 65536) return {};
        const [ok, bytes] = file.load_contents(null);
        const value = ok ? JSON.parse(new TextDecoder().decode(bytes)) : {};
        return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    } catch (_) {
        return {};
    }
}

function armIdle() {
    if (idleTimer) GLib.source_remove(idleTimer);
    idleTimer = 0;
    if (!jobs.size) {
        idleTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 60, () => {
            idleTimer = 0;
            loop.quit();
            return GLib.SOURCE_REMOVE;
        });
    }
}

function publish(job, event) {
    if (job.watching && !connection.is_closed())
        connection.emit_signal(job.sender, OBJECT_PATH, BUS_NAME, 'Event', new GLib.Variant('(ss)', [job.id, JSON.stringify(event)]));
}

function cancel(job) {
    job.cancelled = true;
    if (job.process && !job.exited) {
        try { job.process.send_signal(15); } catch (_) { /* The child may already have exited. */ }
    }
}

function finish(job) {
    if (!job.eof || !job.exited) return;
    if (job.timer) GLib.source_remove(job.timer);
    if (job.watch) Gio.bus_unwatch_name(job.watch);
    job.stream.close(null);
    publish(job, {event: 'finished', success: job.success && !job.cancelled});
    jobs.delete(job.id);
    if (stopRequested && !jobs.size) loop.quit();
    else armIdle();
}

function launch(job, request) {
    const launcher = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE});
    // Never inherit route overrides from a previous request or an activating shell.
    launcher.unsetenv('GPT_USAGE_AUTH_PROXY');
    launcher.unsetenv('GPT_USAGE_QUOTA_PROXY');
    for (const [key, value] of Object.entries(request.env)) launcher.setenv(key, value, true);
    try {
        job.process = launcher.spawnv(['python3', '-B', GLib.build_filenamev([root, 'backend', 'run.py']),
            '--data-dir', dataDir, '--codex', GLib.build_filenamev([root, 'backend', 'vendor', 'codex']), ...request.argv]);
    } finally {
        launcher.close();
    }
    job.stream = new Gio.DataInputStream({base_stream: job.process.get_stdout_pipe()});
    const read = () => job.stream.read_line_async(GLib.PRIORITY_DEFAULT, null, (source, result) => {
        try {
            const [line] = source.read_line_finish_utf8(result);
            if (line === null) {
                job.eof = true;
                finish(job);
                return;
            }
            if (line.length > 20000) {
                cancel(job);
            } else if (request.action === 'login') {
                const event = authEvent(line);
                if (event) publish(job, event);
            }
        } catch (_) {
            cancel(job);
            job.eof = true;
            finish(job);
            return;
        }
        read();
    });
    read();
    job.process.wait_async(null, (process, result) => {
        try {
            process.wait_finish(result);
            job.success = process.get_successful();
        } catch (_) {
            job.success = false;
        }
        job.exited = true;
        finish(job);
    });
    job.watch = Gio.bus_watch_name_on_connection(connection, job.sender, Gio.BusNameWatcherFlags.NONE, null, () => {
        job.watching = false;
        cancel(job);
    });
    job.timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, request.action === 'login' ? 420 : 115, () => {
        job.timer = 0;
        cancel(job);
        return GLib.SOURCE_REMOVE;
    });
}

const implementation = {
    Read(account) {
        if (!validAccount(account)) throw new Error('Invalid account');
        const config = readJson(GLib.build_filenamev([dataDir, 'accounts.json']));
        const accounts = {};
        for (const [id, profile] of Object.entries(config.accounts || {})) {
            if (validAccount(id) && profile && typeof profile === 'object') accounts[id] = {label: String(profile.label || id).slice(0, 100)};
        }
        return JSON.stringify({protocol: 1, accounts, snapshot: readJson(GLib.build_filenamev([dataDir, 'snapshots', `${account}.json`]))});
    },
    StartAsync([id, json], invocation) {
        try {
            if (!/^[a-f0-9-]{36}$/.test(id) || jobs.has(id)) throw new Error('Invalid operation id');
            const request = requestArguments(json);
            if (jobs.size >= 4 || [...jobs.values()].some(job => job.account === request.account || (job.action === 'add' && request.action === 'add'))) {
                invocation.return_dbus_error(`${BUS_NAME}.Busy`, 'Another operation is using this account');
                return;
            }
            const job = {id, action: request.action, account: request.account, sender: invocation.get_sender(), watching: true, watch: 0,
                timer: 0, process: null, stream: null, eof: false, exited: false, success: false, cancelled: false};
            jobs.set(id, job);
            armIdle();
            try {
                launch(job, request);
            } catch (_) {
                jobs.delete(id);
                armIdle();
                throw new Error('Cannot launch companion helper; check Python 3.10+ and reinstall the companion');
            }
            invocation.return_value(null);
        } catch (error) {
            invocation.return_dbus_error(`${BUS_NAME}.Error`, error.message);
        }
    },
    CancelAsync([id], invocation) {
        const job = jobs.get(id);
        if (job && job.sender === invocation.get_sender()) cancel(job);
        invocation.return_value(null);
    },
};

function shutdown() {
    stopRequested = true;
    for (const job of jobs.values()) cancel(job);
    if (!jobs.size) loop.quit();
}

const owner = Gio.bus_own_name(Gio.BusType.SESSION, BUS_NAME, Gio.BusNameOwnerFlags.NONE, bus => {
    connection = bus;
    exported = Gio.DBusExportedObject.wrapJSObject(INTERFACE_XML, implementation);
    exported.export(bus, OBJECT_PATH);
}, () => armIdle(), shutdown);
const signals = [2, 15].map(signal => addUnixSignal(GLib.PRIORITY_DEFAULT, signal, () => {
    shutdown();
    return GLib.SOURCE_CONTINUE;
}));
loop.run();
for (const signal of signals) GLib.source_remove(signal);
if (idleTimer) GLib.source_remove(idleTimer);
if (exported) exported.unexport();
Gio.bus_unown_name(owner);
System.exit(0);
