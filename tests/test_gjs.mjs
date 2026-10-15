import {view, validAccount, resetText} from '../gnome-extension/gpt-usage@local/ui.mjs';
function check(value, message) { if (!value) throw new Error(message); }
const sample = {schema_version: 1, account_id: 'personal', status: 'ok', updated_at: 100,
    windows: {five_hour: {remaining_percent: 75, used_percent: 25, resets_at: 300}}};
check(view(sample, 'personal', true, 200).values[0] === 75, 'remaining quota');
check(view(sample, 'work', true, 200).values[0] === null, 'account isolation');
check(view(sample, 'personal', true, 300).values[0] === null, 'reset expiry');
check(!validAccount('../other'), 'path traversal');
check(resetText(null) === 'Reset time unavailable', 'unknown reset');
print('GJS presentation runtime checks passed');
