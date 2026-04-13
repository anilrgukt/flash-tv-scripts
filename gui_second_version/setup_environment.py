#!/usr/bin/env python3

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_PACKAGES = ("PySide6", "pyqtgraph", "numpy", "pydantic")
VENV_NAME = "py312"
REQUIRED_APT_PACKAGES = (
    "python3.12",
    "python3.12-dev",
    "python3.12-venv",
    "python3-pip",
)


def print_step(message: str) -> None:
    print(f"[FLASH-TV setup] {message}")


def run_command(
    command: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, text=True)


def command_output(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def repo_paths() -> tuple[Path, Path]:
    gui_dir = Path(__file__).resolve().parent
    repo_root = gui_dir.parent
    main_py = gui_dir / "main.py"
    launch_gui_py = gui_dir / "launch_gui.py"

    if not main_py.exists():
        raise FileNotFoundError(f"Expected GUI entrypoint was not found: {main_py}")
    if not launch_gui_py.exists():
        raise FileNotFoundError(f"Expected launcher helper was not found: {launch_gui_py}")

    return gui_dir, repo_root


def check_platform() -> None:
    print_step(f"Running on {platform.system()} {platform.release()}.")
    if os.name != "posix":
        raise RuntimeError(
            "This setup helper currently supports Linux-style desktop setup only."
        )


def python_version(executable: str | Path) -> tuple[int, int] | None:
    output = command_output(
        [
            str(executable),
            "-c",
            "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
        ]
    )
    if not output:
        return None
    try:
        major_text, minor_text = output.split(".", 1)
        return int(major_text), int(minor_text)
    except ValueError:
        return None


def python312_supports_venv(executable: str | Path) -> bool:
    try:
        result = subprocess.run(
            [str(executable), "-m", "venv", "--help"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return result.returncode == 0


def find_python312() -> str | None:
    current_version = sys.version_info[:2]
    if current_version == (3, 12):
        return sys.executable

    for candidate in ("python3.12", "python3"):
        executable = shutil.which(candidate)
        if not executable:
            continue
        if python_version(executable) == (3, 12) and python312_supports_venv(
            executable
        ):
            return executable

    return None


def try_install_python312() -> str | None:
    apt_get = shutil.which("apt-get")
    if apt_get is None:
        print_step("Python 3.12 is missing and apt-get is not available here.")
        return None

    sudo = shutil.which("sudo")
    prefix: list[str] = []
    if os.geteuid() != 0:
        if sudo is None:
            print_step(
                "Python 3.12 is missing and sudo is not available for installation."
            )
            return None
        prefix = [sudo]

    print_step(
        "Python 3.12 was not found. Trying the Ubuntu/deadsnakes apt path for Python 3.12 setup."
    )

    commands = [
        prefix + [apt_get, "install", "-y", "software-properties-common"],
        prefix + ["add-apt-repository", "-y", "ppa:deadsnakes/ppa"],
        prefix + [apt_get, "update"],
        prefix
        + [
            apt_get,
            "install",
            "-y",
            *REQUIRED_APT_PACKAGES,
        ],
    ]

    for command in commands:
        try:
            _ = run_command(command)
        except (OSError, subprocess.CalledProcessError):
            print_step(
                "Automatic Python 3.12 installation did not complete. "
                + "Please ensure the deadsnakes PPA is available and install "
                + ", ".join(REQUIRED_APT_PACKAGES)
                + ", then run this tool again."
            )
            return None

    return find_python312()


def ensure_python312() -> str:
    executable = find_python312()
    if executable:
        print_step(f"Using Python 3.12 with venv support: {executable}")
        return executable

    python312_binary = shutil.which("python3.12")
    if python312_binary and python_version(python312_binary) == (3, 12):
        print_step(
            "Python 3.12 is present, but its venv support is not ready. "
            + "Trying to install the missing Python 3.12 environment packages."
        )

    executable = try_install_python312()
    if executable:
        print_step(f"Python 3.12 environment is ready: {executable}")
        return executable

    raise RuntimeError(
        "Python 3.12 with venv support is required for the GUI setup environment and could not be prepared automatically."
    )


def ensure_venv(python312: str, venv_path: Path) -> Path:
    venv_python = venv_path / "bin" / "python"
    if venv_python.exists() and python_version(venv_python) == (3, 12):
        print_step(f"Reusing existing GUI virtual environment at {venv_path}.")
        return venv_python

    if venv_path.exists():
        raise RuntimeError(
            f"{venv_path} already exists but is not a usable Python 3.12 environment. "
            + "Please fix or remove that folder manually. ~/py38 was not touched."
        )

    print_step(f"Creating a new Python 3.12 virtual environment at {venv_path}.")
    try:
        _ = run_command([python312, "-m", "venv", str(venv_path)])
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            f"Failed to create the GUI virtual environment at {venv_path}."
        ) from exc

    return venv_python


def package_installed(venv_python: Path, package_name: str) -> bool:
    try:
        _ = subprocess.run(
            [str(venv_python), "-m", "pip", "show", package_name],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def ensure_package(venv_python: Path, package_name: str) -> None:
    if package_installed(venv_python, package_name):
        print_step(f"{package_name} is already installed in ~/py312.")
        return

    print_step(f"Installing {package_name} into ~/py312.")
    try:
        _ = run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
        _ = run_command([str(venv_python), "-m", "pip", "install", package_name])
    except (OSError, subprocess.CalledProcessError) as exc:
        if package_name == "PySide6":
            raise RuntimeError(
                "PySide6 could not be installed in ~/py312. "
                + "This usually means Python 3.12 wheels are not available for this device or OS yet. "
                + "Please use a PySide6-compatible platform or install a supported PySide6 build manually."
            ) from exc
        raise RuntimeError(f"Failed to install {package_name} in ~/py312.") from exc


def ensure_packages(venv_python: Path) -> None:
    for package_name in REQUIRED_PACKAGES:
        ensure_package(venv_python, package_name)


def validate_gui_imports(venv_python: Path) -> None:
    print_step("Validating GUI imports in ~/py312.")
    import_check = (
        "import numpy\n"
        "import pyqtgraph\n"
        "from PySide6 import QtCore, QtWidgets\n"
        "print('GUI import validation passed')\n"
    )
    try:
        _ = run_command([str(venv_python), "-c", import_check])
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "Installed GUI packages did not pass import validation for numpy, pyqtgraph, and PySide6.QtCore/PySide6.QtWidgets."
        ) from exc


def launcher_icon(gui_dir: Path) -> str:
    icon_path = gui_dir / "assets" / "flash_tv_icon.png"
    if icon_path.exists():
        return str(icon_path)
    return "utilities-system-monitor"


def desktop_entry_text(gui_dir: Path) -> str:
    launch_gui_py = gui_dir / "launch_gui.py"
    return "\n".join(
        [
            "[Desktop Entry]",
            "Version=1.0",
            "Type=Application",
            "Name=FLASH-TV Setup",
            "Comment=FLASH-TV System Setup Wizard",
            f"Exec=python3 {launch_gui_py}",
            f"Path={gui_dir}",
            f"Icon={launcher_icon(gui_dir)}",
            "Terminal=false",
            "Categories=Utility;System;",
            "StartupNotify=true",
            "",
        ]
    )


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    _ = path.write_text(content, encoding="utf-8")
    return True


def trust_desktop_file(desktop_file: Path) -> None:
    gio = shutil.which("gio")
    if gio is None:
        return
    _ = subprocess.run(
        [gio, "set", str(desktop_file), "metadata::trusted", "true"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def ensure_desktop_launcher(gui_dir: Path) -> None:
    home = Path.home()
    desktop_dir = home / "Desktop"
    applications_dir = home / ".local" / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    applications_dir.mkdir(parents=True, exist_ok=True)

    desktop_file = desktop_dir / "flash-tv-setup.desktop"
    application_file = applications_dir / "flash-tv-setup.desktop"
    content = desktop_entry_text(gui_dir)

    desktop_changed = write_if_changed(desktop_file, content)
    application_changed = write_if_changed(application_file, content)

    desktop_file.chmod(0o755)
    application_file.chmod(0o755)
    trust_desktop_file(desktop_file)
    trust_desktop_file(application_file)

    if desktop_changed or application_changed:
        print_step(f"Desktop launcher updated at {desktop_file}.")
    else:
        print_step(
            f"Desktop launcher already matches the current setup at {desktop_file}."
        )


def ensure_py38_untouched() -> None:
    py38_path = Path.home() / "py38"
    if py38_path.exists():
        print_step(f"Leaving the existing legacy environment untouched: {py38_path}")
    else:
        print_step("No ~/py38 environment was found. Nothing to preserve there.")


def main() -> int:
    gui_dir, _ = repo_paths()

    print_step("Starting FLASH-TV GUI environment setup.")
    check_platform()
    ensure_py38_untouched()

    python312 = ensure_python312()
    venv_path = Path.home() / VENV_NAME
    venv_python = ensure_venv(python312, venv_path)

    ensure_packages(venv_python)
    validate_gui_imports(venv_python)
    ensure_desktop_launcher(gui_dir)

    print_step("Setup finished successfully.")
    print_step(f"Launch the GUI with: {venv_python} {gui_dir / 'main.py'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print_step(str(exc))
        raise SystemExit(1)
