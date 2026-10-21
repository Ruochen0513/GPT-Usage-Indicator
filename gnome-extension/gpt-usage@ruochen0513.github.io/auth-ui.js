// Validate the small public event protocol; never display arbitrary helper output.
export function authEvent(line) {
    if (typeof line !== 'string' || line.length > 20000) throw new Error('Invalid login event');
    const value = JSON.parse(line);
    if (!value || typeof value !== 'object') throw new Error('Invalid login event');
    if (value.event === 'authorization') {
        // GJS has no browser URL global on some supported releases.
        if (typeof value.url !== 'string' || !/^https:\/\/(auth\.openai\.com|auth0\.openai\.com|chatgpt\.com)(:443)?([/?#]|$)/.test(value.url) || /[\s\\]/.test(value.url))
            throw new Error('Authorization address is not an official HTTPS page');
        if (value.code !== undefined && (typeof value.code !== 'string' || value.code.length > 128))
            throw new Error('Invalid device code');
        return {event: 'authorization', url: value.url, code: value.code || ''};
    }
    if (value.event === 'complete' && typeof value.email === 'string')
        return {event: 'complete', email: value.email.slice(0, 254), quota_status: value.quota_status};
    if (value.event === 'error' && typeof value.message === 'string')
        return {event: 'error', message: value.message.slice(0, 500)};
    return null;
}
