"""ProcessRunner for unified subprocess management."""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime
from typing import Callable

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QInputDialog, QLineEdit

from constants import Process, Messages
from models import ProcessInfo, ProcessStatus, WizardState
from utils import get_logger, log_process_start, log_process_complete, log_error


class ProcessRunner:
    """Unified subprocess management with monitoring and cleanup."""

    def __init__(self, state: WizardState):
        self.state = state
        self.sudo_password: str | None = None
        self.sudo_password_time: float | None = None
        self.sudo_timeout = Process.SUDO_TIMEOUT_SECONDS
        self.logger = get_logger("process_runner")

        # Setup monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_processes)
        self.monitor_timer.start(Process.MONITOR_INTERVAL_MS)

    def run_script(
        self,
        command: list[str],
        description: str,
        working_dir: str | None = None,
        env: dict[str, str] | None = None,
        process_name: str | None = None,
        cleanup_handler: Callable[[], None] | None = None,
    ) -> ProcessInfo | None:
        """Run a script and track the process."""
        try:
            # Log process start
            log_process_start(process_name or "unnamed", command, description)

            # Prepare environment
            process_env = os.environ.copy()
            if env:
                process_env.update(env)

            # Start process
            process = subprocess.Popen(
                command,
                cwd=working_dir,
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Create process info
            process_info = ProcessInfo(
                process=process,
                description=description,
                start_time=datetime.now(),
                cleanup_handler=cleanup_handler,
            )

            # Track process
            if process_name is None:
                process_name = f"process_{process.pid}"

            self.state.add_process(process_name, process_info)
            self.logger.info(f"Started process '{process_name}' (PID: {process.pid})")

            return process_info

        except Exception as e:
            log_error("process_runner", e, f"starting process '{description}'")
            return None

    def run_sudo_command(
        self,
        command: list[str],
        description: str,
        working_dir: str | None = None,
        process_name: str | None = None,
    ) -> ProcessInfo | None:
        """Run a sudo command with password caching."""
        password, error = self._get_sudo_password(description)
        if error:
            return None

        # Prepare sudo command
        sudo_command = ["sudo", "-S"] + command

        try:
            process = subprocess.Popen(
                sudo_command,
                cwd=working_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Send password
            process.stdin.write(f"{password}\n")
            process.stdin.flush()

            # Create process info
            process_info = ProcessInfo(
                process=process,
                description=f"[SUDO] {description}",
                start_time=datetime.now(),
            )

            # Track process
            if process_name is None:
                process_name = f"sudo_process_{process.pid}"

            self.state.add_process(process_name, process_info)

            return process_info

        except Exception as e:
            print(f"Error starting sudo process '{description}': {e}")
            return None

    def _get_sudo_password(self, description: str) -> tuple[str | None, str | None]:
        """Get sudo password with caching."""
        current_time = time.time()

        # Check if cached password is still valid
        if (
            self.sudo_password
            and self.sudo_password_time
            and current_time - self.sudo_password_time < self.sudo_timeout
        ):
            self.logger.debug("Using cached sudo password")
            return self.sudo_password, None

        # Need to prompt for password
        password, ok = QInputDialog.getText(
            None,
            "Administrator Password Required",
            f"Please enter your password to run:\n{description}",
            QLineEdit.EchoMode.Password,
        )

        if not ok or not password:
            self.logger.info("Sudo password input cancelled by user")
            return None, Messages.PASSWORD_CANCELLED

        # Verify password
        if not self._verify_sudo_password(password):
            self.logger.warning("Invalid sudo password provided")
            return None, Messages.INVALID_PASSWORD

        # Cache password
        self.sudo_password = password
        self.sudo_password_time = current_time
        self.logger.info("Sudo password verified and cached")

        return password, None

    def _verify_sudo_password(self, password: str) -> bool:
        """Verify sudo password without caching."""
        try:
            process = subprocess.Popen(
                ["sudo", "-S", "true"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            process.stdin.write(f"{password}\n")
            process.stdin.flush()
            process.wait(timeout=10)

            return process.returncode == 0

        except Exception:
            return False

    def get_process_status(self, process_name: str) -> ProcessStatus:
        """Get the status of a tracked process."""
        process_info = self.state.get_process(process_name)
        if not process_info:
            return ProcessStatus.NOT_FOUND

        return process_info.get_status()

    def terminate_process(self, process_name: str, force: bool = False) -> bool:
        """Terminate a tracked process."""
        process_info = self.state.get_process(process_name)
        if not process_info:
            return False

        try:
            if force:
                process_info.kill()
            else:
                process_info.terminate()

            # Wait for termination
            try:
                process_info.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                if not force:  # If graceful termination failed, force kill
                    process_info.kill()

            # Run cleanup handler
            process_info.cleanup()

            return True

        except Exception as e:
            print(f"Error terminating process {process_name}: {e}")
            return False

    def cleanup_all_processes(self) -> None:
        """Clean up all tracked processes."""
        for process_name in list(self.state.process_status.keys()):
            self.terminate_process(process_name, force=True)

        # Clear all processes from state
        self.state.process_status.clear()

    def _monitor_processes(self) -> None:
        """Monitor tracked processes and clean up completed ones."""
        completed_processes = []

        for process_name, process_info in self.state.process_status.items():
            status = process_info.get_status()

            if status in [
                ProcessStatus.COMPLETED,
                ProcessStatus.FAILED,
                ProcessStatus.TERMINATED,
            ]:
                # Log process completion
                log_process_complete(
                    process_name,
                    process_info.process.returncode or 0,
                    process_info.get_runtime(),
                )

                completed_processes.append(process_name)
                process_info.cleanup()

        # Remove completed processes
        for process_name in completed_processes:
            self.state.remove_process(process_name)
            self.logger.debug(f"Removed completed process: {process_name}")

    def get_sudo_cache_status(self) -> str:
        """Get the current sudo cache status for UI display."""
        if not self.sudo_password or not self.sudo_password_time:
            return "🔒 No cached credentials"

        current_time = time.time()
        remaining = self.sudo_timeout - (current_time - self.sudo_password_time)

        if remaining <= 0:
            self.sudo_password = None
            self.sudo_password_time = None
            return "🔒 No cached credentials"

        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        return f"🔓 Cached for {minutes:02d}:{seconds:02d}"

    def clear_sudo_cache(self) -> None:
        """Clear cached sudo credentials."""
        self.sudo_password = None
        self.sudo_password_time = None
        self.logger.info("Sudo password cache cleared")

    def is_any_process_running(self) -> bool:
        """Check if any tracked process is currently running."""
        return any(
            process_info.is_running()
            for process_info in self.state.process_status.values()
        )

    def get_running_processes(self) -> dict[str, ProcessInfo]:
        """Get all currently running processes."""
        return {
            name: process_info
            for name, process_info in self.state.process_status.items()
            if process_info.is_running()
        }
