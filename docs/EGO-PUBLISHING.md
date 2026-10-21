# GNOME Extensions submission

[English README](../README.md) · [中文说明](../README.zh-CN.md)

The EGO edition is a submission candidate, not an approved listing. It targets
GNOME Shell 46 and uses UUID `gpt-usage@ruochen0513.github.io`. The original
`gpt-usage@local` complete package remains available for GitHub distribution.
Do not submit either of the large `gpt-usage-linux-*.shell-extension.zip` files.

## Install the separate companion

Download `gpt-usage-companion-linux-x64.tar.gz` from the project's release assets
(or use the locally generated file under `dist/release/`). ARM64 users need the
`linux-arm64` archive. Until the new release is published, these files are available
to the owner in its draft release. **Publish the companion downloads before
submitting to EGO**, so reviewers and users can install the dependency.

Extract the archive and, inside its extracted directory, run:

```bash
python3 -B install.py
```

There is no source checkout or build step. The companion needs GJS (`gjs`) and
Python 3.10+ on Linux. It includes the verified Codex runtime. Installation is
user-local, needs no root, and creates only:

- `$XDG_DATA_HOME/gpt-usage-companion/` (default `~/.local/share/…`)
- `$XDG_DATA_HOME/dbus-1/services/io.github.Ruochen0513.GptUsage.service`

The session bus starts it on demand. It exits after 60 seconds with no active
operations and does not add a system service or login autostart entry. Credentials
remain in the existing private `gpt-usage-indicator` data directory. Other local
applications in the same user session can access that user's bus; D-Bus is not an
isolation boundary against malicious software running as that same user.

## Test the candidate locally

Disable the original edition first to avoid duplicate indicators and queries:

```bash
gnome-extensions disable gpt-usage@local
```

Install the small candidate ZIP, compile its schema for local testing, then log out
and back in. EGO compiles schemas for its distributed packages; the submission ZIP
contains only the XML schema.

```bash
gnome-extensions install --force ./gpt-usage@ruochen0513.github.io.shell-extension.zip
glib-compile-schemas "${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/gpt-usage@ruochen0513.github.io/schemas"
```

After logging back in:

```bash
gnome-extensions enable gpt-usage@ruochen0513.github.io
gnome-extensions prefs gpt-usage@ruochen0513.github.io
```

Open Preferences → **Check connection**. Your existing profiles should appear if
you previously used the default data directory. For a proxy listener on port 7897,
choose **Manual proxy URL**, enter `http://127.0.0.1:7897`, and click **Apply**.
The EGO edition has a separate settings schema, so proxy and appearance settings
must be selected again. Account files are shared, without copying credentials.
If you previously used a custom data directory, keep using the full edition until
you deliberately migrate that directory; the EGO companion uses the standard one.

Before submission, manually verify on GNOME 46:

- Missing companion: preferences explains the dependency and offers its homepage.
- Installed companion: existing profiles load; adding a new profile works.
- Browser sign-in and device code sign-in use official HTTPS pages.
- Cancel, window close, and disabling the extension stop its pending operations.
- Sign out clears the selected account's quota; another profile is unaffected.
- All four presentations work, along with remaining / used and account switching.
- Manual proxy works; a failed route does not silently fall back to direct.
- The desktop remains responsive during slow queries and the indicator disappears
  cleanly when disabled.

These real-desktop checks are not established by the offline integration suite.
Do not add other `shell-version` values without testing those versions.

## Publish the listing

1. Review the source and confirm you can explain, debug, and maintain it. AI-assisted
   development does not transfer maintainership to an automated tool.
2. Make the companion archive publicly downloadable from the GitHub release and
   verify the README's installation link is accessible without owner permissions.
3. Log in to https://extensions.gnome.org/upload/ and upload only
   `gpt-usage@ruochen0513.github.io.shell-extension.zip` from `dist/ego/`.
4. Check the name, description, homepage, and compatible Shell version. The site
   controls its extension version; it is separate from the app's semantic version.
5. Follow the review discussion, fix requested issues, and upload a revised ZIP
   using the **same UUID**. Approval is a reviewer decision, not guaranteed by this
   build or self-review.

Suggested reviewer note:

> This extension is a GJS-only D-Bus client. It contains no bundled binary,
> Python module, downloader, or credential store. Authentication and quota queries
> are handled by the separately installed open-source GPT Usage companion, linked
> from the homepage. Authorization events are addressed only to the initiating
> session-bus caller. The companion is not part of this EGO submission.

Official references:

- https://gjs.guide/extensions/review-guidelines/review-guidelines.html
- https://gjs.guide/extensions/review-guidelines/best-practices.html
- https://gjs.guide/guides/gio/dbus.html

## Build and remove

Maintainer builds:

```bash
python3 -B scripts/package_ego.py
python3 -B scripts/fetch_codex.py --target linux-x64
python3 -B scripts/package_companion.py --target linux-x64
```

The submission ZIP is architecture-independent. Build a separate companion archive
for each Linux architecture. Future release builds produce both alongside the
existing complete packages and desktop apps.

To remove the companion, finish any active operation and run `python3 -B install.py
--remove` from the extracted archive. It removes the program and activation file,
while preserving account data. Restart the desktop session after updating an
already active companion. Uninstall the EGO extension normally with
`gnome-extensions uninstall gpt-usage@ruochen0513.github.io`.
