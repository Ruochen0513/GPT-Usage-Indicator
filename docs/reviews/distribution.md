# Direct-install distribution review — 2026-10-16

## Requested outcome

End users install a GNOME ZIP or run a Windows EXE/macOS app, and create/sign in
to an account in Settings. Source checkout and compilation are maintenance tasks.

## Implemented

- Official managed browser and device-code authorization with public JSONL events.
  GNOME Preferences adds/selects profiles, opens the authorization page, shows device
  codes, cancels and logs out. Desktop first launch opens account setup and uses the
  same authorization backend without a terminal.
- Login completion is buffered if it arrives before the start-request response.
  Only the matching login id is accepted; account email is checked after authorization.
  An unexpected account is signed out. Raw server diagnostics/tokens are not emitted.
- Browser URLs are restricted to official OpenAI HTTPS hosts. Browser launch fails
  gracefully with a reusable authorization link. Closing settings cancels login.
- Profile operations use an OS-released, per-account exclusive lock so an in-flight
  periodic query cannot publish old credentials' quotas after login/logout. Refresh
  pauses during authorization; cancellation and exceptions release the locks.
- User data survives plugin/application updates. Frozen apps use the platform user
  data directory rather than writing beside the executable or inside the .app.
- Full GNOME archives and native PyInstaller builds include a verified official
  Codex runtime. Upstream 0.163.0 is pinned. SHA-512 package integrity and the native
  SHA-256 are checked; LICENSE, NOTICE and provenance accompany redistribution.
- Release workflow builds GNOME x64/ARM64, Windows x64, macOS ARM64/Intel, with raw
  EXE / installable extension ZIP / application ZIP plus checksums. Version tags
  create a reviewable draft release. No public release is published automatically.

## Local evidence

- Python suite: 34 tests, 33 passed, 1 Tk GUI test skipped (DISPLAY not connectable).
- Node display and authorization-event validation: passed.
- GJS display runtime: passed.
- GJS extension/preferences syntax and strict schema compilation: passed.
- Bundled official Linux runtime executed `--version`: codex-cli 0.163.0.
- Full x64 GNOME ZIP built (about 107 MiB), with runtime, authorization UI, backend,
  compiled schema and upstream notices. Installation/real login remains a manual check.
- Package digest validation rejects modified bytes; untrusted download hosts rejected.
- Original project boundary retained for local development outputs; no host extension
  installation, global credentials inspection, or real account authorization was done.

## Remote build results

Uploaded reviewed code to the user-specified repository using its existing SSH
access. The first `v0.2.0` tag points to commit `411b6e4`.

- [Native checks on main](https://github.com/Ruochen0513/GPT-Usage-Indicator/actions/runs/38865428356): success (1m 4s).
- [Native checks on v0.2.0](https://github.com/Ruochen0513/GPT-Usage-Indicator/actions/runs/38865428526): success (1m 0s).
- [Downloadable application build](https://github.com/Ruochen0513/GPT-Usage-Indicator/actions/runs/38865428494): success (3m 24s).

The release build completed all five platform jobs and its draft-release job.
Verified artifact names on the public build summary:

| Artifact | Reported size | User application inside |
| --- | --- | --- |
| release-win32-x64 | 118 MB | GPT-Usage-windows-x64.exe |
| release-darwin-arm64 | 105 MB | GPT-Usage-macos-arm64.zip |
| release-darwin-x64 | 114 MB | GPT-Usage-macos-x64.zip |
| release-linux-x64 | 107 MB | gpt-usage-linux-x64.shell-extension.zip |
| release-linux-arm64 | 100 MB | gpt-usage-linux-arm64.shell-extension.zip |

The workflow created a `v0.2.0` draft with direct downloadable application assets,
upstream redistribution notices and per-file checksums. It remains a draft for
maintainer review; it was not publicly published. Owners can access it on the
[repository Releases page](https://github.com/Ruochen0513/GPT-Usage-Indicator/releases).
The Actions run also retains the five artifact downloads.

A native build succeeding does not prove interactive OAuth or every OS UI behavior.
No real ChatGPT account was used in these automated tests.

## Remaining target checks

GNOME Shell loading and the actual OAuth browser callback/device-code ceremony require
a real graphical desktop and the user's account. macOS output is unsigned/unnotarized;
Windows output is unsigned. OS trust prompts, visual placement and native window
behavior still need manual acceptance even when builds and smoke tests pass.
