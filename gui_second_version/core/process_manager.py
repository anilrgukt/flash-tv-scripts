"""High-level process lifecycle management for FLASH-TV GUI Setup Wizard.

This module provides a high-level abstraction for managing process lifecycles,
separating concerns from the low-level ProcessRunner.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Optional

from core.process_runner import ProcessRunner
from models.process_info import ProcessInfo


class ProcessState(Enum):
    """Process lifecycle states."""

    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass
class ProcessConfig:
    """Configuration for a managed process.

    This dataclass encapsulates all configuration needed to start and manage
    a background process, including callbacks for lifecycle events.

    Attributes:
        name: Unique identifier for the process
        command: Command and arguments to execute
        timeout_ms: Timeout in milliseconds (default: 30 seconds)
        capture_output: Whether to capture stdout/stderr
        on_start: Callback invoked when process starts (optional)
        on_success: Callback invoked on successful completion (optional)
        on_failure: Callback invoked on failure (optional)
    """

    name: str
    command: list[str]
    timeout_ms: int = 30000
    capture_output: bool = True
    on_start: Optional[Callable[[], None]] = None
    on_success: Optional[Callable[[ProcessInfo], None]] = None
    on_failure: Optional[Callable[[ProcessInfo, Exception], None]] = None


class ProcessManager:
    """High-level process lifecycle management.

    This class provides a higher-level abstraction over ProcessRunner,
    adding lifecycle management, state tracking, and callback support.

    Separation of concerns:
    - ProcessRunner: Low-level subprocess operations, output capture, cleanup
    - ProcessManager: High-level lifecycle, callbacks, state tracking

    Usage:
        >>> manager = ProcessManager(process_runner)
        >>>
        >>> config = ProcessConfig(
        ...     name="gallery_creation",
        ...     command=["python", "create_gallery.py"],
        ...     timeout_ms=60000,
        ...     on_success=lambda p: print("Gallery created!"),
        ...     on_failure=lambda p, e: print(f"Failed: {e}")
        ... )
        >>>
        >>> process = manager.start_process(config)
        >>> success = manager.wait_for_completion("gallery_creation")
    """

    def __init__(self, process_runner: ProcessRunner):
        """Initialize process manager.

        Args:
            process_runner: The low-level process runner to use
        """
        self._runner = process_runner
        self._processes: Dict[str, ProcessInfo] = {}
        self._states: Dict[str, ProcessState] = {}
        self._configs: Dict[str, ProcessConfig] = {}
        self._logger = logging.getLogger(__name__)

    def start_process(self, config: ProcessConfig) -> ProcessInfo:
        """Start a managed process with lifecycle callbacks.

        This method starts a background process and sets up state tracking
        and callbacks. The process runs asynchronously.

        Args:
            config: Process configuration including command and callbacks

        Returns:
            ProcessInfo for the started process

        Raises:
            ValueError: If process with same name already exists
            Exception: If process fails to start

        Example:
            >>> config = ProcessConfig(
            ...     name="wifi_scan",
            ...     command=["nmcli", "device", "wifi", "list"],
            ...     on_success=lambda p: print("Scan complete")
            ... )
            >>> process = manager.start_process(config)
        """
        if config.name in self._processes:
            raise ValueError(f"Process '{config.name}' already exists")

        self._logger.info(f"Starting process: {config.name}")
        self._logger.debug(f"Command: {' '.join(config.command)}")
        self._states[config.name] = ProcessState.STARTING
        self._configs[config.name] = config

        try:
            # Call on_start callback
            if config.on_start:
                self._logger.debug(f"Calling on_start callback for {config.name}")
                config.on_start()

            # Start the process using the low-level runner
            process_info = self._runner.start_background_process(
                name=config.name, command=config.command, timeout_ms=config.timeout_ms
            )

            self._processes[config.name] = process_info
            self._states[config.name] = ProcessState.RUNNING

            self._logger.info(f"Process started successfully: {config.name}")
            return process_info

        except Exception as e:
            self._logger.error(
                f"Failed to start process {config.name}: {e}", exc_info=True
            )
            self._states[config.name] = ProcessState.FAILED

            # Call on_failure callback
            if config.on_failure:
                self._logger.debug(f"Calling on_failure callback for {config.name}")
                try:
                    config.on_failure(None, e)
                except Exception as callback_error:
                    self._logger.error(
                        f"Error in on_failure callback: {callback_error}"
                    )

            raise

    def wait_for_completion(
        self, process_name: str, timeout_ms: Optional[int] = None
    ) -> bool:
        """Wait for process to complete and handle callbacks.

        This method blocks until the process completes or times out,
        then invokes the appropriate success or failure callback.

        Args:
            process_name: Name of process to wait for
            timeout_ms: Optional timeout override (uses config timeout if None)

        Returns:
            True if process completed successfully, False otherwise

        Raises:
            ValueError: If process not found

        Example:
            >>> success = manager.wait_for_completion("gallery_creation")
            >>> if success:
            ...     print("Gallery created!")
        """
        process = self._processes.get(process_name)
        config = self._configs.get(process_name)

        if not process or not config:
            raise ValueError(f"Unknown process: {process_name}")

        self._logger.info(f"Waiting for process completion: {process_name}")

        try:
            # Wait for the process using the low-level runner
            success = self._runner.wait_for_process(process_name, timeout_ms)

            if success:
                self._states[process_name] = ProcessState.COMPLETED
                self._logger.info(f"Process completed successfully: {process_name}")

                # Call on_success callback
                if config.on_success:
                    self._logger.debug(
                        f"Calling on_success callback for {process_name}"
                    )
                    try:
                        config.on_success(process)
                    except Exception as callback_error:
                        self._logger.error(
                            f"Error in on_success callback: {callback_error}"
                        )
            else:
                self._states[process_name] = ProcessState.FAILED
                self._logger.error(f"Process failed: {process_name}")

                # Call on_failure callback
                if config.on_failure:
                    self._logger.debug(
                        f"Calling on_failure callback for {process_name}"
                    )
                    try:
                        error = Exception(f"Process failed with non-zero exit code")
                        config.on_failure(process, error)
                    except Exception as callback_error:
                        self._logger.error(
                            f"Error in on_failure callback: {callback_error}"
                        )

            return success

        except Exception as e:
            self._states[process_name] = ProcessState.FAILED
            self._logger.error(
                f"Error waiting for process {process_name}: {e}", exc_info=True
            )

            # Call on_failure callback
            if config.on_failure:
                self._logger.debug(f"Calling on_failure callback for {process_name}")
                try:
                    config.on_failure(process, e)
                except Exception as callback_error:
                    self._logger.error(
                        f"Error in on_failure callback: {callback_error}"
                    )

            return False

    def get_state(self, process_name: str) -> Optional[ProcessState]:
        """Get current state of a process.

        Args:
            process_name: Name of process to query

        Returns:
            Current ProcessState or None if not found

        Example:
            >>> state = manager.get_state("gallery_creation")
            >>> if state == ProcessState.RUNNING:
            ...     print("Still running...")
        """
        return self._states.get(process_name)

    def get_process(self, process_name: str) -> Optional[ProcessInfo]:
        """Get ProcessInfo for a process.

        Args:
            process_name: Name of process to query

        Returns:
            ProcessInfo or None if not found

        Example:
            >>> process = manager.get_process("gallery_creation")
            >>> if process:
            ...     print(f"Exit code: {process.exit_code}")
        """
        return self._processes.get(process_name)

    def is_running(self, process_name: str) -> bool:
        """Check if a process is currently running.

        Args:
            process_name: Name of process to check

        Returns:
            True if process is running, False otherwise

        Example:
            >>> if manager.is_running("gallery_creation"):
            ...     print("Please wait...")
        """
        state = self._states.get(process_name)
        return state in (ProcessState.STARTING, ProcessState.RUNNING)

    def cleanup(self, process_name: Optional[str] = None) -> None:
        """Clean up process(es) properly.

        This method ensures processes are terminated and resources are freed.

        Args:
            process_name: Specific process to clean up, or None for all

        Example:
            >>> # Clean up specific process
            >>> manager.cleanup("long_running_task")
            >>>
            >>> # Clean up all processes
            >>> manager.cleanup()
        """
        if process_name:
            process = self._processes.get(process_name)
            if process:
                self._logger.info(f"Cleaning up process: {process_name}")
                process.cleanup()
                self._states[process_name] = ProcessState.TERMINATED
        else:
            self._logger.info("Cleaning up all processes")
            for name, process in self._processes.items():
                self._logger.debug(f"Cleaning up process: {name}")
                process.cleanup()
                self._states[name] = ProcessState.TERMINATED

    def cleanup_all(self) -> None:
        """Clean up all managed processes.

        Convenience method that calls cleanup(None).

        Example:
            >>> manager.cleanup_all()
        """
        self.cleanup(None)

    def get_all_states(self) -> Dict[str, ProcessState]:
        """Get states of all managed processes.

        Returns:
            Dictionary mapping process names to their states

        Example:
            >>> states = manager.get_all_states()
            >>> for name, state in states.items():
            ...     print(f"{name}: {state.value}")
        """
        return self._states.copy()
