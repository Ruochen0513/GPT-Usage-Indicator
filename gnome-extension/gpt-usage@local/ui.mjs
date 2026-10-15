// Pure presentation functions shared by the extension and Node/GJS tests.
export const validAccount = id => typeof id === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,47}$/.test(id);
export const finite = value => typeof value === 'number' && Number.isFinite(value);
export const clamp = value => Math.max(0, Math.min(100, value));
export const percentText = value => value === null ? '—' : `${Math.round(value)}%`;

export function view(snapshot, account, remaining, now = Date.now() / 1000, staleAfter = 600) {
    const valid = snapshot?.schema_version === 1 && snapshot.account_id === account;
    let status = valid ? snapshot.status : 'unknown';
    if (status === 'ok' && (!finite(snapshot.updated_at) || now - snapshot.updated_at > staleAfter || snapshot.updated_at > now + 60))
        status = 'stale';
    const values = ['five_hour', 'seven_day'].map(key => {
        const item = snapshot?.windows?.[key];
        if (!valid || status !== 'ok' || !item || (finite(item.resets_at) && item.resets_at <= now))
            return null;
        const value = item[remaining ? 'remaining_percent' : 'used_percent'];
        return finite(value) ? clamp(value) : null;
    });
    return {status, values, label: valid ? String(snapshot.label || account) : account,
        text: `5h ${percentText(values[0])} · 7d ${percentText(values[1])}`};
}

export function color(value, remaining) {
    if (value === null) return [0.55, 0.59, 0.65];
    const available = remaining ? value : 100 - value;
    return available <= 10 ? [0.96, 0.36, 0.40] : available <= 25 ? [0.98, 0.73, 0.29] : [0.35, 0.83, 0.68];
}

export function resetText(timestamp, now = Date.now() / 1000) {
    if (!finite(timestamp)) return 'Reset time unavailable';
    if (timestamp <= now) return 'Reset due · awaiting refresh';
    return `Resets ${new Date(timestamp * 1000).toLocaleString()}`;
}
