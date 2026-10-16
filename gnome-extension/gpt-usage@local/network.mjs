// Pure, credential-free proxy route validation shared by tests and GNOME clients.
export function proxyRoute(value) {
    if (value === 'direct://' || value === 'direct') return 'direct';
    if (typeof value !== 'string') throw new Error('Proxy address is unavailable');
    const match = /^(https?|socks5h?):\/\/(\[[0-9a-fA-F:]+\]|[A-Za-z0-9._-]+)(?::([0-9]{1,5}))?\/?$/.exec(value.trim());
    if (!match || (match[3] && (Number(match[3]) < 1 || Number(match[3]) > 65535)))
        throw new Error('Enter an HTTP, HTTPS or SOCKS5 proxy URL with a valid port and no credentials');
    return value.trim().replace(/\/$/, '');
}

export function routeEnvironment(auth, quota) {
    return {GPT_USAGE_AUTH_PROXY: proxyRoute(auth), GPT_USAGE_QUOTA_PROXY: proxyRoute(quota)};
}

export function routeSummary(auth, quota) {
    const name = value => value === 'direct' ? 'Direct connection' : value;
    return `Sign-in: ${name(auth)} · Quota: ${name(quota)}`;
}
