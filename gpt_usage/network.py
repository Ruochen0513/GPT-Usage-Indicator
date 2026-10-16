"""Apply validated, purpose-specific GNOME proxy routes to Codex child processes."""
from __future__ import annotations
import re
from urllib.parse import urlsplit

ROUTE_KEYS = {'auth': 'GPT_USAGE_AUTH_PROXY', 'quota': 'GPT_USAGE_QUOTA_PROXY'}
PROXY_KEYS = ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy')


def proxy_url(value):
    if value == 'direct':
        return value
    if not isinstance(value, str) or any(c.isspace() or c == '\\' for c in value):
        raise ValueError('Invalid proxy URL')
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme in {'http', 'https', 'socks5', 'socks5h'} and parsed.hostname
                 and parsed.username is None and parsed.password is None
                 and parsed.path in ('', '/') and not parsed.query and not parsed.fragment
                 and (parsed.port is None or 1 <= parsed.port <= 65535))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Invalid proxy URL; use HTTP, HTTPS or SOCKS5 without credentials')
    return value.rstrip('/')


def apply_proxy(env, purpose='quota'):
    key = ROUTE_KEYS[purpose]
    if key not in env:
        return env
    route = proxy_url(env[key])
    # A resolved/manual route is authoritative over stale inherited env/bypasses.
    for name in PROXY_KEYS:
        env.pop(name, None)
    if route != 'direct':
        for name in PROXY_KEYS:
            env[name] = route
    env['NO_PROXY'] = env['no_proxy'] = 'localhost,127.0.0.1,::1'
    return env


def service_error(value):
    """Classify known failures without reflecting arbitrary service response bodies."""
    if isinstance(value, dict):
        value = value.get('message')
    if not isinstance(value, str):
        return None
    text = value.lower()
    if 'unsupported_country_region_territory' not in text and 'country, region, or territory not supported' not in text:
        return None
    message = ('OpenAI rejected this request because its region is not supported. '
               'Check the sign-in proxy route and service availability; browser and background routes may differ.')
    request = re.search(r'\brequest id:\s*([a-f0-9]{16,64}-[A-Z]{3})\b', value, re.IGNORECASE)
    if request:
        message += ' Request id: ' + request.group(1)
    return 'unsupported_region', message
