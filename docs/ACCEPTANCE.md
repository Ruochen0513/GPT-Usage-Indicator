# Target-machine acceptance checklist

The following are manual acceptance steps, not claims of completed tests.
Use your own account only after reviewing the data directory. Native GUI and
account login were not accessible during the implementation environment.

## GNOME (each declared Shell version)

1. Build the ZIP, install, log out/in, enable. Set the project `.runtime` absolute path.
2. Add/login a profile through the CLI and verify its email in the menu.
3. Compare both quota percentages against the account's Codex usage view.
4. Confirm the indicator is on the left. Try text, rings, bars and combined.
5. Toggle remaining/used; values must add to 100 when known. Missing windows stay unknown.
6. Create a second profile and switch accounts while a refresh is in progress.
   The first account's response must never replace the second account's view.
7. Disconnect network, refresh, reconnect. Error must be visible; Refresh recovers.
8. Disable/re-enable during refresh. Check that helper and app-server processes exit.
9. Test preferences Apply buttons, refresh interval, absolute executable paths,
   100%/200% scaling, light/dark Shell themes, keyboard menu access and screen reader label.
10. Test a reset passing: old quota disappears until a new server response arrives.

## Windows / macOS

1. Start source launcher with Python/Tk. Repeat with native build on each OS.
2. Add two profiles, login from terminal; switch while fetching and compare live quota.
3. Resize and drag window, change all views and used/remaining.
4. Change topmost/opacity/refresh settings; restart and verify persistence.
5. Move the saved window off screen or unplug a monitor; restart must recover a reachable position.
6. Close during refresh; no helper process should remain. Retry after a network failure.
7. On Windows test PATH with npm Codex, and explicit `codex.exe` paths with spaces.
8. On macOS test Intel/Apple Silicon builds separately, `.command`, `.app`, and shared runtime
   beside the `.app` and console executable. Review unsigned-app prompts as appropriate.
9. Confirm all data is in the chosen directory and never included in output archives.

## Automated CI

Run the provided workflow after pushing to your own repository. Confirm the native
GUI test actually ran rather than skipped, and inspect/download all three build artifacts.
Shell integration still requires the GNOME manual steps above; Xvfb is only for Tk.
