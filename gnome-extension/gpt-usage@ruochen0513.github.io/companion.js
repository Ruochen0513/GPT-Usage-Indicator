import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const BUS_NAME = 'io.github.Ruochen0513.GptUsage';
const OBJECT_PATH = '/io/github/Ruochen0513/GptUsage';
export const DOWNLOAD_URL = 'https://github.com/Ruochen0513/GPT-Usage-Indicator#gnome-extensions-platform-edition';
export const MISSING_COMPANION = 'Companion unavailable. Install the separate Linux companion from the project page, then retry.';

export class CompanionClient {
    constructor() {
        this._cancellable = new Gio.Cancellable();
        this._connection = null;
        this._connecting = null;
        this._subscription = 0;
        this._jobs = new Map();
    }

    async _connect() {
        if (this._connection) return this._connection;
        this._connecting ??= new Promise((resolve, reject) => {
            Gio.bus_get(Gio.BusType.SESSION, this._cancellable, (_source, result) => {
                try {
                    const connection = Gio.bus_get_finish(result);
                    if (this._cancellable.is_cancelled()) throw new Error('Cancelled');
                    this._connection = connection;
                    this._subscription = connection.signal_subscribe(BUS_NAME, BUS_NAME, 'Event', OBJECT_PATH, null,
                        Gio.DBusSignalFlags.NONE, (_bus, _sender, _path, _interface, _signal, parameters) => {
                            const [id, json] = parameters.deepUnpack();
                            const job = this._jobs.get(id);
                            if (!job) return;
                            try {
                                const event = JSON.parse(json);
                                if (event.event === 'finished') {
                                    this._jobs.delete(id);
                                    GLib.source_remove(job.timer);
                                    job.resolve(event.success === true);
                                } else {
                                    job.onEvent(event);
                                }
                            } catch (_) {
                                this._jobs.delete(id);
                                GLib.source_remove(job.timer);
                                this._cancel(id);
                                job.reject(new Error('Invalid companion response'));
                            }
                        });
                    resolve(connection);
                } catch (error) {
                    reject(error);
                }
            });
        });
        return this._connecting;
    }

    async _call(method, parameters) {
        const connection = await this._connect();
        return new Promise((resolve, reject) => {
            connection.call(BUS_NAME, OBJECT_PATH, BUS_NAME, method, parameters, null,
                Gio.DBusCallFlags.NONE, 15000, this._cancellable, (bus, result) => {
                    try { resolve(bus.call_finish(result)); }
                    catch (error) {
                        const name = Gio.DBusError.get_remote_error(error);
                        reject(new Error(name === `${BUS_NAME}.Busy`
                            ? 'Another operation is using this account. Wait for it to finish, then retry.' : MISSING_COMPANION));
                    }
                });
        });
    }

    async read(account) {
        const result = await this._call('Read', new GLib.Variant('(s)', [account]));
        const [json] = result.deepUnpack();
        if (json.length > 150000) throw new Error('Companion response is too large');
        const state = JSON.parse(json);
        if (state.protocol !== 1) throw new Error('Update the companion to a compatible version');
        return state;
    }

    run(request, onEvent = () => {}) {
        const id = GLib.uuid_string_random();
        return new Promise((resolve, reject) => {
            const timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, request.action === 'login' ? 435 : 130, () => {
                this._jobs.delete(id);
                this._cancel(id);
                reject(new Error('Companion operation timed out'));
                return GLib.SOURCE_REMOVE;
            });
            this._jobs.set(id, {resolve, reject, onEvent, timer});
            this._call('Start', new GLib.Variant('(ss)', [id, JSON.stringify(request)])).catch(error => {
                if (this._jobs.delete(id)) {
                    GLib.source_remove(timer);
                    reject(error);
                }
            });
        });
    }

    _cancel(id) {
        if (!this._connection) return;
        this._connection.call(BUS_NAME, OBJECT_PATH, BUS_NAME, 'Cancel', new GLib.Variant('(s)', [id]), null,
            Gio.DBusCallFlags.NO_AUTO_START, 3000, null, (bus, result) => {
                try { bus.call_finish(result); } catch (_) { /* Service may already have exited. */ }
            });
    }

    close() {
        if (this._connection) {
            for (const id of this._jobs.keys()) this._cancel(id);
            if (this._subscription) this._connection.signal_unsubscribe(this._subscription);
        }
        for (const job of this._jobs.values()) {
            GLib.source_remove(job.timer);
            job.reject(new Error('Cancelled'));
        }
        this._jobs.clear();
        this._cancellable.cancel();
        this._connection = null;
        this._subscription = 0;
    }
}
