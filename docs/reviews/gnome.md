# GNOME stage self-review

Date: 2026-10-15. Conducted before desktop implementation.

## Findings fixed

1. Helper termination originally bypassed Python cleanup and could orphan the
   app-server when disabling the extension. The CLI now unwinds on SIGTERM;
   AppServer context cleanup terminates/waits for its child.
2. A present but empty multi-bucket response could fall back to the legacy bucket
   and show the wrong allowance. An explicit multi-bucket map is now authoritative,
   including when empty; a regression test covers this.
3. Syntactically valid JSON containing `null` or an array could break menu loading.
   Extension reads now require an object before use.

## Checks and evidence

- Backend unit/protocol tests: missing data, unsupported durations, bucket selection,
  percent clamping, identity validation, isolation, transport timeout and process exit.
- Node presentation tests: account mismatch, stale/expired data, used/remaining, colors.
- `glib-compile-schemas --strict`: passes during extension build.
- JS syntax checks: extension and preferences pass.
- ZIP integration test: bundled backend runs, required schema exists, credentials excluded.
- Source lifecycle review: timer and settings signals removed, stale async callbacks ignored,
  at most one refresh per active configuration, Cairo contexts disposed.

## Limits

GNOME 46–50 are compatibility targets. A live Shell session has not been enabled or
modified: installing an extension would write outside the two authorized project
directories. Nested/live Shell activation, fractional-scale panel visuals and
preferences require manual validation on the target desktop. No actual account
credentials were read and no real quota request was made in this development run.
