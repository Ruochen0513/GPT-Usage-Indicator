# GPT Usage Indicator

**English** | [简体中文](README.zh-CN.md)

Install the GNOME extension or open the Windows / macOS app, sign in to your ChatGPT account in Settings, and see your **Codex subscription usage limits for the 5-hour and 7-day windows**. No repository clone or compilation is needed for regular use.

Choose percentages, dual rings, progress bars, or rings with percentages. Features include remaining/used views, multiple accounts, automatic refresh, and reset times. The architecture was inspired by [Agent Status Indicator](https://github.com/Ruochen0513/agent-status-indicator); quota retrieval and the interface are implemented separately in this project.

![Feature illustration with sample values; not a live screenshot](docs/preview.svg)

## Download and install

Repository: [Ruochen0513/GPT-Usage-Indicator](https://github.com/Ruochen0513/GPT-Usage-Indicator). Choose the file for your platform from [Releases](https://github.com/Ruochen0513/GPT-Usage-Indicator/releases). The `v0.2.1` builds passed for all five targets and produced a draft release: the repository owner can download its attachments, and other users can download them once the release is published. Files are also available in the [build artifacts](https://github.com/Ruochen0513/GPT-Usage-Indicator/actions/runs/38867877878).

| Platform | Download | Python / Codex required? |
| --- | --- | --- |
| GNOME, Intel/AMD 64-bit | `gpt-usage-linux-x64.shell-extension.zip` | System Python 3.10+ required; Codex bundled |
| GNOME, ARM64 | `gpt-usage-linux-arm64.shell-extension.zip` | System Python 3.10+ required; Codex bundled |
| Windows x64 | `GPT-Usage-windows-x64.exe` | Both bundled |
| macOS Apple Silicon | `GPT-Usage-macos-arm64.zip` | Both bundled |
| macOS Intel | `GPT-Usage-macos-x64.zip` | Both bundled |

The complete GNOME package includes the official native Codex runtime, making it relatively large (about 107 MiB for x64). A smaller development package, `gpt-usage@local.shell-extension.zip`, requires a separately installed Codex executable. For regular use, choose a complete package from the table above.

### GNOME

Targets GNOME Shell 46–50. Download the ZIP for your architecture and run this command from your download directory:

```bash
gnome-extensions install --force ./gpt-usage-linux-x64.shell-extension.zip
```

For ARM64, use the corresponding filename. Log out and back in, enable **GPT Usage Indicator** in Extensions / Extension Manager, and open its preferences. You can also run:

```bash
gnome-extensions enable gpt-usage@local
gnome-extensions prefs gpt-usage@local
```

These commands install or manage the desktop extension. You do not need to download or build the source, and root access is not required.

Under **Accounts** in the extension preferences:

1. Enter a profile ID (for example, `personal`), a display name, and an optional expected email address, then click **Add account**.
2. Select the account and click **Sign in**. Complete authorization on the official page that opens in your browser.
3. Return to preferences. Once your signed-in email appears, the quota automatically updates on the left side of the top panel.

The default data directory and runtime are already configured; no source paths are needed. Use the panel menu to switch accounts, view reset times, refresh manually, or open preferences.

If the browser callback is unavailable, click **Device code** and enter the displayed code on the official page. Availability depends on your account or organization policy. Click **Cancel** or close preferences to cancel authorization. **Sign out** clears the profile's login and quota data.

### GNOME Extensions platform edition

A separate **submission candidate** is available for extensions.gnome.org. It has
not been approved or listed there. It targets **GNOME Shell 46** and uses UUID
`gpt-usage@ruochen0513.github.io`.

- **Extension:** `gpt-usage@ruochen0513.github.io.shell-extension.zip` (about 16 KB).
  Contains only GJS, metadata, styles, the XML schema, and the license.
- **Separate dependency:** `gpt-usage-companion-linux-x64.tar.gz` or
  `gpt-usage-companion-linux-arm64.tar.gz`. Download it from the release assets,
  extract it, and run the following from the extracted directory:

```bash
python3 -B install.py
```

The companion includes Codex and requires system GJS and Python 3.10+. It installs
without root, starts through session D-Bus on demand, and exits after 60 idle
seconds. The extension communicates over D-Bus and does not spawn commands or
read credential files. Account sign-in remains in Preferences. Existing profiles
in the standard data directory are shared with the full edition; proxy and
appearance settings are separate. Disable the original edition before enabling
this one to avoid duplicate indicators.

The small extension ZIP belongs to `dist/ego/`; companion archives are under
`dist/release/`. New release builds generate both. A draft release is visible only
to its owner until published: make the companion downloads public before an EGO
submission. See the [installation, local validation, and submission guide](docs/EGO-PUBLISHING.md).
The complete GNOME packages above remain available for installation from GitHub.

### GNOME system proxy and sign-in errors (v0.2.1)

The bundled Codex 0.163.0 runtime does not implement Linux system proxy resolution. A proxy configured in GNOME may therefore not reach its background process. The extension now uses GIO to resolve system proxy / PAC settings and explicitly passes the authentication and quota routes to their respective Codex processes.

Preferences → **Network proxy** offers three modes:

- **GNOME system proxy / PAC**: the default; resolves the system configuration. Resolution failures are reported without automatically falling back to a direct connection.
- **Manual proxy URL**: enter your proxy client's local HTTP / mixed listener, such as `http://127.0.0.1:7897`, and click **Apply** before signing in. For a SOCKS5 listener, use an address such as `socks5h://127.0.0.1:7897`. Do not include a username or password in the URL.
- **Inherited launch environment**: uses the launch environment without GNOME overrides, for users who already configure proxy environment variables.

**Check route** displays the routes configured for authentication and quota requests. It only checks configuration; it does not send a login request, detect your exit IP, or verify its region. Manual mode overrides inherited proxy variables and bypass lists in the background process while keeping localhost callbacks direct. It does not change system proxy or browser settings.

`Country, region, or territory not supported` indicates a server-side region rejection. The extension recognizes this error and retains a sanitized request ID. A proxy node labeled Singapore does not verify the exit location seen by the service. If you have confirmed that you are in a [supported region](https://help.openai.com/en/articles/7947663-chatgpt-supported-countries) and still receive this error, contact official support with the time and request ID.

### Windows

Download and double-click `GPT-Usage-windows-x64.exe`. It includes Python/Tk and the Codex runtime; no Python, Node.js, Codex installation, or terminal is needed.

Settings opens on first launch. Adding an account starts official browser authorization. For an existing account, click **Sign in** to sign in again, or use **Device code**. Settings also supports signing out and canceling authorization.

### macOS

Choose the ZIP for your processor, extract it, and open `gpt-usage-desktop.app`. Add an account and sign in under Settings on first launch. Runtime dependencies are bundled.

The current builds are not developer-signed or notarized; macOS may require confirmation of their source on first launch. The app supports always-on-top mode, opacity, dragging, and account / presentation switching.

## Controls

| Action | GNOME | Desktop window |
| --- | --- | --- |
| Switch accounts | Panel menu or preferences | Top dropdown |
| Switch presentation | Preferences → Presentation | Text / Rings / Bars / Combined |
| Remaining / used | Show remaining quota | Remaining / Used |
| Refresh manually | Menu → Refresh now | Refresh |
| Sign in / sign out / cancel | Preferences → Accounts | Settings |
| Position, always-on-top, opacity | Managed by the Shell panel | Drag the title area, or use Settings |
| Automatic refresh | Every 120 seconds by default; configurable from 30–3600 seconds | Same |

Browser authorization takes place only on official OpenAI HTTPS pages. This project does not receive your password. Authorization links and device codes are displayed only in the current settings session. After sign-in, the app checks the account email before refreshing quota. If an expected email is configured and a different account signs in, the app signs that account out of the profile and reports the mismatch.

Regular users do not need to change **Advanced** settings. These allow a custom data directory or Python / Codex executable. The default `codex` setting prefers the bundled runtime and falls back to PATH if none is available.

## What the quota means

The indicator displays **ChatGPT subscription limits** returned by Codex's `account/rateLimits/read`. These are not per-model message counts on the ChatGPT website, API credit balances, or API token billing.

- The 300-minute and 10,080-minute windows are identified by their server-provided durations, without assuming primary/secondary order.
- 25% used means 75% remaining; you can switch between the two views.
- An unavailable window displays `—`, rather than 0% used.
- Data older than `max(600, 2 × refresh interval + 120)` seconds is marked stale and its old values are hidden.
- At the reset time, the indicator waits for a new query rather than assuming the quota is full.
- Network, authentication, or identity-check failures clear old quota values and display the reason.
- Remaining quota above 25% is green, 10–25% is yellow, and 10% or less is red. Unknown values are gray.

Each profile has its own login directory. GNOME and desktop clients sharing a data directory serialize queries, sign-ins, and sign-outs for the same account so polling cannot interfere with authorization. Quota belongs to the ChatGPT account and is shared regardless of which client consumes it.

## Data, updates, and removal

| Edition | Default data directory |
| --- | --- |
| GNOME | `$XDG_DATA_HOME/gpt-usage-indicator`, defaulting to `~/.local/share/gpt-usage-indicator` |
| Windows EXE | `%LOCALAPPDATA%\gpt-usage-indicator` |
| macOS app | `~/Library/Application Support/gpt-usage-indicator` |
| Native Linux desktop app | `$XDG_DATA_HOME/gpt-usage-indicator` |
| Source development version | `.runtime/` inside the repository |

Updating the extension or replacing the EXE / `.app` preserves this data. Login data is stored separately from the executable, so placing the app in a protected directory does not prevent settings from being saved.

Data includes `accounts.json`, each profile's `codex-home`, token-free quota snapshots, and window preferences. Codex credentials use per-profile file storage rather than a shared system-keychain login. Private directories use `0700` and JSON files use `0600` on POSIX; Windows relies on the current user's directory ACLs.

Closing the window stops its background threads; disabling the extension terminates its query. There is no persistent system service, registry modification, global PATH change, or automatic startup entry. To remove the GNOME extension:

```bash
gnome-extensions disable gpt-usage@local
gnome-extensions uninstall gpt-usage@local
```

On Windows / macOS, close and delete the app. To remove account credentials, first use **Sign out** in Settings. To remove all configuration, delete the corresponding data directory from the table above. This project does not manage other Codex clients' configuration.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| GNOME extension does not appear | Check the Shell version and ZIP architecture; log out and back in after installation, then enable it |
| Sign in does not start | Complete packages include Codex; on GNOME, check for Python 3.10+ and set an absolute path under Advanced if needed |
| Browser does not open automatically | Click Open authorization page, or try Device code |
| Authorization times out or is canceled | Click Sign in again and close extra authorization pages |
| Email mismatch | Sign in with the expected email, or create another profile |
| Values always show `—` | Check sign-in and connectivity; the account may not provide those window durations |
| Only one window shows a number | The other window is unavailable; displaying it as unknown is expected |
| Old data disappears after an update | If you previously used the project's `.runtime` explicitly, set its absolute path under Advanced |
| Linux source version lacks Tkinter | Install Tcl/Tk matching your Python; the GNOME extension does not require Tk |

Complete releases use a pinned Codex version. If the official protocol changes, update the release; advanced users can temporarily select a newer external Codex binary. Quota queries do not start a model turn or read chat history. They do require connectivity to the official service.

## For maintainers: build and release

These steps are for maintainers. Regular users can download a ready-to-use package from the table above.

### Automated release builds

The [Build downloadable applications workflow](.github/workflows/release.yml) supports:

- GitHub Actions → **Build downloadable applications** → **Run workflow**: builds all five targets and provides downloadable artifacts.
- Pushing a `v*` tag: creates a **draft release** with downloadable attachments after the builds finish. A maintainer reviews and publishes it to make the files available through Releases.

The matrix covers Windows x64, macOS ARM64 / Intel, and GNOME x64 / ARM64. Windows EXEs and macOS `.app` bundles are built on runners for the corresponding operating systems, rather than assembled on Linux.

### Build a complete GNOME package locally

```bash
python3 -B scripts/fetch_codex.py --target linux-x64
python3 -B scripts/package_extension.py --target linux-x64
python3 -B scripts/package_release.py --target linux-x64
```

Use `linux-arm64` for ARM64. The build host does not need to run the packaged target binary. For the lightweight source extension, run only `scripts/package_extension.py`.

For the source-only EGO candidate and its separately distributed companion:

```bash
python3 -B scripts/package_ego.py
python3 -B scripts/package_companion.py --target linux-x64
```

The runtime comes from OpenAI's official native `@openai/codex` npm package, pinned to `0.163.0`. Downloads are checked against npm SHA-512 integrity metadata; the native file's SHA-256 is checked again before packaging. The matching LICENSE, NOTICE, and provenance manifest are included. Extraction is limited to explicitly selected native files, and archive installation scripts are not executed.

### Build Windows / macOS locally

Install Python/Tk and PyInstaller on the corresponding operating system. Choose `win32-x64`, `darwin-arm64`, or `darwin-x64` as the target.

```bash
python -m pip install --no-cache-dir 'pyinstaller>=6.11,<7'
python -B scripts/fetch_codex.py --target win32-x64
python -B scripts/build_desktop.py --bundle-codex
python -B scripts/package_release.py --target win32-x64
```

On macOS, substitute the appropriate target. Final files and SHA-256 checksums are written to `dist/release/`. These are application packages rather than source ZIPs: Windows produces one GUI EXE, and macOS uses `ditto` to preserve the `.app` bundle structure.

### Run from source and use the CLI

Development requires Python 3.10+. The Tk window also requires Tkinter, and a system Codex installation is needed if no runtime is bundled. The core runtime has no third-party Python dependencies.

```bash
python3 -B bin/run.py account add personal --label Personal --email you@example.com
python3 -B bin/run.py login --account personal
python3 -B bin/run.py refresh --account personal
python3 -B bin/run.py desktop
```

On Windows, use `py -3` or the included `.cmd` launcher. On macOS, use `bin/GPT-Usage.command`. Source-mode Settings also supports graphical authorization. Other commands:

| Command | Purpose |
| --- | --- |
| `account list` | List profiles without printing credentials |
| `login --account ID --gui [--device-auth]` | Emit safe authorization JSONL events for graphical clients |
| `logout --account ID` | Sign out and clear quota data |
| `show --account ID` | Read the snapshot |
| `--data-dir PATH --codex PATH` | Place before the subcommand to customize the data directory and runtime |

Independent profiles do not automatically import another Codex client's login; sign in once for each profile. Profile IDs accept 1–48 letters, digits, `_`, or `-`; directory traversal is rejected.

### Tests and self-review

```bash
python3 -B -m unittest discover -s tests -v
node tests/test_ui.mjs
gjs -m tests/test_gjs.mjs
gjs -m tests/test_proxy_gjs.mjs
node --input-type=module --check < gnome-extension/gpt-usage@local/extension.js
node --input-type=module --check < gnome-extension/gpt-usage@local/prefs.js
git diff --check
```

Mock tests write data only under `.runtime/tests` in the repository. They do not use real logins or query quota over the network. Tk tests explicitly skip when no display is available. The companion tests use a private session bus and a simulated helper, including installation, D-Bus activation, private authorization events, caller ownership, route isolation, and cancellation. Self-reviews: [GNOME stage](docs/reviews/gnome.md), [initial release](docs/reviews/final.md), [direct installation and graphical sign-in](docs/reviews/distribution.md), [GNOME proxy fix](docs/reviews/proxy.md), and [EGO edition](docs/reviews/ego.md). See the [acceptance checklist](docs/ACCEPTANCE.md) and [EGO guide](docs/EGO-PUBLISHING.md) for manual checks on target desktops. Successful builds do not establish that all real-account authorization and desktop interactions have been tested.

The source `.runtime`, `build`, and `dist` directories are excluded from Git. Releases include only selected programs, licenses, and verification information, without development account data. `scripts/package_desktop.py` separately creates a portable source ZIP for development use.

## References and license

- [Official App Server protocol](https://developers.openai.com/codex/app-server/): quota and managed browser / device authorization interfaces.
- [Official authentication documentation](https://developers.openai.com/codex/auth/).
- [GNOME extension API](https://gjs.guide/extensions/topics/extension.html) and [preferences](https://gjs.guide/extensions/development/preferences.html).
- [Reference project: Agent Status Indicator](https://github.com/Ruochen0513/agent-status-indicator). The reference repository was not modified.

This project is licensed under MIT ([LICENSE](LICENSE)). Bundled Codex is licensed under Apache-2.0, and complete packages include its upstream license and NOTICE. This is an unofficial project and is not an OpenAI product.
