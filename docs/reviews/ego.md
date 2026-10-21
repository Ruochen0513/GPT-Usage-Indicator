# EGO submission candidate self-review — 2026-10-21

## Scope and policy

This is a separate publication edition, not an EGO-approved release. The existing
GitHub complete packages and desktop clients are retained. The candidate UUID is
`gpt-usage@ruochen0513.github.io`; it targets GNOME Shell 46, matching the local
Shell version. Real Shell-session acceptance and real-account login for this
edition remain manual checks, not inferred from the tests below.

Reviewed against:

- https://gjs.guide/extensions/review-guidelines/review-guidelines.html
- https://gjs.guide/extensions/review-guidelines/best-practices.html

The EGO archive contains no Codex binary, Python module, downloader, install
script, compiled schema, credential data, or unnecessary build files. It includes
metadata with a public source URL and an OSI/GPL-compatible MIT license. No claim
is made that these checks guarantee approval. The maintainer must understand,
review, and maintain the submitted JavaScript.

## Implementation review

- The Shell edition reads state asynchronously through session D-Bus rather than
  doing synchronous disk reads or spawning Python in the Shell process.
- Shell-only graph imports are separate from shared D-Bus, proxy, and presentation
  modules. The preferences process imports Gtk/Adw only in its own entry point.
- `enable()` acquires resources; `disable()` removes the poll timer, disconnects
  settings, cancels route lookups and its D-Bus jobs, then destroys the panel UI.
- Results from an old refresh session are checked before assignment, preventing
  a canceled account switch from restoring another account's cached state.
- The companion accepts only four fixed operations with validated profile IDs.
  Requests cannot choose executable paths, data paths, or arbitrary commands.
- Proxy overrides are allowlisted and validated independently for authentication
  and quota. They cannot carry embedded credentials or leak between jobs.
- Authorization URLs are checked against the official HTTPS host allowlist before
  transmission and again before display/opening by preferences.
- Authorization events are unicast to the initiating unique bus name. Cancel
  checks the caller's ownership. Caller disappearance terminates its helper.
- Operations are bounded by timeouts, limited globally and per account, and retain
  the backend's existing per-account OS locks. Profile additions are serialized
  to avoid concurrent read/modify/write loss in the shared config file.
- The independent service handles shutdown and waits for helper cleanup; it exits
  after 60 idle seconds. A missing companion produces an installation link and
  usable settings, without silently downloading or installing anything.
- The installer writes only the selected user's data-home and D-Bus activation
  directory. Uninstall preserves the separate account directory. We exercised it
  under a project-local staging prefix, never against the real user installation.

## Evidence

- Real isolated D-Bus tests use the actual GJS client and service with a fake CLI:
  profile creation, state refresh, independent proxy routes, cleared overrides,
  operation/path rejection, private events, explicit cancellation, unauthorized
  cancellation rejection, caller-disconnect cleanup, and invalid URL rejection.
- A second isolated-bus test installs to a path containing spaces, exercises actual
  D-Bus activation from the installed `.service` file, and uninstalls while keeping
  the simulated account data.
- Artifact test builds the actual upload ZIP and checks its metadata, source-only
  file contents, import closure, absence of subprocess/disk-read calls, and size.
- Node syntax checks run on every JavaScript module during packaging; the XML
  schema passes strict GLib compilation validation.
- Full regression suite: **44 tests passed**, including the existing quota,
  account, authentication, distribution, desktop-window, and proxy tests.
- Node presentation/authentication/proxy checks and both existing GJS checks pass.
- English/Chinese README command blocks match; local document links and Markdown
  fences pass validation. The candidate ZIP is 13,424 bytes (16 KB allocated on disk).
- Local Linux x64 companion archive: checksum, runtime/licenses, current backend
  version, service source, and absence of account data verified. The portable
  source archive includes both READMEs, companion sources, and the publishing guide.
- [Main checks](https://github.com/Ruochen0513/GPT-Usage-Indicator/actions/runs/39577933337)
  passed on Linux, Windows, and macOS. The
  [v0.3.0 release build](https://github.com/Ruochen0513/GPT-Usage-Indicator/actions/runs/39578055603)
  passed all five native targets and created its draft release. The Linux artifacts
  include separate x64/ARM64 companion archives; the x64 artifact also carries the
  architecture-independent EGO candidate ZIP and checksums. This is not an EGO upload.

## Remaining release and manual steps

The maintainer must complete the real GNOME 46 checks in
[the publishing guide](../EGO-PUBLISHING.md), publish the separate companion
archives so reviewers can install them, and then submit the small ZIP using the
registered EGO account. The candidate is not uploaded automatically. Other GNOME
versions need their own validation before expanding `shell-version`.
