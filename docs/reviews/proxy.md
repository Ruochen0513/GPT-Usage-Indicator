# GNOME proxy fix self-review — 2026-10-16

## Report and verified source cause

A user reported an OAuth token-exchange 403 for unsupported region while selecting
a Singapore node in a system proxy client. The reported local proxy port is 7897.
We did not inspect or change the user's system settings or verify its actual exit IP.

Upstream Codex 0.163.0 source has system-proxy resolvers for macOS/Windows, but its
Linux implementation returns ProxyResolutionUnavailable. The existing helper only
copied the launch environment, so GNOME's desktop proxy configuration was not
explicitly transferred to that process. This is a confirmed compatibility gap;
it does not establish the exact route taken by the user's failed request.

Sources:
- https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/http-client/src/outbound_proxy.rs
- https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/server.rs

## Change

- Resolve GNOME proxy/PAC using Gio.ProxyResolver for the authentication and quota
  destination URLs before spawning the Python helper. This is a routing lookup,
  not a geolocation or network reachability test.
- Add Manual proxy URL and inherited-environment modes. The suggested manual URL
  for an HTTP/mixed listener on the reported port is http://127.0.0.1:7897.
- Use the same subprocess launcher from Shell and Preferences. Pass validated,
  purpose-specific routes to the actual Codex children for login, logout and quota.
- Explicitly set upper/lowercase HTTP(S)/ALL_PROXY when a route is selected, clear
  stale inherited routes and bypass lists, and keep loopback callbacks bypassed.
  Inherited-environment mode preserves the original launch environment.
- A system direct route removes inherited proxy variables. Resolution errors and
  invalid manual URLs fail visibly; no automatic direct fallback is introduced.
- Timeout/cancel proxy lookups, cancel sibling lookups on failure, and ignore stale
  async results after reconfiguration/disable/close. Account creation requires no
  proxy lookup. Network controls are disabled during account operations.
- Classify the known region error without emitting raw response bodies or tokens.
  Only an allowlisted request-id format is retained for support.

## Evidence

- Python: 41 tests, 40 pass and 1 Tk test skipped (no accessible display).
- Node route/auth/display tests: pass.
- GJS async resolver test with injected resolver: pass, including separate routes,
  cancellation and redacted errors.
- Real Gio.SubprocessLauncher child and Python child environment tests: pass for
  the supplied local HTTP proxy address. These do not make network requests.
- JS syntax and strict schema compilation: pass during package creation.
- Full Linux x64 runtime remains pinned and checksum-verified.

## Limits and remaining checks

A real account login through the user's proxy is unverified. The resolver uses the
first system candidate for each primary destination; it does not implement proxy
failover or per-redirect PAC evaluation inside Codex's Linux HTTP stack. Use Manual
proxy when a PAC setup requires one consistent local client route. Proxy URL fields
intentionally reject embedded credentials and accept HTTP/HTTPS/SOCKS5(SOCKS5h).

The patch does not guarantee that a proxy provider's node label matches the egress
location or that an IP will be accepted by the service. Region decisions remain
server-side; repeated rejection from an actually supported location needs support
review with the request id. Do not infer geolocation from the request-id suffix alone.
