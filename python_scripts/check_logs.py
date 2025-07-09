from __future__ import annotations

import os
import sys
from pathlib import Path


def read_errlog(log_path: Path | str) -> None:
    # Open the log file and read all lines
    with Path(log_path).open() as fid:
        lines = fid.readlines()

    lines = [line for line in lines if not line.strip("\n").startswith("can't get")]

    error_lines = []
    for line in lines:
        # Skip lines containing "Warning", "warn", or "Deprecated"
        if ("Warning" in line) or ("warn" in line) or ("Deprecated" in line):
            continue
        error_lines.append(line)

    if len(error_lines) > 8:
        print(f"Check the error log for potential errors:\n{log_path}")


def main() -> None:
    participant_id = sys.argv[1]
    user_home = Path.home()
    path = user_home / "data" / f"{participant_id}_data"
    ext = "_flash_logstderr.log"

    read_errlog(path / f"{participant_id}{ext}")

    path_logs = path / "logs"
    log_dir_list = sorted(next(os.walk(path_logs))[1])

    for dir_name in log_dir_list:
        print(f"Checking the log file: {dir_name}")
        log_path = path_logs / dir_name / f"{participant_id}{ext}"
        read_errlog(log_path)


if __name__ == "__main__":
    main()
