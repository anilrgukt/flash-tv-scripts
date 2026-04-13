#!/usr/bin/env bash
set -euo pipefail

python_runner="$(command -v python3 || command -v python3.12 || true)"

if [[ -z "$python_runner" ]]; then
    printf 'FLASH-TV GUI setup needs a system Python to start setup_environment.py. Install python3, then rerun this bootstrap so the helper can prepare Python 3.12.\n' >&2
    exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$python_runner" "$script_dir/setup_environment.py" "$@"
