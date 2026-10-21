import {validAccount} from './ui.js';
import {proxyRoute} from './network.js';

export const BUS_NAME = 'io.github.Ruochen0513.GptUsage';
export const OBJECT_PATH = '/io/github/Ruochen0513/GptUsage';
export const INTERFACE_XML = `<node>
<interface name="${BUS_NAME}">
  <method name="Read"><arg name="account" type="s" direction="in"/><arg name="state" type="s" direction="out"/></method>
  <method name="Start"><arg name="id" type="s" direction="in"/><arg name="request" type="s" direction="in"/></method>
  <method name="Cancel"><arg name="id" type="s" direction="in"/></method>
  <signal name="Event"><arg name="id" type="s"/><arg name="event" type="s"/></signal>
</interface>
</node>`;

export function requestArguments(json) {
    if (typeof json !== 'string' || json.length > 8192) throw new Error('Request is too large');
    const value = JSON.parse(json);
    if (!value || !validAccount(value.account)) throw new Error('Invalid account');
    const {action, account} = value;
    let argv;
    if (action === 'add') {
        if (typeof value.label !== 'string' || value.label.length > 100 || typeof value.email !== 'string' || value.email.length > 254)
            throw new Error('Invalid profile fields');
        argv = ['account', 'add', account, '--label', value.label || account, '--email', value.email];
    } else if (action === 'login') {
        if (typeof value.device !== 'boolean') throw new Error('Invalid login mode');
        argv = ['login', '--account', account, '--gui', ...(value.device ? ['--device-auth'] : [])];
    } else if (action === 'refresh' || action === 'logout') {
        argv = [action, '--account', account];
    } else {
        throw new Error('Unknown operation');
    }
    // Only route overrides are accepted; callers cannot supply paths or commands.
    const env = {};
    for (const key of ['GPT_USAGE_AUTH_PROXY', 'GPT_USAGE_QUOTA_PROXY']) {
        if (value.env?.[key] !== undefined) {
            env[key] = value.env[key] === 'direct' ? 'direct' : proxyRoute(value.env[key]);
        }
    }
    return {action, account, argv, env};
}
