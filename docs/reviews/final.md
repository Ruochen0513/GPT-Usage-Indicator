# Final self-review

Date: 2026-10-15. The GNOME implementation was reviewed and committed before the
Windows/macOS desktop implementation (see `gnome.md` and Git history).

## Result

Implementation and local non-GUI checks are complete. No known blocking issue was
found in the exercised paths. Native GUI acceptance and real-account integration
are still unverified; this report does not claim a production-ready release.

## Review findings and fixes

- Profile isolation must include the Codex credential backend, not just CODEX_HOME.
  Login and app-server explicitly select file credential storage so system keyring
  credentials cannot silently merge profiles. API-key environment overrides are removed.
- Account email is validated before and after fetching quotas. An identity change
  discards the result and clears prior display data. A regression exercises this.
- Empty multi-bucket maps are authoritative and never fall back to an unrelated
  legacy bucket. Only 300-minute and 10080-minute windows map to the two displays.
- Malformed numbers (including enormous integers, NaN, infinity, booleans) do not
  become plausible quotas. Unknown, stale and expired readings remain unknown.
- Initial SIGTERM integration testing exposed a timing-dependent child leak while
  AppServer.__enter__ was initializing. Cleanup now covers SystemExit/KeyboardInterrupt
  throughout acquisition, with a deterministic regression. The real CLI SIGTERM
  test was repeated 30 times after the fix, all passing.
- GUI worker cancellation is polled every 200 ms; process exit is bounded and reaped.
  The desktop waits for its non-daemon worker before closing; stale generations
  cannot update the selected account. An unexpected worker exception still posts a
  result so Tk cannot remain stuck waiting for a dead worker.
- Windows npm shims resolve to a known native executable layout without shell=True.
  An explicit native executable remains available for other installation layouts.
- Frozen macOS builds store runtime beside the .app, not inside the application bundle.
- JSON writes use unique temporary files, restrictive POSIX permissions and atomic replace.
  Extension file reads are size-bounded and reject non-object JSON.
- Package manifests exclude runtime, credentials and Python bytecode. The extension
  ZIP contains its own runnable backend and compiled GSettings schema.

## Local validation

| Check | Observed result |
| --- | --- |
| Python unittest discovery | 19 tests: 18 passed, 1 GUI test skipped |
| CLI termination integration repeated after race fix | 30 / 30 passed |
| Node presentation tests | Passed |
| GJS presentation runtime tests | Passed |
| Extension and preferences JS syntax | Passed |
| Strict GSettings compilation | Passed |
| Bash launcher syntax | Passed |
| Source CLI --help | Passed |
| GNOME ZIP build and bundled backend CLI | Passed |
| Desktop portable ZIP build | Passed |
| Archive privacy/required-file inspection | Passed |
| git diff --check | Passed |

The Python suite covers identity mismatch, account switches during refresh, private
storage, profile path validation, quota semantics, stale/reset behavior, JSONL
initialization, ignored notifications, diagnostic redaction, request timeouts,
cancellation, child reaping, native Windows discovery, preference validation and packaging.
Tests create private directories only under this checkout's `.runtime/tests`.

## Unverified and remaining limits

- DISPLAY=:0 is present but not connectable; the actual Tk window smoke test reports
  an explicit skip. Visual layout, native topmost/opacity behavior and dragging need
  target-machine validation.
- No live GNOME extension was installed or enabled. GNOME 46–50 are compatibility
  targets, not tested version certifications. Shell lifecycle was reviewed in source.
- Windows/macOS native builds and the provided CI workflow were not executed locally.
  The deliverable is source plus a portable source ZIP, a GNOME ZIP and build workflows,
  not signed or notarized Windows/macOS binaries.
- No real credentials were read and no real quota request or login was performed.
  Account login is a required user setup step, described in README.
- Account configuration edits are not transactionally locked across multiple editors;
  account creation/config editing should be performed from one client at a time.
- Exact backend availability and quota windows depend on Codex CLI and the account.
  If the official service does not expose a seven-day window, the UI reports unknown.

Only the requested new project and the supplied reference repository were accessed
as project files; all created/modified files are in the new project. The reference
repository was not changed. Host configuration, installed extensions and global
credentials were not inspected or modified.

See `docs/ACCEPTANCE.md` for the remaining manual target-machine checks.
