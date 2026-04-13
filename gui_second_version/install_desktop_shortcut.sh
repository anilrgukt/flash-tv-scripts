#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
    printf 'FLASH-TV GUI setup requires python3 so it can refresh the desktop shortcut and launcher.\n' >&2
    exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'Running the FLASH-TV GUI setup tool. This refreshes the py312 environment checks and the desktop shortcut.\n'
exec python3 "$script_dir/setup_environment.py" "$@"
