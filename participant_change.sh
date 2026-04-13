#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
REQUIRED_PYTHON="${HOME}/py312/bin/python"

if [ ! -x "${REQUIRED_PYTHON}" ]; then
    printf '%s\n' "FLASH participant change requires the managed Python 3.12 environment at ${REQUIRED_PYTHON}." >&2
    printf '%s\n' "Recovery: run ${SCRIPT_DIR}/gui_second_version/bootstrap.sh, let it finish, then rerun ./participant_change.sh." >&2
    printf '%s\n' "This script will not fall back to ~/py38 or system python3 because that can hide missing dependencies." >&2
    exit 1
fi

if ! "${REQUIRED_PYTHON}" -c 'import pydantic' >/dev/null 2>&1; then
    printf '%s\n' "FLASH participant change could not import the required Python dependency 'pydantic' from ${REQUIRED_PYTHON}." >&2
    printf '%s\n' "Recovery: rerun ${SCRIPT_DIR}/gui_second_version/bootstrap.sh so the managed GUI environment can repair ~/py312, then rerun ./participant_change.sh." >&2
    exit 1
fi

exec "${REQUIRED_PYTHON}" "${SCRIPT_DIR}/python_scripts/participant_manager.py" "$@"
