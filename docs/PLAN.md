# Implementation contract

- Reference: Agent Status Indicator (local reference project), architecture inspiration only.
- Scope: Codex ChatGPT subscription quotas, not ChatGPT web model message limits or API billing.
- Provider: official Codex app-server JSONL protocol; no private HTTP endpoints or token extraction.
- Account isolation: each profile owns a CODEX_HOME; explicit ChatGPT login, optional expected email.
- No model turns are started to read quotas.
- Both clients share one validated, versioned snapshot. Unknown data never becomes 0% used.
- GNOME: left panel, text/rings/bars/combined, preferences, refresh and account switching.
- Desktop: Windows/macOS/Linux Tk small window, same views, movable and optional always on top.
- Development/test outputs remain inside this checkout. Do not install into host directories.
- Commit each feature/fix; review GNOME before implementing desktop; final review and README.
