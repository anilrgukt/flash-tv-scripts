#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REQUIRED_PACKAGES = ("PySide6", "pyqtgraph", "numpy", "pydantic")
VENV_NAME = "py312"


def print_step(message: str) -> None:
    print(f"[FLASH-TV launcher] {message}")


def show_message(title: str, message: str) -> None:
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
        return
    except Exception:
        pass

    sys.stderr.write(f"{title}\n{message}\n")


def gui_dir() -> Path:
    return Path(__file__).resolve().parent


def venv_python() -> Path:
    return Path.home() / VENV_NAME / "bin" / "python"


def import_check_code() -> str:
    package_imports = "\n".join(
        f"import {package_name}"
        for package_name in REQUIRED_PACKAGES
        if package_name != "PySide6"
    )
    return (
        package_imports
        + "\nfrom PySide6 import QtCore, QtWidgets\n"
        + "print('FLASH-TV GUI runtime is ready')\n"
    )


def readiness_error() -> str:
    setup_script = gui_dir() / "setup_environment.py"
    return (
        "The FLASH-TV GUI is not ready yet.\n\n"
        + f"Expected environment: {Path.home() / VENV_NAME}\n"
        + f"Required packages: {', '.join(REQUIRED_PACKAGES)}\n\n"
        + "To fix this, run the GUI setup tool again:\n"
        + f"python3 {setup_script}"
    )


def ensure_runtime_ready() -> Path:
    python_path = venv_python()
    if not python_path.exists():
        raise RuntimeError(readiness_error())

    try:
        subprocess.run(
            [str(python_path), "-c", import_check_code()],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(readiness_error()) from exc

    return python_path


def main() -> int:
    main_py = gui_dir() / "main.py"
    python_path = ensure_runtime_ready()
    print_step("Runtime check passed. Starting the setup wizard.")
    os.execv(str(python_path), [str(python_path), str(main_py)])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        message = str(exc)
        print_step(message)
        show_message("FLASH-TV Setup Launcher", message)
        raise SystemExit(1)
