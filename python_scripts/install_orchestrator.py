#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.install_defaults_loader import load_install_defaults_module


install_defaults_module = load_install_defaults_module()
HOME_ASSISTANT_IMAGE = str(getattr(install_defaults_module, "HOME_ASSISTANT_IMAGE"))


LEGACY_VENV_NAME = "py38"
MXNET_REPO_URL = "https://github.com/apache/mxnet.git"
MXNET_BRANCH = "v1.6.x"
TORCH_WHEEL_URL = (
    "https://developer.download.nvidia.cn/compute/redist/jp/v51/pytorch/"
    "torch-1.14.0a0+44dac51c.nv23.01-cp38-cp38-linux_aarch64.whl"
)
COMMON_APT_PACKAGES = (
    "nvidia-jetpack",
    "screen",
    "htop",
    "cheese",
    "v4l-utils",
    "python3.8",
    "python3.8-venv",
    "python3-pip",
    "libxcb-xinerama0",
    "nano",
    "gimp",
    "libbluetooth-dev",
    "borgbackup",
    "build-essential",
    "git",
    "libopenblas-dev",
    "libopencv-dev",
    "python-numpy",
    "python3-testresources",
    "libatlas-base-dev",
    "ca-certificates",
    "curl",
)
VENV_PACKAGES = {
    "smbus2": None,
    "watchdog": None,
    "cryptography": None,
    "aiohttp": None,
    "numpy": "1.21.4",
    "scipy": "1.9.1",
    "protobuf": None,
    "torchvision": "0.14.1",
    "setuptools": None,
    "Cython": None,
    "packaging": None,
    "lazy_loader": None,
    "imageio": None,
    "scikit-image": None,
    "opencv-python": None,
    "tqdm": None,
}
OBSOLETE_DOCKER_PACKAGES = (
    "docker.io",
    "docker-doc",
    "docker-compose",
    "docker-compose-v2",
    "podman-docker",
    "containerd",
    "runc",
)
DOCKER_PACKAGES = (
    "docker-ce",
    "docker-ce-cli",
    "containerd.io",
    "docker-buildx-plugin",
    "docker-compose-plugin",
)


class InstallError(RuntimeError):
    pass


def print_step(message: str) -> None:
    print(f"[FLASH-TV install] {message}")


def print_skip(message: str) -> None:
    print(f"[FLASH-TV install] Skipping: {message}")


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=check,
        text=True,
        capture_output=capture_output,
    )


def command_output(command: list[str]) -> str | None:
    try:
        result = run_command(command, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def command_exists(command_name: str) -> bool:
    return shutil.which(command_name) is not None


def operator_username() -> str:
    sudo_user = os.environ.get("SUDO_USER", "").strip()
    if sudo_user:
        return sudo_user
    return Path.home().name


def operator_home() -> Path:
    username = operator_username()
    if username == Path.home().name:
        return Path.home()
    return Path("/home") / username


def sudo_prefix() -> list[str]:
    if os.geteuid() == 0:
        return []
    sudo = shutil.which("sudo")
    if sudo is None:
        raise InstallError(
            "This installer needs sudo for system package and Docker setup, but sudo is not available."
        )
    return [sudo]


def ensure_sudo_ready() -> None:
    prefix = sudo_prefix()
    if not prefix:
        return
    print_step("Checking sudo access for system setup steps.")
    run_command(prefix + ["-v"])


def require_linux() -> None:
    if os.name != "posix":
        raise InstallError(
            "This installer currently supports Linux-style systems only."
        )
    print_step(f"Running on {platform.system()} {platform.release()}.")


def apt_package_installed(package_name: str) -> bool:
    result = run_command(
        ["dpkg-query", "-W", "-f=${Status}", package_name],
        check=False,
        capture_output=True,
    )
    return "install ok installed" in result.stdout


def ensure_apt_packages(packages: tuple[str, ...]) -> None:
    missing_packages = [
        package for package in packages if not apt_package_installed(package)
    ]
    if not missing_packages:
        print_step("Required apt packages are already installed.")
        return

    print_step("Installing missing apt packages: " + ", ".join(missing_packages) + ".")
    prefix = sudo_prefix()
    run_command(prefix + ["apt-get", "update"])
    run_command(prefix + ["apt-get", "install", "-y", *missing_packages])


def remove_obsolete_apt_packages(packages: tuple[str, ...]) -> None:
    present_packages = [
        package for package in packages if apt_package_installed(package)
    ]
    if not present_packages:
        print_step("No obsolete Docker packages were found.")
        return

    print_step(
        "Removing obsolete Docker packages: " + ", ".join(present_packages) + "."
    )
    run_command(sudo_prefix() + ["apt-get", "remove", "-y", *present_packages])


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


def find_legacy_python() -> str:
    for candidate in ("python3.8", "python3"):
        executable = shutil.which(candidate)
        if executable is None:
            continue
        if python_version(executable) == (3, 8):
            return executable
    raise InstallError(
        "FLASH-TV machine bootstrap expects Python 3.8 for the legacy ~/py38 environment and NVIDIA PyTorch wheel."
    )


def ensure_legacy_venv() -> Path:
    home = operator_home()
    venv_path = home / LEGACY_VENV_NAME
    venv_python = venv_path / "bin" / "python"
    if venv_python.exists() and python_version(venv_python) == (3, 8):
        print_step(f"Reusing existing legacy environment at {venv_path}.")
        return venv_python

    if venv_path.exists():
        raise InstallError(
            f"{venv_path} already exists but is not a usable Python 3.8 environment. Fix or remove it, then rerun the installer."
        )

    python38 = find_legacy_python()
    print_step(f"Creating the legacy FLASH-TV environment at {venv_path}.")
    run_command([python38, "-m", "venv", str(venv_path)])
    return venv_python


def pip_version(venv_python: Path, package_name: str) -> str | None:
    result = run_command(
        [str(venv_python), "-m", "pip", "show", package_name],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
    return "installed"


def ensure_pip_package(
    venv_python: Path, package_name: str, version: str | None = None
) -> None:
    installed_version = pip_version(venv_python, package_name)
    if installed_version and (version is None or installed_version == version):
        if version:
            print_step(f"{package_name}=={version} is already installed in ~/py38.")
        else:
            print_step(f"{package_name} is already installed in ~/py38.")
        return

    target = f"{package_name}=={version}" if version else package_name
    print_step(f"Installing {target} in ~/py38.")
    run_command([str(venv_python), "-m", "pip", "install", target])


def ensure_venv_packages(venv_python: Path) -> None:
    print_step("Making sure pip is up to date in ~/py38.")
    run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    for package_name, version in VENV_PACKAGES.items():
        ensure_pip_package(venv_python, package_name, version)


def torch_installed(venv_python: Path) -> bool:
    result = run_command(
        [str(venv_python), "-c", "import torch; print(torch.__version__)"],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0 and "1.14.0" in result.stdout


def ensure_torch(venv_python: Path) -> None:
    if torch_installed(venv_python):
        print_step("The NVIDIA PyTorch build is already installed in ~/py38.")
        return

    print_step("Installing the NVIDIA PyTorch wheel in ~/py38.")
    run_command(
        [str(venv_python), "-m", "pip", "install", "--no-cache", TORCH_WHEEL_URL]
    )


def ensure_bashrc_exports(home: Path, mxnet_dir: Path) -> None:
    bashrc_path = home / ".bashrc"
    if not bashrc_path.exists():
        bashrc_path.touch()

    export_lines = [
        "export PATH=/usr/local/cuda/bin:${PATH}",
        f"export MXNET_HOME={mxnet_dir}/",
        "export PYTHONPATH=${MXNET_HOME}/python:${PYTHONPATH}",
    ]
    original_text = bashrc_path.read_text(encoding="utf-8")
    updated_text = original_text
    appended = False

    for line in export_lines:
        if line not in updated_text.splitlines():
            updated_text = (
                updated_text.rstrip() + ("\n" if updated_text else "") + line + "\n"
            )
            appended = True

    if appended:
        bashrc_path.write_text(updated_text, encoding="utf-8")
        print_step("Updated ~/.bashrc with the MXNet environment exports.")
    else:
        print_step("~/.bashrc already contains the MXNet environment exports.")


def ensure_git_checkout(target_dir: Path, *, repo_url: str, branch: str) -> None:
    if target_dir.exists():
        print_step(f"Reusing existing source tree at {target_dir}.")
        return

    print_step(f"Cloning {repo_url} into {target_dir}.")
    run_command(
        [
            "git",
            "clone",
            "--recursive",
            "-b",
            branch,
            repo_url,
            str(target_dir),
        ]
    )


def build_mxnet(venv_python: Path) -> None:
    home = operator_home()
    mxnet_dir = home / "mxnet"
    ensure_git_checkout(mxnet_dir, repo_url=MXNET_REPO_URL, branch=MXNET_BRANCH)
    ensure_bashrc_exports(home, mxnet_dir)

    config_source = REPO_ROOT / "install_scripts" / "mxnet_config.mk"
    config_target = mxnet_dir / "config.mk"
    if not config_target.exists() or config_target.read_text(
        encoding="utf-8"
    ) != config_source.read_text(encoding="utf-8"):
        shutil.copy2(config_source, config_target)
        print_step("Updated mxnet/config.mk from the repo template.")
    else:
        print_step("mxnet/config.mk already matches the repo template.")

    env = os.environ.copy()
    env["PATH"] = f"/usr/local/cuda/bin:{env.get('PATH', '')}"
    env["MXNET_HOME"] = f"{mxnet_dir}/"
    env["PYTHONPATH"] = f"{mxnet_dir / 'python'}:{env.get('PYTHONPATH', '')}"

    mxnet_import = run_command(
        [str(venv_python), "-c", "import mxnet; print(mxnet.__version__)"],
        env=env,
        check=False,
        capture_output=True,
    )
    if mxnet_import.returncode == 0:
        print_step("MXNet Python bindings are already available in ~/py38.")
        return

    jobs = str(max(1, os.cpu_count() or 1))
    print_step("Building MXNet and installing its Python bindings.")
    run_command(["make", f"-j{jobs}", "all"], cwd=mxnet_dir, env=env)
    run_command(
        [str(venv_python), "-m", "pip", "install", "-e", "."],
        cwd=mxnet_dir / "python",
        env=env,
    )


def ensure_insightface(venv_python: Path) -> None:
    insightface_dir = operator_home() / "insightface"
    python_package_dir = insightface_dir / "python-package"
    retinaface_dir = insightface_dir / "detection" / "RetinaFace"
    if not python_package_dir.exists():
        print_skip(
            f"InsightFace source was not found at {python_package_dir}. Place that checkout first if this device still needs the legacy runtime."
        )
        return

    insightface_import = run_command(
        [str(venv_python), "-c", "import insightface"],
        check=False,
        capture_output=True,
    )
    retinaface_built = retinaface_dir.exists() and any(
        artifact.is_file()
        for pattern in ("*.so", "*.pyd", "*.dylib")
        for artifact in retinaface_dir.rglob(pattern)
    )
    if insightface_import.returncode == 0 and retinaface_built:
        print_step("InsightFace is already installed in ~/py38 and RetinaFace helpers are already built.")
        return

    print_step("Installing InsightFace into ~/py38.")
    run_command([str(venv_python), "setup.py", "install"], cwd=python_package_dir)

    if retinaface_dir.exists():
        jobs = str(max(1, os.cpu_count() or 1))
        print_step("Building InsightFace RetinaFace helpers.")
        run_command(["make", f"-j{jobs}", "all"], cwd=retinaface_dir)
    else:
        print_skip(f"RetinaFace source was not found at {retinaface_dir}.")


def ensure_darknet_face_release() -> None:
    darknet_dir = operator_home() / "FLASH_TV" / "darknet_face_release"
    if not darknet_dir.exists():
        print_skip(
            f"darknet_face_release was not found at {darknet_dir}. Place that source tree first if this device still needs the legacy runtime."
        )
        return

    if any(
        artifact.exists()
        for artifact in (
            darknet_dir / "darknet",
            darknet_dir / "libdarknet.so",
            darknet_dir / "libdarknet.a",
        )
    ):
        print_step("darknet_face_release already has a built artifact.")
        return

    jobs = str(max(1, os.cpu_count() or 1))
    print_step("Building darknet_face_release.")
    run_command(["make", f"-j{jobs}", "all"], cwd=darknet_dir)


def machine_bootstrap() -> None:
    require_linux()
    ensure_sudo_ready()
    print_step(
        "Machine bootstrap handles the legacy FLASH-TV runtime environment only. GUI setup stays in gui_second_version/setup_environment.py."
    )
    ensure_apt_packages(COMMON_APT_PACKAGES)
    venv_python = ensure_legacy_venv()
    ensure_venv_packages(venv_python)
    ensure_torch(venv_python)
    build_mxnet(venv_python)
    ensure_insightface(venv_python)
    ensure_darknet_face_release()
    print_step(
        "Machine bootstrap finished. ~/py38 is ready for the legacy FLASH-TV runtime."
    )


def docker_repository_text() -> str:
    architecture = command_output(["dpkg", "--print-architecture"])
    if not architecture:
        raise InstallError(
            "Could not determine the dpkg architecture for Docker setup."
        )

    version_codename = None
    os_release = Path("/etc/os-release")
    if os_release.exists():
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if line.startswith("VERSION_CODENAME="):
                version_codename = line.split("=", 1)[1].strip().strip('"')
                break

    if not version_codename:
        raise InstallError(
            "Could not determine VERSION_CODENAME from /etc/os-release for Docker setup."
        )

    return (
        "deb [arch="
        + architecture
        + " signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu "
        + version_codename
        + " stable\n"
    )


def install_file_with_sudo(content: str, destination: Path, mode: int) -> None:
    prefix = sudo_prefix()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    try:
        run_command(
            prefix + ["install", "-m", oct(mode)[2:], str(temp_path), str(destination)]
        )
    finally:
        temp_path.unlink(missing_ok=True)


def ensure_docker_repository() -> None:
    prefix = sudo_prefix()
    run_command(prefix + ["install", "-m", "0755", "-d", "/etc/apt/keyrings"])

    docker_key = Path("/etc/apt/keyrings/docker.asc")
    if not docker_key.exists():
        print_step("Installing Docker's apt signing key.")
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            run_command(
                [
                    "curl",
                    "-fsSL",
                    "https://download.docker.com/linux/ubuntu/gpg",
                    "-o",
                    str(temp_path),
                ]
            )
            run_command(
                prefix + ["install", "-m", "0644", str(temp_path), str(docker_key)]
            )
        finally:
            temp_path.unlink(missing_ok=True)
    else:
        print_step("Docker apt signing key is already installed.")

    desired_repo = docker_repository_text()
    docker_repo_path = Path("/etc/apt/sources.list.d/docker.list")
    current_repo = (
        docker_repo_path.read_text(encoding="utf-8")
        if docker_repo_path.exists()
        else None
    )
    if current_repo == desired_repo:
        print_step("Docker apt repository is already configured.")
        return

    print_step("Configuring the Docker apt repository.")
    install_file_with_sudo(desired_repo, docker_repo_path, 0o644)


def ensure_docker_group_membership() -> None:
    username = operator_username()
    groups = command_output(["id", "-nG", username]) or ""
    if "docker" in groups.split():
        print_step(f"{username} is already in the docker group.")
        return

    print_step(
        f"Adding {username} to the docker group. Log out and back in when setup is done."
    )
    run_command(sudo_prefix() + ["usermod", "-aG", "docker", username])


def ensure_homeassistant_directories() -> None:
    homeassistant_root = operator_home() / "homeassistant-compose"
    config_dir = homeassistant_root / "config"
    themes_dir = config_dir / "themes"
    for path in (homeassistant_root, config_dir, themes_dir):
        path.mkdir(parents=True, exist_ok=True)
    print_step(f"Home Assistant bootstrap folders are ready at {homeassistant_root}.")


def homeassistant_bootstrap() -> None:
    require_linux()
    ensure_sudo_ready()
    print_step(
        "Home Assistant bootstrap only prepares Docker and the homeassistant-compose folder. Participant-specific Home Assistant files stay under python_scripts/participant_manager.py."
    )
    remove_obsolete_apt_packages(OBSOLETE_DOCKER_PACKAGES)
    ensure_apt_packages(("ca-certificates", "curl"))
    ensure_docker_repository()
    ensure_apt_packages(DOCKER_PACKAGES)
    ensure_docker_group_membership()
    ensure_homeassistant_directories()
    print_step(
        "Home Assistant bootstrap finished. The compose folder is ready, but participant-specific files will be rendered later."
    )


def gui_setup_script() -> Path:
    return REPO_ROOT / "gui_second_version" / "setup_environment.py"


def run_gui_setup() -> None:
    script_path = gui_setup_script()
    if not script_path.exists():
        raise InstallError(f"GUI setup helper is missing: {script_path}")
    print_step("Running the separate GUI environment setup helper.")
    run_command([sys.executable, str(script_path)])


def full_install(*, with_gui: bool) -> None:
    require_linux()
    print_step(
        "Full install now orchestrates clear phases instead of chaining legacy shell blobs."
    )
    machine_bootstrap()
    homeassistant_bootstrap()
    if with_gui:
        run_gui_setup()
    else:
        print_step(
            "Skipping GUI environment setup. Run gui_second_version/bootstrap.sh when you want the separate desktop setup environment."
        )

    print_step(
        "Participant-specific setup is intentionally separate. Run ./participant_change.sh when you are ready to prepare this device for a specific family."
    )
    print_step(f"Home Assistant image is currently set to {HOME_ASSISTANT_IMAGE}.")
    print_step("Full install finished.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Python-backed installer for FLASH-TV machine and Home Assistant bootstrap steps."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "machine-bootstrap",
        help="Prepare the legacy machine runtime environment in ~/py38.",
    )
    subparsers.add_parser(
        "homeassistant-bootstrap",
        help="Prepare Docker and the homeassistant-compose folder.",
    )
    full_parser = subparsers.add_parser(
        "full-install",
        help="Run the explicit machine and Home Assistant bootstrap phases.",
    )
    full_parser.add_argument(
        "--with-gui",
        action="store_true",
        help="Also run gui_second_version/setup_environment.py after machine and Home Assistant bootstrap.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "machine-bootstrap":
            machine_bootstrap()
        elif args.command == "homeassistant-bootstrap":
            homeassistant_bootstrap()
        elif args.command == "full-install":
            full_install(with_gui=args.with_gui)
        else:
            raise InstallError(f"Unsupported command: {args.command}")
        return 0
    except (InstallError, OSError, subprocess.CalledProcessError) as exc:
        print_step(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
