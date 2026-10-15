#!/usr/bin/env bash
# Portable source launch; neither installs globally nor changes login items.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 -B "$project_root/bin/run.py" "$@" desktop
