import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {proxyRoute, routeEnvironment, routeSummary} from './network.mjs';

// URL lookups use GNOME's resolver (including its configured PAC), not a network
// probe. Never silently fall back to direct if resolution fails or a proxy fails.
export async function resolveNetwork(mode, address, cancellable, resolver = null) {
    if (mode === 'environment')
        return {env: {}, summary: 'Using the launch environment; no GNOME proxy override'};
    if (mode === 'manual') {
        const route = proxyRoute(address);
        if (route === 'direct') throw new Error('Enter a proxy URL for manual mode');
        return {env: routeEnvironment(route, route), summary: routeSummary(route, route)};
    }
    if (mode !== 'system') throw new Error('Unknown proxy mode');
    resolver ??= Gio.ProxyResolver.get_default();
    let timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 15, () => {
        timer = 0; cancellable.cancel(); return GLib.SOURCE_REMOVE;
    });
    const lookup = url => new Promise((resolve, reject) => {
        resolver.lookup_async(url, cancellable, (source, result) => {
            try {
                const routes = source.lookup_finish(result);
                if (!routes?.length) throw new Error('No proxy route returned');
                resolve(proxyRoute(routes[0]));
            } catch (_) {
                reject(new Error('Cannot resolve the GNOME proxy. Try Manual proxy with your local HTTP/mixed port.'));
            }
        });
    });
    try {
        const [auth, quota] = await Promise.all([
            lookup('https://auth.openai.com/oauth/token'),
            lookup('https://chatgpt.com/backend-api/wham/usage'),
        ]);
        return {env: routeEnvironment(auth, quota), summary: routeSummary(auth, quota)};
    } catch (error) {
        cancellable.cancel();
        throw error;
    } finally {
        if (timer) GLib.source_remove(timer);
    }
}

export function launchHelper(argv, env, flags) {
    const launcher = new Gio.SubprocessLauncher({flags});
    try {
        for (const [key, value] of Object.entries(env)) launcher.setenv(key, value, true);
        return launcher.spawnv(argv);
    } finally {
        launcher.close();
    }
}
