"""Centralized error handling for the FLASH-TV GUI application."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

from core.exceptions import ErrorType, FlashTVError
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QWidget
from utils.logger import get_logger


class ErrorHandler:
    """Centralized error handling utilities for consistent error presentation and logging."""

    @staticmethod
    def show_error_dialog(
        error: Exception,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None,
        detailed_message: Optional[str] = None,
    ) -> None:
        """
        Show error dialog to user with appropriate formatting.

        Args:
            error: The exception to display
            parent: Parent widget for dialog (None for application-level dialog)
            title: Optional custom dialog title
            detailed_message: Optional additional details to show
        """
        if isinstance(error, FlashTVError):
            # Use structured error information
            message = error.get_user_message()
            dialog_title = title or error.error_type.value.replace("_", " ").title()

            # Add context if available
            if error.context and error.context.component:
                message = f"[{error.context.component}]\n{message}"
        else:
            # Generic exception
            message = str(error)
            dialog_title = title or "Error"

        # Add detailed message if provided
        if detailed_message:
            message = f"{message}\n\nDetails:\n{detailed_message}"

        QMessageBox.critical(parent, dialog_title, message)

    @staticmethod
    def show_warning_dialog(
        message: str,
        parent: Optional[QWidget] = None,
        title: str = "Warning",
        detailed_message: Optional[str] = None,
    ) -> None:
        """
        Show warning dialog to user.

        Args:
            message: Warning message to display
            parent: Parent widget for dialog
            title: Dialog title
            detailed_message: Optional additional details
        """
        if detailed_message:
            message = f"{message}\n\nDetails:\n{detailed_message}"

        QMessageBox.warning(parent, title, message)

    @staticmethod
    def show_info_dialog(
        message: str,
        parent: Optional[QWidget] = None,
        title: str = "Information",
        detailed_message: Optional[str] = None,
    ) -> None:
        """
        Show information dialog to user.

        Args:
            message: Information message to display
            parent: Parent widget for dialog
            title: Dialog title
            detailed_message: Optional additional details
        """
        if detailed_message:
            message = f"{message}\n\nDetails:\n{detailed_message}"

        QMessageBox.information(parent, title, message)

    @staticmethod
    def show_question_dialog(
        message: str,
        parent: Optional[QWidget] = None,
        title: str = "Confirm",
        default_yes: bool = False,
    ) -> bool:
        """
        Show yes/no question dialog to user.

        Args:
            message: Question to ask
            parent: Parent widget for dialog
            title: Dialog title
            default_yes: Whether "Yes" should be the default button

        Returns:
            True if user clicked Yes, False otherwise
        """
        default_button = (
            QMessageBox.StandardButton.Yes
            if default_yes
            else QMessageBox.StandardButton.No
        )

        result = QMessageBox.question(
            parent,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button,
        )

        return result == QMessageBox.StandardButton.Yes

    @staticmethod
    def handle_step_error(func: Callable) -> Callable:
        """
        Decorator for step methods that handles errors consistently.

        Use this on button click handlers and other UI methods in wizard steps.
        Logs errors and displays user-friendly dialogs.

        Example:
            @ErrorHandler.handle_step_error
            def on_button_clicked(self):
                # Your code here
                pass
        """

        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            try:
                return func(self, *args, **kwargs)

            except FlashTVError as e:
                # Log structured error
                logger = get_logger(self.__class__.__name__)
                logger.error(
                    f"Step error in {func.__name__}: {e.message}",
                    exc_info=True,
                    extra={
                        "error_type": e.error_type.value,
                        "step": getattr(self, "step_id", "unknown"),
                        "component": e.context.component if e.context else None,
                    },
                )

                # Show user-friendly error dialog
                ErrorHandler.show_error_dialog(e, parent=self)

                # Update step status if method exists
                if hasattr(self, "set_status"):
                    self.set_status("error", e.message)

            except Exception as e:
                # Log unexpected error
                logger = get_logger(self.__class__.__name__)
                logger.error(
                    f"Unexpected error in {func.__name__}: {e}",
                    exc_info=True,
                    extra={
                        "step": getattr(self, "step_id", "unknown"),
                    },
                )

                # Show generic error dialog
                ErrorHandler.show_error_dialog(
                    e,
                    parent=self,
                    title="Unexpected Error",
                    detailed_message="Please contact support if this issue persists.",
                )

                # Update step status if method exists
                if hasattr(self, "set_status"):
                    self.set_status("error", f"Unexpected error: {str(e)}")

        return wrapper

    @staticmethod
    def handle_background_error(
        error: Exception,
        logger_name: str,
        error_signal: Optional[pyqtSignal] = None,
        context: Optional[str] = None,
    ) -> None:
        """
        Handle errors in background operations (threads, processes).

        Args:
            error: The exception that occurred
            logger_name: Name of logger to use
            error_signal: Optional Qt signal to emit for UI notification
            context: Optional context string describing where error occurred
        """
        logger = get_logger(logger_name)

        # Build error message
        error_msg = f"Background error{f' in {context}' if context else ''}: {error}"

        # Log the error
        if isinstance(error, FlashTVError):
            logger.error(
                error_msg,
                exc_info=True,
                extra={
                    "error_type": error.error_type.value,
                    "component": error.context.component if error.context else None,
                },
            )
        else:
            logger.error(error_msg, exc_info=True)

        # Emit signal if provided
        if error_signal:
            if isinstance(error, FlashTVError):
                error_signal.emit(error.get_user_message())
            else:
                error_signal.emit(str(error))

    @staticmethod
    def with_error_logging(logger_name: str) -> Callable:
        """
        Decorator that logs errors without showing dialogs (for background tasks).

        Args:
            logger_name: Name of logger to use

        Example:
            @ErrorHandler.with_error_logging("MyClass")
            def background_task(self):
                # Your code here
                pass
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger = get_logger(logger_name)
                    logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                    raise  # Re-raise for caller to handle

            return wrapper

        return decorator


class ErrorRecovery:
    """Helper class for error recovery strategies."""

    @staticmethod
    def suggest_recovery_action(error: Exception) -> str:
        """
        Suggest a recovery action based on the error type.

        Args:
            error: The exception to analyze

        Returns:
            Suggested recovery action as a string
        """
        if isinstance(error, FlashTVError):
            if error.recovery_action:
                return error.recovery_action

            # Default suggestions based on error type
            suggestions = {
                ErrorType.VALIDATION_ERROR: "Check your input and try again",
                ErrorType.PROCESS_ERROR: "Check system resources and try again",
                ErrorType.NETWORK_ERROR: "Check your network connection and try again",
                ErrorType.PERMISSION_ERROR: "Check permissions and try again",
                ErrorType.CONFIGURATION_ERROR: "Check configuration and try again",
            }

            return suggestions.get(
                error.error_type, "Please try again or contact support"
            )

        # Generic exceptions
        error_str = str(error).lower()

        if "permission" in error_str or "access" in error_str:
            return "Check file/directory permissions and try again"
        elif "not found" in error_str or "no such" in error_str:
            return "Check that the file or resource exists and try again"
        elif "timeout" in error_str:
            return "The operation timed out. Try again with more time"
        elif "connection" in error_str or "network" in error_str:
            return "Check your network connection and try again"
        else:
            return "Please try again or contact support if the issue persists"

    @staticmethod
    def can_retry(error: Exception) -> bool:
        """
        Determine if an error is likely to be transient and worth retrying.

        Args:
            error: The exception to analyze

        Returns:
            True if retry is recommended, False otherwise
        """
        if isinstance(error, FlashTVError):
            # These error types are typically transient
            transient_types = {
                ErrorType.NETWORK_ERROR,
                ErrorType.PROCESS_ERROR,
            }
            return error.error_type in transient_types

        # Check exception message for transient indicators
        error_str = str(error).lower()
        transient_keywords = [
            "timeout",
            "connection",
            "network",
            "temporarily",
            "busy",
            "locked",
        ]

        return any(keyword in error_str for keyword in transient_keywords)
