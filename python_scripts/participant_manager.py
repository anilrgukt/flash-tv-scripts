#!/usr/bin/env python3

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from typing import Protocol
import urllib.error
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.participant_config import (
    DEFAULT_BLUETOOTH_MAC,
    ParticipantConfig,
    ParticipantConfigError,
    build_participant_config,
)


class ParticipantConfigProtocol(Protocol):
    participant_id: str
    device_id: str
    username: str
    smart_plug_power_sensor_entity_id: str

    @property
    def data_root(self) -> Path: ...

    @property
    def data_dir(self) -> Path: ...

    @property
    def home_dir(self) -> Path: ...

    @property
    def logs_dir(self) -> Path: ...

    @property
    def tv_power_csv_path(self) -> Path: ...

    @property
    def homeassistant_root(self) -> Path: ...

    @property
    def homeassistant_config_dir(self) -> Path: ...

    @property
    def homeassistant_archive_dir(self) -> Path: ...

    @property
    def git_config_copy_path(self) -> Path: ...

    @property
    def backup_readiness_path(self) -> Path: ...

    def template_values(self) -> dict[str, str]: ...


class ParticipantManagerError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackupReadinessStatus:
    is_ready: bool
    summary: str
    next_action: str | None


class ParticipantManager:
    def __init__(self, config: ParticipantConfigProtocol, repo_root: Path) -> None:
        self.config = config
        self.repo_root = repo_root
        self.templates_dir = repo_root / "config" / "templates"

    def apply(self) -> None:
        self._print("Getting the participant files ready.")
        self._ensure_data_directories()
        self._ensure_homeassistant_installation()
        self._stop_running_services_for_reset()
        archive_path = self._archive_existing_homeassistant_config()
        self._render_repo_artifacts()
        self._render_homeassistant_artifacts()
        self._validate_homeassistant_csv_writer_contract()
        self._copy_git_config()
        backup_status = self._assess_backup_readiness()
        self._run_setup_script(self.repo_root / "setup_scripts" / "service_setup.sh")
        self._run_setup_script(self.repo_root / "setup_scripts" / "RTC_setup.sh")
        self._start_homeassistant()
        self._wait_for_homeassistant_readiness()
        self._open_homeassistant_if_available()

        if archive_path is not None:
            self._print(f"Previous Home Assistant data was saved in {archive_path}.")

        self._print(backup_status.summary)
        if backup_status.next_action is not None:
            self._print(backup_status.next_action)

        self._print(
            "Participant change is ready. Pair the smart plug again in Home Assistant, then confirm power readings are appearing."
        )

    def _ensure_data_directories(self) -> None:
        self.config.data_root.mkdir(parents=True, exist_ok=True)
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.config.logs_dir.mkdir(parents=True, exist_ok=True)
        self._verify_tv_power_csv_path()

    def _verify_tv_power_csv_path(self) -> None:
        csv_path = self.config.tv_power_csv_path
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        if csv_path.exists() and csv_path.is_dir():
            raise ParticipantManagerError(
                f"The smart plug CSV path is a folder, not a file: {csv_path}."
            )

        try:
            with csv_path.open("a", encoding="utf-8", newline="") as handle:
                handle.write("")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise ParticipantManagerError(
                f"FLASH could not prepare the smart plug CSV file at {csv_path}. Check that the data folder is writable."
            ) from exc

    def _ensure_homeassistant_installation(self) -> None:
        if self.config.homeassistant_root.exists():
            return

        self._print("Installing the Home Assistant folder for this device.")
        self._run_setup_script(
            self.repo_root / "install_scripts" / "homeassistant_install.sh"
        )

    def _stop_running_services_for_reset(self) -> None:
        stop_script = self.repo_root / "services" / "stop_services.sh"
        if not self.config.homeassistant_root.exists():
            return

        self._run_command(
            ["bash", str(stop_script), self.config.username],
            check=False,
        )

    def _archive_existing_homeassistant_config(self) -> Path | None:
        config_dir = self.config.homeassistant_config_dir
        if not config_dir.exists() or not any(config_dir.iterdir()):
            if config_dir.exists() and config_dir.is_dir():
                shutil.rmtree(config_dir)
            return None

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        previous_full_id = self._detect_previous_full_id() or "previous-participant"
        archive_dir = (
            self.config.homeassistant_archive_dir
            / f"{timestamp}-{previous_full_id}-homeassistant-config"
        )
        archive_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(config_dir), str(archive_dir))
        return archive_dir

    def _detect_previous_full_id(self) -> str | None:
        compose_path = self.config.homeassistant_root / "compose.yaml"
        if not compose_path.exists():
            return None

        text = compose_path.read_text(encoding="utf-8")
        match = re.search(r":/([^/]+)_data", text)
        if match:
            return match.group(1)
        return None

    def _render_repo_artifacts(self) -> None:
        context = self.config.template_values()
        repo_targets = {
            "install_compose.yaml.tmpl": self.repo_root
            / "install_scripts"
            / "compose.yaml",
            "flash-run-on-boot.service.tmpl": self.repo_root
            / "services"
            / "flash-run-on-boot.service",
            "flash-periodic-restart.service.tmpl": self.repo_root
            / "services"
            / "flash-periodic-restart.service",
            "flash_run_on_boot.sh.tmpl": self.repo_root
            / "services"
            / "flash_run_on_boot.sh",
            "flash_periodic_restart.sh.tmpl": self.repo_root
            / "services"
            / "flash_periodic_restart.sh",
            "homeassistant_configuration.yaml.tmpl": self.repo_root
            / "install_scripts"
            / "configuration.yaml",
            "homeassistant_automations.yaml.tmpl": self.repo_root
            / "install_scripts"
            / "automations.yaml",
            "homeassistant_scripts.yaml.tmpl": self.repo_root
            / "install_scripts"
            / "scripts.yaml",
            "homeassistant_scenes.yaml.tmpl": self.repo_root
            / "install_scripts"
            / "scenes.yaml",
            "rtc_setup.sh.tmpl": self.repo_root / "setup_scripts" / "RTC_setup.sh",
            "USB_backup_setup.sh.tmpl": self.repo_root
            / "setup_scripts"
            / "USB_backup_setup.sh",
            "build_gallery.sh.tmpl": self.repo_root
            / "runtime_scripts"
            / "build_gallery.sh",
            "create_faces.sh.tmpl": self.repo_root
            / "runtime_scripts"
            / "create_faces.sh",
            "run_flashtv_system.sh.tmpl": self.repo_root
            / "runtime_scripts"
            / "run_flashtv_system.sh",
            "face_ID_transfer.sh.tmpl": self.repo_root
            / "runtime_scripts"
            / "face_ID_transfer.sh",
        }

        for template_name, target_path in repo_targets.items():
            self._render_template(template_name, target_path, context)

    def _render_homeassistant_artifacts(self) -> None:
        config_dir = self.config.homeassistant_config_dir
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "themes").mkdir(parents=True, exist_ok=True)

        context = self.config.template_values()
        self._render_template(
            "install_compose.yaml.tmpl",
            self.config.homeassistant_root / "compose.yaml",
            context,
        )
        self._render_template(
            "homeassistant_configuration.yaml.tmpl",
            config_dir / "configuration.yaml",
            context,
        )
        self._render_template(
            "homeassistant_automations.yaml.tmpl",
            config_dir / "automations.yaml",
            context,
        )
        self._render_template(
            "homeassistant_scripts.yaml.tmpl",
            config_dir / "scripts.yaml",
            context,
        )
        self._render_template(
            "homeassistant_scenes.yaml.tmpl",
            config_dir / "scenes.yaml",
            context,
        )

    def _copy_git_config(self) -> None:
        source = self.repo_root / ".git" / "config"
        if source.exists():
            shutil.copy2(source, self.config.git_config_copy_path)

    def _assess_backup_readiness(self) -> BackupReadinessStatus:
        setup_script_path = self.repo_root / "setup_scripts" / "USB_backup_setup.sh"
        if not setup_script_path.exists():
            raise ParticipantManagerError(
                f"FLASH expected the backup setup script at {setup_script_path}, but it is missing."
            )

        borg_env_path = self.config.home_dir / ".flash_borg_env"
        borg_env_text = ""
        if borg_env_path.exists():
            borg_env_text = borg_env_path.read_text(encoding="utf-8")

        borg_repo = self._extract_shell_export_value(borg_env_text, "BORG_REPO")
        borg_passphrase = self._extract_shell_export_value(
            borg_env_text, "BORG_PASSPHRASE"
        )
        borg_repo_access_error: str | None = None
        is_ready = bool(borg_repo and borg_passphrase)
        if is_ready:
            borg_repo_access_error = self._probe_borg_repository(
                borg_repo=borg_repo,
                borg_passphrase=borg_passphrase,
            )
            is_ready = borg_repo_access_error is None

        if is_ready:
            summary = (
                "USB backup is already configured for this device. "
                f"Readiness report: {self.config.backup_readiness_path}."
            )
            next_action = None
        else:
            summary = (
                "USB backup is not ready for this device yet. "
                f"Readiness report: {self.config.backup_readiness_path}."
            )
            if borg_repo_access_error is not None:
                next_action = (
                    "Required next action before leaving the home: the Borg backup "
                    "repository could not be opened with the current configuration. "
                    f"Details: {borg_repo_access_error} Reconnect the backup USB and rerun "
                    f"{setup_script_path}, then complete the USB backup setup flow until Borg "
                    "can open the configured repository."
                )
            elif borg_env_path.exists():
                next_action = (
                    "Required next action before leaving the home: ensure "
                    f"{borg_env_path} contains valid BORG_REPO and "
                    "BORG_PASSPHRASE exports, or rerun "
                    f"{setup_script_path} and complete the USB backup setup flow."
                )
            else:
                next_action = (
                    "Required next action before leaving the home: "
                    f"{borg_env_path} is missing. Run {setup_script_path} and "
                    "complete the USB backup setup flow so it writes the Borg "
                    "exports there."
                )

        self._write_backup_readiness_report(
            setup_script_path=setup_script_path,
            borg_env_path=borg_env_path,
            borg_repo=borg_repo,
            borg_passphrase=borg_passphrase,
            borg_repo_access_error=borg_repo_access_error,
            is_ready=is_ready,
            next_action=next_action,
        )

        return BackupReadinessStatus(
            is_ready=is_ready,
            summary=summary,
            next_action=next_action,
        )

    def _write_backup_readiness_report(
        self,
        *,
        setup_script_path: Path,
        borg_env_path: Path,
        borg_repo: str | None,
        borg_passphrase: str | None,
        borg_repo_access_error: str | None,
        is_ready: bool,
        next_action: str | None,
    ) -> None:
        lines = [
            f"checked_at={datetime.now().isoformat(timespec='seconds')}",
            f"backup_ready={'yes' if is_ready else 'no'}",
            f"setup_script={setup_script_path}",
            f"borg_env_path={borg_env_path}",
            "borg_env_source_of_truth=~/.flash_borg_env",
            f"borg_env_file_present={'yes' if borg_env_path.exists() else 'no'}",
            f"borg_repo_configured={'yes' if borg_repo else 'no'}",
            f"borg_passphrase_configured={'yes' if borg_passphrase else 'no'}",
            f"borg_repo_accessible={'yes' if borg_repo_access_error is None and borg_repo and borg_passphrase else 'no'}",
        ]

        if borg_repo:
            lines.append(f"borg_repo={borg_repo}")
        if borg_repo_access_error is not None:
            lines.append(f"borg_repo_access_error={borg_repo_access_error}")
        if next_action is not None:
            lines.append(f"next_action={next_action}")

        self.config.backup_readiness_path.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )

    def _probe_borg_repository(
        self,
        *,
        borg_repo: str,
        borg_passphrase: str,
    ) -> str | None:
        borg = shutil.which("borg")
        if borg is None:
            return "The 'borg' command is not available on this device."

        env = os.environ.copy()
        env["BORG_REPO"] = borg_repo
        env["BORG_PASSPHRASE"] = borg_passphrase

        result = subprocess.run(
            [borg, "repo-info"],
            text=True,
            capture_output=True,
            env=env,
        )
        if result.returncode == 0:
            return None

        detail = self._summarize_command_output(result.stderr) or self._summarize_command_output(
            result.stdout
        )
        if detail:
            return detail
        return f"borg info exited with code {result.returncode}."

    def _extract_shell_export_value(self, shell_text: str, name: str) -> str | None:
        match = re.search(rf"^export {re.escape(name)}=(.+)$", shell_text, re.MULTILINE)
        if match is None:
            return None

        value = match.group(1).strip()
        if not value:
            return None

        if value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1].strip()

        return value or None

    def _run_setup_script(self, script_path: Path) -> None:
        self._run_command(["bash", str(script_path)])

    def _start_homeassistant(self) -> None:
        self._print("Starting Home Assistant with the new participant files.")
        self._run_command(
            ["docker", "compose", "up", "-d"],
            cwd=self.config.homeassistant_root,
        )

    def _validate_homeassistant_csv_writer_contract(self) -> None:
        full_id = f"{self.config.participant_id}{self.config.device_id}"
        container_data_dir = PurePosixPath(f"/{full_id}_data")
        container_csv_path = container_data_dir / f"{full_id}_tv_power_5s.csv"
        csv_filename = self.config.tv_power_csv_path.name

        if self.config.tv_power_csv_path.parent != self.config.data_dir:
            raise ParticipantManagerError(
                "The smart plug CSV file is not in the participant data folder."
            )

        if csv_filename != f"{full_id}_tv_power_5s.csv":
            raise ParticipantManagerError(
                f"The smart plug CSV file name is wrong: {csv_filename}."
            )

        compose_path = self.config.homeassistant_root / "compose.yaml"
        configuration_path = self.config.homeassistant_config_dir / "configuration.yaml"
        automations_path = self.config.homeassistant_config_dir / "automations.yaml"

        compose_text = compose_path.read_text(encoding="utf-8")
        configuration_text = configuration_path.read_text(encoding="utf-8")
        automations_text = automations_path.read_text(encoding="utf-8")

        expected_mount = f"- {self.config.data_dir}:{container_data_dir}"
        if expected_mount not in compose_text:
            raise ParticipantManagerError(
                "The rendered Home Assistant compose file is not mounting the participant data folder to the expected container path."
            )

        expected_allowlist = f'    - "{container_data_dir}"'
        if expected_allowlist not in configuration_text:
            raise ParticipantManagerError(
                "The rendered Home Assistant configuration is not allowlisting the participant data folder."
            )

        if "name: file" not in configuration_text:
            raise ParticipantManagerError(
                "The rendered Home Assistant configuration is missing the notify.file definition."
            )

        expected_filename = f'    filename: "{container_csv_path}"'
        if expected_filename not in configuration_text:
            raise ParticipantManagerError(
                "The rendered Home Assistant configuration is not pointing notify.file at the participant CSV path."
            )

        if "- service: notify.file" not in automations_text:
            raise ParticipantManagerError(
                "The rendered Home Assistant automations are not calling notify.file for TV power logging."
            )

        if self.config.smart_plug_power_sensor_entity_id not in automations_text:
            raise ParticipantManagerError(
                "The rendered Home Assistant automations are missing the smart plug power sensor entity ID."
            )

        if str(container_csv_path) != f"{container_data_dir}/{csv_filename}":
            raise ParticipantManagerError(
                "The rendered Home Assistant CSV path does not match the participant CSV contract."
            )

    def _wait_for_homeassistant_readiness(self) -> None:
        self._print("Waiting for Home Assistant to finish starting.")
        endpoints = (
            ("http://localhost:8123/", {200, 301, 302, 303, 307, 308}),
            ("http://localhost:8123/api/", {200, 401, 403}),
        )
        deadline = time.monotonic() + 180

        while time.monotonic() < deadline:
            if all(
                self._is_http_endpoint_ready(url, expected_statuses)
                for url, expected_statuses in endpoints
            ):
                self._print("Home Assistant is responding.")
                return
            time.sleep(3)

        raise ParticipantManagerError(
            "Home Assistant did not become ready at http://localhost:8123/ and http://localhost:8123/api/."
        )

    def _is_http_endpoint_ready(self, url: str, expected_statuses: set[int]) -> bool:
        request = urllib.request.Request(url, method="GET")

        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.getcode() in expected_statuses
        except urllib.error.HTTPError as exc:
            return exc.code in expected_statuses
        except urllib.error.URLError:
            return False

    def _open_homeassistant_if_available(self) -> None:
        firefox = shutil.which("firefox")
        if firefox is None:
            return

        subprocess.Popen(
            [firefox, "--new-window", "http://localhost:8123/history"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _render_template(
        self, template_name: str, target_path: Path, context: dict[str, str]
    ) -> None:
        template_path = self.templates_dir / template_name
        template = template_path.read_text(encoding="utf-8")
        rendered = template
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)

        if re.search(r"\{\{[A-Z0-9_]+\}\}", rendered):
            raise ParticipantManagerError(
                f"Template placeholders are still unresolved in {template_name}."
            )

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(rendered.rstrip() + "\n", encoding="utf-8")

    def _run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
        )

        if check and result.returncode != 0:
            raise ParticipantManagerError(
                self._format_command_failure_message(
                    command=command,
                    cwd=cwd,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
            )

        return result

    def _format_command_failure_message(
        self,
        *,
        command: list[str],
        cwd: Path | None,
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> str:
        command_text = " ".join(command)
        detail = self._summarize_command_output(stderr) or self._summarize_command_output(
            stdout
        )
        message = (
            "Participant change could not finish because this step failed: "
            f"{command_text}."
        )

        if cwd is not None:
            message += f" Working folder: {cwd}."

        message += f" Exit code: {returncode}."

        if detail:
            message += f" Details: {detail}"
        else:
            message += " Details: The step exited without a readable error message."

        return message

    @staticmethod
    def _summarize_command_output(output: str) -> str:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            return ""

        summary = " ".join(lines[-3:])
        if len(summary) > 400:
            summary = summary[:397].rstrip() + "..."
        return summary

    @staticmethod
    def _print(message: str) -> None:
        print(message)


def detect_username() -> str:
    return Path.home().name


def detect_device_id(username: str) -> str:
    match = re.search(r"(\d{3})$", username)
    if match is None:
        raise ParticipantManagerError(
            "The username does not end in a 3-digit device ID."
        )
    return match.group(1)


def prompt_for_participant_id() -> str:
    zenity = shutil.which("zenity")
    prompt_text = (
        "Enter the participant ID. Use P1-1234 for TECH homes or ES-1234 for ESS homes."
    )

    if zenity is not None:
        result = subprocess.run(
            [
                zenity,
                "--entry",
                "--width",
                "500",
                "--height",
                "100",
                "--text",
                prompt_text,
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode != 0:
            raise ParticipantManagerError("Participant change was cancelled.")
        return result.stdout.strip()

    return input(f"{prompt_text}\n").strip()


def confirm_details(participant_id: str, device_id: str) -> None:
    zenity = shutil.which("zenity")
    message = (
        "Please confirm these details.\n\n"
        f"Participant ID: {participant_id}\n"
        f"Device ID: {device_id}"
    )

    if zenity is not None:
        result = subprocess.run(
            [
                zenity,
                "--question",
                "--title",
                "Verify Details",
                "--width",
                "500",
                "--height",
                "100",
                "--text",
                message,
                "--no-wrap",
            ],
            check=False,
            text=True,
        )
        if result.returncode != 0:
            raise ParticipantManagerError("Participant change was cancelled.")
        return

    answer = input(f"{message}\nType yes to continue: ").strip().lower()
    if answer not in {"y", "yes"}:
        raise ParticipantManagerError("Participant change was cancelled.")


def show_error(message: str) -> None:
    zenity = shutil.which("zenity")
    if zenity is not None:
        subprocess.run(
            [
                zenity,
                "--warning",
                "--width",
                "500",
                "--height",
                "100",
                "--text",
                message,
            ],
            check=False,
            text=True,
        )
        return

    print(message, file=sys.stderr)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare FLASH-TV for a new participant."
    )
    parser.add_argument("--participant-id")
    parser.add_argument("--device-id")
    parser.add_argument("--username")
    parser.add_argument("--bluetooth-mac-address", default=DEFAULT_BLUETOOTH_MAC)
    parser.add_argument("--skip-confirm", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        username = args.username or detect_username()
        device_id = args.device_id or detect_device_id(username)
        participant_id = args.participant_id or prompt_for_participant_id()

        if not args.skip_confirm:
            confirm_details(participant_id, device_id)

        config = build_participant_config(
            participant_id=participant_id,
            device_id=device_id,
            username=username,
            bluetooth_beacon_mac_address=args.bluetooth_mac_address,
        )
        manager = ParticipantManager(config=config, repo_root=REPO_ROOT)
        manager.apply()
        return 0
    except (ParticipantConfigError, ParticipantManagerError, FileNotFoundError) as exc:
        show_error(str(exc))
        return 1
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() if exc.stderr else str(exc)
        show_error(message or "Participant change did not finish.")
        return exc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
