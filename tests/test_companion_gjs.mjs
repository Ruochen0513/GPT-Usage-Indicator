import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import System from 'system';

const root = ARGV[0];
const extension = Gio.File.new_for_path(`${root}/gnome-extension/gpt-usage@ruochen0513.github.io`).get_uri();
const {CompanionClient} = await import(`${extension}/companion.js`);
const {BUS_NAME, OBJECT_PATH} = await import(Gio.File.new_for_path(`${root}/companion/protocol.js`).get_uri());
const assert = (value, message) => { if (!value) throw new Error(message); };
const pause = ms => new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { resolve(); return GLib.SOURCE_REMOVE; }));

async function test() {
    print('integration: connecting');
    const client = new CompanionClient();
    // Wait until the manually started service owns its name in this private bus.
    let state;
    for (let attempt = 0; attempt < 30; attempt++) {
        try { state = await client.read('personal'); break; } catch (_) { await pause(100); }
    }
    assert(state?.protocol === 1, 'service must respond');
    print('integration: adding');
    assert(await client.run({action: 'add', account: 'personal', label: 'Offline profile', email: ''}), 'add profile');
    print('integration: reading profile');
    state = await client.read('personal');
    assert(state.accounts.personal.label === 'Offline profile', 'account list');
    assert(await client.run({action: 'refresh', account: 'personal',
        env: {GPT_USAGE_AUTH_PROXY: 'http://127.0.0.1:7897', GPT_USAGE_QUOTA_PROXY: 'direct'}}), 'refresh');
    state = await client.read('personal');
    assert(state.snapshot.test_routes[0] === 'http://127.0.0.1:7897' && state.snapshot.test_routes[1] === 'direct', 'independent routes');
    await client.run({action: 'refresh', account: 'personal'});
    state = await client.read('personal');
    assert(state.snapshot.test_routes.every(value => value === null), 'routes must not leak to subsequent operations');
    let rejected = false;
    try { await client.run({action: 'execute', account: 'personal'}); } catch (_) { rejected = true; }
    assert(rejected, 'arbitrary operations rejected');
    rejected = false;
    try { await client.run({action: 'refresh', account: '../outside'}); } catch (_) { rejected = true; }
    assert(rejected, 'path traversal rejected');

    // A distinct session-bus connection must not receive private authorization events.
    const address = GLib.getenv('DBUS_SESSION_BUS_ADDRESS');
    const observer = Gio.DBusConnection.new_for_address_sync(address,
        Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION, null, null);
    let leaked = false;
    const subscription = observer.signal_subscribe(BUS_NAME, BUS_NAME, 'Event', OBJECT_PATH, null, Gio.DBusSignalFlags.NONE, () => { leaked = true; });
    const login = new CompanionClient();
    let authorized;
    const authorization = new Promise(resolve => { authorized = resolve; });
    const pending = login.run({action: 'login', account: 'personal', device: false}, event => {
        if (event.event === 'authorization') authorized(event);
    }).then(() => false, () => true);
    const event = await authorization;
    assert(event.code === 'TEST-ONLY', 'authorization event reaches initiating client');
    await pause(100);
    assert(!leaked, 'authorization must not be broadcast');
    login.close();
    assert(await pending, 'closing client cancels local wait');
    const cancelled = `${GLib.get_user_data_dir()}/gpt-usage-indicator/personal-cancelled`;
    for (let attempt = 0; attempt < 30 && !GLib.file_test(cancelled, GLib.FileTest.EXISTS); attempt++) await pause(100);
    assert(GLib.file_test(cancelled, GLib.FileTest.EXISTS), 'cancel must terminate helper');
    observer.signal_unsubscribe(subscription);
    const rawCall = (bus, method, parameters) => new Promise((resolve, reject) => {
        bus.call(BUS_NAME, OBJECT_PATH, BUS_NAME, method, parameters, null, Gio.DBusCallFlags.NONE, 5000, null, (source, result) => {
            try { resolve(source.call_finish(result)); } catch (error) { reject(error); }
        });
    });
    const foreignId = GLib.uuid_string_random();
    let foreignAuthorized;
    const foreignReady = new Promise(resolve => { foreignAuthorized = resolve; });
    const foreignSubscription = observer.signal_subscribe(BUS_NAME, BUS_NAME, 'Event', OBJECT_PATH, null,
        Gio.DBusSignalFlags.NONE, (_bus, _sender, _path, _interface, _signal, parameters) => {
            const [operation, payload] = parameters.deepUnpack();
            if (operation === foreignId && JSON.parse(payload).event === 'authorization') foreignAuthorized();
        });
    await rawCall(observer, 'Start', new GLib.Variant('(ss)', [foreignId,
        JSON.stringify({action: 'login', account: 'ownerexit', device: false})]));
    await foreignReady;
    await rawCall(Gio.DBus.session, 'Cancel', new GLib.Variant('(s)', [foreignId]));
    await pause(100);
    const ownerCancelled = `${GLib.get_user_data_dir()}/gpt-usage-indicator/ownerexit-cancelled`;
    assert(!GLib.file_test(ownerCancelled, GLib.FileTest.EXISTS), 'another caller cannot cancel an operation');
    observer.signal_unsubscribe(foreignSubscription);
    observer.close_sync(null);
    for (let attempt = 0; attempt < 30 && !GLib.file_test(ownerCancelled, GLib.FileTest.EXISTS); attempt++) await pause(100);
    assert(GLib.file_test(ownerCancelled, GLib.FileTest.EXISTS), 'caller disappearance terminates its helper');

    const bad = new CompanionClient();
    let untrustedUrl = false;
    const badResult = await bad.run({action: 'login', account: 'badurl', device: true}, () => { untrustedUrl = true; });
    assert(!badResult && !untrustedUrl, 'untrusted authorization URL rejected before D-Bus emission');
    bad.close();
    client.close();
    print('D-Bus integration: profile, refresh, route isolation, validation, private events, cancellation and URL checks passed');
}

const watchdog = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 20, () => {
    printerr('D-Bus integration timed out');
    System.exit(1);
});
try {
    await test();
} finally {
    GLib.source_remove(watchdog);
}
