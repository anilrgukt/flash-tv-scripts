#!/usr/bin/env bash
set -euo pipefail

python_runner="$(command -v python3 || true)"

if [[ -z "$python_runner" ]]; then
    printf 'FLASH-TV Home Assistant bootstrap needs python3. Install python3, then rerun this script.\n' >&2
    exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$python_runner" "$script_dir/../python_scripts/install_orchestrator.py" homeassistant-bootstrap "$@"
