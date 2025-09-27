"""Thread-safe ProcessRunner with proper resource management."""

from __future__ import annotations

import os
import platform
import subprocess
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Callable, Iterator

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QInputDialog, QLineEdit

from .config import get_config
from .exceptions import ProcessError, PermissionError, handle_step_error
from models import ProcessInfo, WizardState
from utils import get_logger, log_process_start, log_process_complete, log_error


class ProcessRunner:
    """Thread-safe subprocess management with proper resource cleanup."""

    def __init__(self, state: WizardState):
        self.state = state
        self.config = get_config()
        self.logger = get_logger("process_runner")
        self.is_windows = platform.system() == "Windows"

        # Thread-safe password management
        self._password_lock = threading.RLock()
        self._sudo_password: str | None = None
        self._sudo_password_time: float | None = None

        # Process tracking
        self._processes_lock = threading.RLock()
        self._active_processes: dict[str, ProcessInfo] = {}

        # Setup monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_processes)
        self.monitor_timer.start(self.config.process_monitor_interval_ms)

    @contextmanager
    def _managed_process(
        self, command: list[str], **kwargs
    ) -> Iterator[subprocess.Popen]:
        """Context manager for subprocess with automatic cleanup."""
        process = None
        try:
            # Create process with proper pipe handling
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                **kwargs,
            )
            yield process
        except subprocess.SubprocessError as e:
            raise ProcessError(
                f"Failed to start process: {e}",
                command=command,
                recovery_action="Check that the command exists and is executable",
            )
        finally:
            if process:
                self._cleanup_process(process)

    def _cleanup_process(self, process: subprocess.Popen) -> None:
        """Safely cleanup a process and its resources."""
        try:
            # Close pipes
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
            if process.stdout and not process.stdout.closed:
                process.stdout.close()
            if process.stderr and not process.stderr.closed:
                process.stderr.close()

            # Terminate if still running
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Process didn't terminate gracefully, killing")
                    process.kill()
                    process.wait()

        except Exception as e:
            self.logger.error(f"Error during process cleanup: {e}")

    @handle_step_error
    def run_script(
        self,
        command: list[str],
        description: str,
        working_dir: str | None = None,
        env: dict[str, str] | None = None,
        process_name: str | None = None,
        cleanup_handler: Callable[[], None] | None = None,
    ) -> ProcessInfo | None:
        """Run a script and track the process with proper resource management."""
        process_name = process_name or f"process_{int(time.time())}"

        # Log process start
        log_process_start(process_name, command, description)

        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        try:
            # Start process WITHOUT the context manager so it doesn't get terminated
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                cwd=working_dir,
                env=process_env,
            )
            
            # Create ProcessInfo with proper tracking
            process_info = ProcessInfo(
                name=process_name,
                process=process,
                command=command,
                description=description,
                start_time=datetime.now(),
                cleanup_handler=cleanup_handler,
            )
            
            # Start capturing output
            process_info.start_output_capture()

            # Thread-safe process tracking
            with self._processes_lock:
                self._active_processes[process_name] = process_info
                self.state.add_process(process_name, process_info)

            self.logger.info(f"Started process {process_name}: {' '.join(command)}")
            return process_info

        except Exception as e:
            log_error(f"Failed to start process {process_name}", str(e))
            raise ProcessError(
                f"Failed to start process: {e}",
                command=command,
                recovery_action="Check permissions and try again",
            )

    @handle_step_error
    def run_with_sudo(
        self,
        command: list[str],
        description: str,
        working_dir: str | None = None,
        process_name: str | None = None,
    ) -> ProcessInfo | None:
        """Run a command with sudo privileges."""
        # Get or prompt for sudo password
        if not self._get_sudo_password():
            raise PermissionError(
                "Sudo password required but not provided",
                recovery_action="Enter the sudo password when prompted",
            )

        # Prepend sudo to command
        sudo_command = ["sudo", "-S"] + command

        try:
            with self._managed_process(sudo_command, cwd=working_dir) as process:
                # Send password to sudo
                with self._password_lock:
                    if process.stdin and self._sudo_password:
                        try:
                            process.stdin.write(f"{self._sudo_password}\n")
                            process.stdin.flush()
                        except BrokenPipeError:
                            # Process may have already finished
                            pass

                # Create ProcessInfo
                process_name = process_name or f"sudo_process_{int(time.time())}"
                process_info = ProcessInfo(
                    name=process_name,
                    process=process,
                    command=sudo_command,
                    description=description,
                    start_time=datetime.now(),
                )

                # Thread-safe tracking
                with self._processes_lock:
                    self._active_processes[process_name] = process_info
                    self.state.add_process(process_name, process_info)

                return process_info

        except Exception as e:
            raise ProcessError(
                f"Failed to run sudo command: {e}",
                command=sudo_command,
                recovery_action="Check sudo permissions and password",
            )

    def _get_sudo_password(self) -> bool:
        """Get sudo password with thread safety and caching."""
        with self._password_lock:
            # Check if we have a valid cached password
            if (
                self._sudo_password
                and self._sudo_password_time
                and time.time() - self._sudo_password_time
                < self.config.sudo_timeout_seconds
            ):
                return True

            # Verify current password if we have one
            if self._sudo_password and self._verify_sudo_password():
                self._sudo_password_time = time.time()
                return True

            # Prompt for new password
            return self._prompt_sudo_password()

    def _verify_sudo_password(self) -> bool:
        """Verify the current sudo password."""
        try:
            with self._managed_process(["sudo", "-S", "true"]) as process:
                if process.stdin and self._sudo_password:
                    process.stdin.write(f"{self._sudo_password}\n")
                    process.stdin.flush()

                # Wait for completion with timeout
                try:
                    process.wait(timeout=10)
                    return process.returncode == 0
                except subprocess.TimeoutExpired:
                    return False

        except Exception:
            return False

    def _prompt_sudo_password(self) -> bool:
        """Prompt user for sudo password."""
        password, ok = QInputDialog.getText(
            None,
            "Sudo Password Required",
            "Enter your sudo password:",
            QLineEdit.EchoMode.Password,
        )

        if not ok or not password:
            return False

        # Test the password
        with self._password_lock:
            self._sudo_password = password
            if self._verify_sudo_password():
                self._sudo_password_time = time.time()
                return True
            else:
                self._sudo_password = None
                return False

    def set_sudo_password_from_state(self) -> bool:
        """Set sudo password from the wizard state instead of prompting."""
        sudo_password = self.state.get_user_input("sudo_password", "").strip()
        self.logger.info(f"DEBUG: Retrieved sudo password from state: {'***' if sudo_password else 'EMPTY'}")
        if sudo_password:
            with self._password_lock:
                self._sudo_password = sudo_password
                self._sudo_password_time = time.time()
                self.logger.info("Sudo password loaded from state")
            return True
        self.logger.error("CRITICAL: No sudo password found in state!")
        return False

    def _monitor_processes(self) -> None:
        """Monitor running processes and clean up completed ones."""
        completed_processes = []

        with self._processes_lock:
            for name, process_info in list(self._active_processes.items()):
                if not process_info.is_running():
                    completed_processes.append((name, process_info))

        # Handle completed processes outside the lock
        for name, process_info in completed_processes:
            self._handle_process_completion(name, process_info)

    def _handle_process_completion(self, name: str, process_info: ProcessInfo) -> None:
        """Handle completion of a process."""
        try:
            # Log completion
            status = process_info.get_status()
            runtime = process_info.get_runtime()

            log_process_complete(
                name,
                process_info.process.returncode if process_info.process.returncode is not None else -1,
                runtime,
            )

            # Run cleanup handler if provided
            if process_info.cleanup_handler:
                try:
                    process_info.cleanup_handler()
                except Exception as e:
                    self.logger.error(f"Error in cleanup handler for {name}: {e}")

            # Remove from tracking
            with self._processes_lock:
                self._active_processes.pop(name, None)

        except Exception as e:
            self.logger.error(f"Error handling completion of process {name}: {e}")

    @handle_step_error
    def terminate_process(self, process_name: str) -> bool:
        """Terminate a specific process."""
        with self._processes_lock:
            process_info = self._active_processes.get(process_name)

        if not process_info:
            self.logger.warning(f"Process {process_name} not found for termination")
            return False

        try:
            if process_info.is_running():
                process_info.terminate()
                self.logger.info(f"Terminated process {process_name}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error terminating process {process_name}: {e}")
            return False

    def cleanup_all_processes(self) -> None:
        """Cleanup all running processes."""
        with self._processes_lock:
            processes_to_cleanup = list(self._active_processes.items())

        for name, process_info in processes_to_cleanup:
            try:
                if process_info.is_running():
                    self.logger.info(f"Terminating process {name} during cleanup")
                    process_info.terminate()

                # Run cleanup handler
                if process_info.cleanup_handler:
                    process_info.cleanup_handler()

            except Exception as e:
                self.logger.error(f"Error cleaning up process {name}: {e}")

        # Clear tracking
        with self._processes_lock:
            self._active_processes.clear()

        # Stop monitoring timer
        if self.monitor_timer.isActive():
            self.monitor_timer.stop()

    def get_sudo_cache_status(self) -> dict[str, any]:
        """Get current sudo password cache status."""
        with self._password_lock:
            if not self._sudo_password_time:
                return {"cached": False, "expires_in": 0}

            expires_in = max(
                0,
                self.config.sudo_timeout_seconds
                - (time.time() - self._sudo_password_time),
            )

            return {"cached": expires_in > 0, "expires_in": int(expires_in)}

    def get_active_processes(self) -> dict[str, ProcessInfo]:
        """Get copy of currently active processes."""
        with self._processes_lock:
            return self._active_processes.copy()

    @handle_step_error
    def run_command(
        self,
        command: list[str],
        timeout_ms: int = 30000,
        working_dir: str | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess | None:
        """Run a command synchronously and return the result.

        This method runs a command and waits for completion, returning
        a CompletedProcess object with returncode, stdout, and stderr.

        Args:
            command: Command and arguments to run
            timeout_ms: Timeout in milliseconds
            working_dir: Working directory for the command
            env: Environment variables to add/override

        Returns:
            CompletedProcess object with returncode, stdout, stderr
        """
        self.logger.info(f"Running command: {' '.join(command)}")

        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        timeout_seconds = timeout_ms / 1000.0
        
        # Check for Linux-specific commands on Windows
        if self.is_windows and self._is_linux_command(command[0]):
            self.logger.warning(f"Linux command '{command[0]}' not available on Windows - returning mock result")
            return self._create_mock_result(command)

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=working_dir,
                env=process_env,
                check=False,  # Don't raise on non-zero exit codes
            )

            self.logger.debug(
                f"Command completed with return code: {result.returncode}"
            )
            if result.returncode != 0:
                self.logger.warning(f"Command stderr: {result.stderr.strip()}")

            return result

        except subprocess.TimeoutExpired:
            self.logger.error(
                f"Command timed out after {timeout_seconds}s: {' '.join(command)}"
            )
            raise ProcessError(
                f"Command timed out after {timeout_seconds}s",
                command=command,
                recovery_action="Try increasing the timeout or check if the command is hanging",
            )
        except subprocess.SubprocessError as e:
            self.logger.error(f"Command failed: {e}")
            raise ProcessError(
                f"Failed to execute command: {e}",
                command=command,
                recovery_action="Check that the command exists and is executable",
            )
        except Exception as e:
            self.logger.error(f"Unexpected error running command: {e}")
            raise ProcessError(
                f"Unexpected error: {e}",
                command=command,
                recovery_action="Check system resources and try again",
            )
    
    def _is_linux_command(self, command: str) -> bool:
        """Check if a command is Linux-specific."""
        linux_commands = {
            'nmcli', 'timedatectl', 'systemctl', 'v4l2-ctl', 
            'bash', 'sudo', 'service', 'udevadm', 'loginctl', 'gnome-screensaver-command'
        }
        return command in linux_commands
    
    def _create_mock_result(self, command: list[str]) -> subprocess.CompletedProcess:
        """Create a mock result for Linux commands on Windows."""
        cmd = command[0]
        
        # Create appropriate mock responses based on command
        if cmd == 'nmcli':
            if '-f' in command and 'ACTIVE,SSID' in command:
                stdout = "yes:MockWiFi"  # Active WiFi connection
            elif 'rescan' in command:
                stdout = ""  # Scan completed
            elif '-f' in command and 'SSID,SIGNAL' in command:
                stdout = "MockWiFi:85:WPA2\nTestNetwork:70:WPA2"  # Available networks
            else:
                stdout = ""
        elif cmd == 'timedatectl':
            if 'status' in command:
                stdout = "NTP service: active\nSystem clock synchronized: yes"
            else:
                stdout = ""
        elif cmd == 'systemctl':
            stdout = "active" if 'is-active' in command else "enabled"
        elif cmd == 'v4l2-ctl':
            stdout = "Driver name: mock\nCapabilities: 0x04200001"
        elif cmd == 'loginctl' or cmd == 'gnome-screensaver-command':
            stdout = ""  # Screen lock commands don't produce output
        else:
            stdout = f"Mock output for {cmd}"
        
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=stdout,
            stderr=""
        )
    
    def run_sudo_command(
        self,
        command: list[str],
        description: str,
        working_dir: str | None = None,
        timeout_ms: int = 30000,
    ) -> tuple[subprocess.CompletedProcess | None, str | None]:
        """Run a command with sudo privileges.
        
        Returns:
            Tuple of (result, error_message). If successful, error_message is None.
        """
        try:
            # On Windows, just run the command without sudo for testing
            if self.is_windows:
                self.logger.info(f"Running sudo command on Windows (mock): {' '.join(command)}")
                result = self.run_command(command, timeout_ms, working_dir)
                return result, None
            
            # Get sudo password from cache (should be set by set_sudo_password_from_state)
            with self._password_lock:
                password = self._sudo_password
            self.logger.info(f"DEBUG: run_sudo_command using cached password: {'***' if password else 'NONE'}")
            if password is None:
                self.logger.error("CRITICAL: No cached sudo password available in run_sudo_command!")
                return None, "Sudo password required but not provided"
            
            # Prepare sudo command
            sudo_command = ["sudo", "-S"] + command
            
            # Prepare environment
            process_env = os.environ.copy()
            if working_dir is None:
                working_dir = os.getcwd()
            
            timeout_seconds = timeout_ms / 1000.0
            
            try:
                process = subprocess.Popen(
                    sudo_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=working_dir,
                    env=process_env,
                )
                
                # Send password
                stdout, stderr = process.communicate(
                    input=f"{password}\n", timeout=timeout_seconds
                )
                
                # Create result object
                result = subprocess.CompletedProcess(
                    args=sudo_command,
                    returncode=process.returncode,
                    stdout=stdout,
                    stderr=stderr
                )
                
                if result.returncode == 0:
                    self.logger.info(f"Sudo command completed successfully: {description}")
                    return result, None
                else:
                    error_msg = f"Sudo command failed: {stderr.strip()}"
                    self.logger.error(error_msg)
                    return result, error_msg
                    
            except subprocess.TimeoutExpired:
                error_msg = f"Sudo command timed out: {description}"
                self.logger.error(error_msg)
                return None, error_msg
                
        except Exception as e:
            error_msg = f"Error running sudo command: {e}"
            self.logger.error(error_msg)
            return None, error_msg
    
    def _get_sudo_password(self, description: str) -> str | None:
        """Get sudo password from user."""
        with self._password_lock:
            if self._sudo_password is not None:
                return self._sudo_password
                
            # Prompt for password
            from PyQt6.QtWidgets import QInputDialog, QMessageBox, QLineEdit
            
            password, ok = QInputDialog.getText(
                None,
                "Sudo Password Required",
                f"Enter sudo password for: {description}",
                QLineEdit.EchoMode.Password
            )
            
            if ok and password:
                self._sudo_password = password
                return password
            else:
                return None
