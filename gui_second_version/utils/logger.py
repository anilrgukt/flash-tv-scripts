"""Logging utilities for FLASH-TV setup wizard."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from config.messages import MESSAGES


class FlashLogger:
    """Enhanced logger for FLASH-TV setup wizard."""

    _loggers: dict[str, logging.Logger] = {}
    _initialized = False

    @classmethod
    def setup_logging(cls, log_dir: str = "logs", debug: bool = False) -> None:
        """Setup logging configuration for the application."""
        if cls._initialized:
            return

        # Create log directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            MESSAGES.Logging.FORMAT, datefmt=MESSAGES.Logging.DATE_FORMAT
        )

        simple_formatter = logging.Formatter("%(levelname)s: %(message)s")

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)

        # Main log file handler
        main_log_file = log_path / MESSAGES.Logging.MAIN_LOG_FILE
        main_handler = logging.FileHandler(main_log_file, encoding="utf-8")
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(main_handler)

        # Error log file handler
        error_log_file = log_path / MESSAGES.Logging.ERROR_LOG_FILE
        error_handler = logging.FileHandler(error_log_file, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)

        cls._initialized = True

        # Log initial setup message
        logger = cls.get_logger("setup")
        logger.info("Logging system initialized")
        logger.info(f"Log directory: {log_path.absolute()}")
        logger.info(f"Debug mode: {debug}")

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger instance for the given name."""
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(f"flash_wizard.{name}")
        return cls._loggers[name]

    @classmethod
    def log_step_start(cls, step_id: int, step_name: str) -> None:
        """Log the start of a wizard step."""
        logger = cls.get_logger("steps")
        logger.info(f"Starting Step {step_id}: {step_name}")

    @classmethod
    def log_step_complete(cls, step_id: int, step_name: str) -> None:
        """Log the completion of a wizard step."""
        logger = cls.get_logger("steps")
        logger.info(f"Completed Step {step_id}: {step_name}")

    @classmethod
    def log_step_failed(cls, step_id: int, step_name: str, error: str) -> None:
        """Log the failure of a wizard step."""
        logger = cls.get_logger("steps")
        logger.error(f"Failed Step {step_id}: {step_name} - {error}")

    @classmethod
    def log_process_start(
        cls, process_name: str, command: list[str], description: str
    ) -> None:
        """Log the start of a process."""
        logger = cls.get_logger("processes")
        cmd_str = " ".join(command)
        logger.info(f"Starting process '{process_name}': {description}")
        logger.debug(f"Command: {cmd_str}")

    @classmethod
    def log_process_complete(
        cls, process_name: str, exit_code: int, runtime: float
    ) -> None:
        """Log the completion of a process."""
        logger = cls.get_logger("processes")
        minutes = int(runtime // 60)
        seconds = int(runtime % 60)

        if exit_code == 0:
            logger.info(
                f"Process '{process_name}' completed successfully in {minutes}m {seconds}s"
            )
        else:
            logger.error(
                f"Process '{process_name}' failed with exit code {exit_code} after {minutes}m {seconds}s"
            )

    @classmethod
    def log_user_input(
        cls, field_name: str, value: Any, sensitive: bool = False
    ) -> None:
        """Log user input (with option to hide sensitive data)."""
        logger = cls.get_logger("user_input")

        if sensitive:
            logger.info(f"User input '{field_name}': [REDACTED]")
        else:
            logger.info(f"User input '{field_name}': {value}")

    @classmethod
    def log_system_state(cls, key: str, value: Any) -> None:
        """Log system state changes."""
        logger = cls.get_logger("system_state")
        logger.info(f"System state '{key}': {value}")

    @classmethod
    def log_error(cls, component: str, error: Exception, context: str = "") -> None:
        """Log an error with context."""
        logger = cls.get_logger("errors")
        context_str = f" (Context: {context})" if context else ""
        logger.error(f"Error in {component}{context_str}: {error}", exc_info=True)

    @classmethod
    def log_sudo_operation(
        cls, command: list[str], success: bool, error: str = ""
    ) -> None:
        """Log sudo operations (without exposing passwords)."""
        logger = cls.get_logger("sudo")
        cmd_str = " ".join(command)

        if success:
            logger.info(f"Sudo operation successful: {cmd_str}")
        else:
            logger.warning(f"Sudo operation failed: {cmd_str} - {error}")

    @classmethod
    def log_network_operation(
        cls, operation: str, target: str, success: bool, details: str = ""
    ) -> None:
        """Log network operations."""
        logger = cls.get_logger("network")
        status = "successful" if success else "failed"
        details_str = f" - {details}" if details else ""
        logger.info(f"Network {operation} to {target}: {status}{details_str}")

    @classmethod
    def log_file_operation(
        cls, operation: str, file_path: str, success: bool, error: str = ""
    ) -> None:
        """Log file operations."""
        logger = cls.get_logger("files")

        if success:
            logger.debug(f"File {operation}: {file_path}")
        else:
            logger.error(f"File {operation} failed: {file_path} - {error}")

    @classmethod
    def log_validation_result(
        cls, field: str, value: Any, valid: bool, error: str = ""
    ) -> None:
        """Log validation results."""
        logger = cls.get_logger("validation")

        if valid:
            logger.debug(f"Validation passed for '{field}': {value}")
        else:
            logger.warning(f"Validation failed for '{field}': {value} - {error}")


# Convenience functions for common logging patterns
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return FlashLogger.get_logger(name)


def log_step_start(step_id: int, step_name: str) -> None:
    """Log step start."""
    FlashLogger.log_step_start(step_id, step_name)


def log_step_complete(step_id: int, step_name: str) -> None:
    """Log step completion."""
    FlashLogger.log_step_complete(step_id, step_name)


def log_error(component: str, error: Exception, context: str = "") -> None:
    """Log an error."""
    FlashLogger.log_error(component, error, context)


def log_process_start(process_name: str, command: list[str], description: str) -> None:
    """Log process start."""
    FlashLogger.log_process_start(process_name, command, description)


def log_process_complete(process_name: str, exit_code: int, runtime: float) -> None:
    """Log process completion."""
    FlashLogger.log_process_complete(process_name, exit_code, runtime)


def log_user_input(field_name: str, value: Any, sensitive: bool = False) -> None:
    """Log user input."""
    FlashLogger.log_user_input(field_name, value, sensitive)
