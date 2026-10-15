import assert from 'node:assert/strict';
import {view, color, resetText, validAccount} from '../gnome-extension/gpt-usage@local/ui.mjs';
const state = {schema_version: 1, account_id: 'work', status: 'ok', updated_at: 1000,
    windows: {five_hour: {remaining_percent: 75, used_percent: 25, resets_at: 1200}}};
assert.deepEqual(view(state, 'work', true, 1100).values, [75, null]);
assert.deepEqual(view(state, 'other', true, 1100).values, [null, null]);
assert.deepEqual(view(state, 'work', false, 1100).values, [25, null]);
assert.equal(view(state, 'work', true, 2000).status, 'stale');
assert.equal(view(state, 'work', true, 1200).values[0], null);
assert.equal(view({...state, status: 'error'}, 'work', true, 1100).values[0], null);
assert.match(resetText(100, 110), /awaiting refresh/);
assert.equal(validAccount('../private'), false);
assert.equal(validAccount('work-1'), true);
assert.deepEqual(color(10, true), color(90, false));
console.log('GNOME presentation checks passed');
