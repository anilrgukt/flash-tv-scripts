"""Custom exceptions and error handling framework for FLASH-TV GUI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ErrorType(StrEnum):
    """Types of errors that can occur in the application."""

    USER_ERROR = "user_error"
    SYSTEM_ERROR = "system_error"
    VALIDATION_ERROR = "validation_error"
    PROCESS_ERROR = "process_error"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    UI_ERROR = "ui_error"


@dataclass
class ErrorContext:
    """Context information for errors."""

    step_id: int | None = None
    component: str | None = None
    operation: str | None = None
    details: dict[str, Any] | None = None


class FlashTVError(Exception):
    """Base exception for all FLASH-TV errors."""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.SYSTEM_ERROR,
        recovery_action: str | None = None,
        context: ErrorContext | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.recovery_action = recovery_action
        self.context = context or ErrorContext()

    def get_user_message(self) -> str:
        """Get a user-friendly error message."""
        if self.recovery_action:
            return f"{self.message}\n\nSuggested action: {self.recovery_action}"
        return self.message


class ValidationError(FlashTVError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None, **kwargs):
        super().__init__(message, ErrorType.VALIDATION_ERROR, **kwargs)
        self.field = field


class ProcessError(FlashTVError):
    """Raised when a process execution fails."""

    def __init__(
        self,
        message: str,
        command: list[str] | None = None,
        exit_code: int | None = None,
        **kwargs,
    ):
        super().__init__(message, ErrorType.PROCESS_ERROR, **kwargs)
        self.command = command
        self.exit_code = exit_code


class ConfigurationError(FlashTVError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_key: str | None = None, **kwargs):
        super().__init__(message, ErrorType.CONFIGURATION_ERROR, **kwargs)
        self.config_key = config_key


class NetworkError(FlashTVError):
    """Raised when network operations fail."""

    def __init__(self, message: str, url: str | None = None, **kwargs):
        super().__init__(message, ErrorType.NETWORK_ERROR, **kwargs)
        self.url = url


class PermissionError(FlashTVError):
    """Raised when permission is denied."""

    def __init__(self, message: str, resource: str | None = None, **kwargs):
        super().__init__(message, ErrorType.PERMISSION_ERROR, **kwargs)
        self.resource = resource


def handle_step_error(func):
    """Decorator for consistent error handling in step methods."""
    from functools import wraps
    from PyQt6.QtWidgets import QMessageBox
    from utils import get_logger

    logger = get_logger("error_handler")

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except FlashTVError as e:
            logger.error(
                f"FlashTV error in {func.__name__}: {e.message}",
                extra={
                    "error_type": e.error_type,
                    "context": e.context.__dict__,
                },
            )

            # Show user-friendly error dialog
            if hasattr(self, "parent"):
                QMessageBox.critical(
                    self.parent() if callable(self.parent) else self,
                    f"{e.error_type.value.replace('_', ' ').title()}",
                    e.get_user_message(),
                )

            # Update step status if applicable
            if hasattr(self, "update_status"):
                from models import StepStatus

                self.update_status(StepStatus.FAILED)

        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")

            if hasattr(self, "parent"):
                QMessageBox.critical(
                    self.parent() if callable(self.parent) else self,
                    "Unexpected Error",
                    f"An unexpected error occurred: {str(e)}\n\n"
                    "Please try again or contact support.",
                )

    return wrapper
