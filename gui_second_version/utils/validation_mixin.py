"""Real-time validation mixin for input widgets in FLASH-TV GUI Setup Wizard.

This module provides a mixin class to add real-time validation feedback to
input widgets, improving user experience by showing validation status as
the user types.
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QLineEdit, QWidget


class ValidationMixin:
    """Mixin to add real-time validation to input widgets.

    This mixin provides methods to set up real-time validation on QLineEdit
    widgets, showing visual feedback (border color, tooltips) as the user types.

    Example:
        >>> class MyStep(WizardStep, ValidationMixin):
        ...     def create_input(self):
        ...         input_field = QLineEdit()
        ...         self.setup_realtime_validation(
        ...             input_field,
        ...             self.validate_participant_id
        ...         )
        ...         return input_field
    """

    @staticmethod
    def setup_realtime_validation(
        widget: QLineEdit,
        validator: Callable[[str], Tuple[bool, str]],
        error_style: str = "border: 2px solid #c62828; background-color: #ffebee;",
        success_style: str = "border: 2px solid #2e7d32; background-color: #e8f5e8;",
        neutral_style: str = "border: 1px solid #ccc; background-color: white;",
        show_tooltip: bool = True,
        feedback_label: Optional[QLabel] = None,
    ) -> None:
        """Set up real-time validation on a QLineEdit.

        This method connects to the textChanged signal and updates the widget's
        visual style and tooltip based on validation results.

        Args:
            widget: The QLineEdit to validate
            validator: Function that takes text and returns (is_valid, error_message)
            error_style: CSS style for invalid input (default: red border)
            success_style: CSS style for valid input (default: green border)
            neutral_style: CSS style for empty/neutral input (default: gray border)
            show_tooltip: Whether to show validation messages as tooltips (default: True)
            feedback_label: Optional QLabel to show validation status icon

        Example:
            >>> def validate_email(text):
            ...     if not text:
            ...         return False, "Email is required"
            ...     if '@' not in text:
            ...         return False, "Must contain @"
            ...     return True, "Valid email"
            >>>
            >>> email_input = QLineEdit()
            >>> ValidationMixin.setup_realtime_validation(
            ...     email_input,
            ...     validate_email
            ... )
        """

        def on_text_changed(text: str):
            # Empty input gets neutral style
            if not text or not text.strip():
                widget.setStyleSheet(neutral_style)
                if show_tooltip:
                    widget.setToolTip("")
                if feedback_label:
                    feedback_label.setText("")
                return

            # Validate the input
            is_valid, error_msg = validator(text)

            if is_valid:
                # Valid input
                widget.setStyleSheet(success_style)
                if show_tooltip:
                    widget.setToolTip("✓ Valid")
                if feedback_label:
                    feedback_label.setText("✓")
                    feedback_label.setStyleSheet("color: #2e7d32; font-size: 16px;")
            else:
                # Invalid input
                widget.setStyleSheet(error_style)
                if show_tooltip:
                    widget.setToolTip(f"✗ {error_msg}")
                if feedback_label:
                    feedback_label.setText("✗")
                    feedback_label.setStyleSheet("color: #c62828; font-size: 16px;")

        # Connect to text changed signal
        widget.textChanged.connect(on_text_changed)

    @staticmethod
    def create_validated_input(
        validator: Callable[[str], Tuple[bool, str]],
        placeholder: str = "",
        initial_value: str = "",
        **validation_kwargs,
    ) -> Tuple[QLineEdit, QLabel]:
        """Create a QLineEdit with validation and feedback label.

        This is a convenience method that creates both the input field and
        a feedback label, already configured for real-time validation.

        Args:
            validator: Validation function
            placeholder: Placeholder text for input
            initial_value: Initial value for input
            **validation_kwargs: Additional arguments for setup_realtime_validation

        Returns:
            Tuple of (input_field, feedback_label)

        Example:
            >>> def validate_port(text):
            ...     try:
            ...         port = int(text)
            ...         if 1 <= port <= 65535:
            ...             return True, ""
            ...         return False, "Port must be 1-65535"
            ...     except ValueError:
            ...         return False, "Must be a number"
            >>>
            >>> port_input, feedback = ValidationMixin.create_validated_input(
            ...     validate_port,
            ...     placeholder="8123"
            ... )
        """
        # Create input field
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        if initial_value:
            input_field.setText(initial_value)

        # Create feedback label
        feedback_label = QLabel()
        feedback_label.setFixedWidth(30)
        feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set up validation
        ValidationMixin.setup_realtime_validation(
            input_field, validator, feedback_label=feedback_label, **validation_kwargs
        )

        return input_field, feedback_label

    @staticmethod
    def add_validation_feedback_widget(
        parent: QWidget,
        input_field: QLineEdit,
        validator: Callable[[str], Tuple[bool, str]],
    ) -> QLabel:
        """Add a validation feedback widget next to an existing input field.

        Args:
            parent: Parent widget
            input_field: Existing QLineEdit to validate
            validator: Validation function

        Returns:
            The created feedback label

        Example:
            >>> # For an existing input field
            >>> feedback = ValidationMixin.add_validation_feedback_widget(
            ...     self,
            ...     self.participant_id_input,
            ...     self.validate_participant_id
            ... )
        """
        feedback_label = QLabel(parent)
        feedback_label.setFixedWidth(30)
        feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ValidationMixin.setup_realtime_validation(
            input_field, validator, feedback_label=feedback_label
        )

        return feedback_label

    @staticmethod
    def validate_on_focus_lost(
        widget: QLineEdit,
        validator: Callable[[str], Tuple[bool, str]],
        on_invalid: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Set up validation that triggers when widget loses focus.

        This is useful for less intrusive validation that doesn't trigger
        on every keystroke.

        Args:
            widget: The QLineEdit to validate
            validator: Validation function
            on_invalid: Optional callback when validation fails

        Example:
            >>> def show_error(error_msg):
            ...     QMessageBox.warning(self, "Invalid Input", error_msg)
            >>>
            >>> ValidationMixin.validate_on_focus_lost(
            ...     self.participant_id_input,
            ...     self.validate_participant_id,
            ...     on_invalid=show_error
            ... )
        """

        def on_focus_out(event):
            text = widget.text()
            if text and text.strip():
                is_valid, error_msg = validator(text)
                if not is_valid and on_invalid:
                    on_invalid(error_msg)
            # Call original focus out handler
            QLineEdit.focusOutEvent(widget, event)

        # Replace focus out event
        widget.focusOutEvent = on_focus_out

    @staticmethod
    def clear_validation_style(widget: QLineEdit) -> None:
        """Clear validation styling from a widget.

        Resets the widget to neutral state without validation feedback.

        Args:
            widget: The QLineEdit to clear

        Example:
            >>> ValidationMixin.clear_validation_style(self.participant_id_input)
        """
        widget.setStyleSheet("")
        widget.setToolTip("")

    @staticmethod
    def set_validation_state(
        widget: QLineEdit,
        is_valid: bool,
        message: str = "",
        error_style: str = "border: 2px solid #c62828; background-color: #ffebee;",
        success_style: str = "border: 2px solid #2e7d32; background-color: #e8f5e8;",
    ) -> None:
        """Manually set the validation state of a widget.

        Useful when validation is done externally (e.g., async validation).

        Args:
            widget: The QLineEdit to update
            is_valid: Whether the input is valid
            message: Message to show in tooltip
            error_style: CSS style for error state
            success_style: CSS style for success state

        Example:
            >>> # After async validation
            >>> ValidationMixin.set_validation_state(
            ...     self.api_key_input,
            ...     is_valid=False,
            ...     message="API key not found"
            ... )
        """
        if is_valid:
            widget.setStyleSheet(success_style)
            widget.setToolTip(f"✓ {message}" if message else "✓ Valid")
        else:
            widget.setStyleSheet(error_style)
            widget.setToolTip(f"✗ {message}" if message else "✗ Invalid")


class ValidationStyles:
    """Pre-defined validation styles for consistency.

    This class provides standardized CSS styles for validation states
    across the application.
    """

    # Default styles
    ERROR = "border: 2px solid #c62828; background-color: #ffebee; padding: 8px;"
    SUCCESS = "border: 2px solid #2e7d32; background-color: #e8f5e8; padding: 8px;"
    NEUTRAL = "border: 1px solid #ccc; background-color: white; padding: 8px;"
    WARNING = "border: 2px solid #f57c00; background-color: #fff3e0; padding: 8px;"

    # Subtle styles (less prominent)
    ERROR_SUBTLE = "border-bottom: 2px solid #c62828;"
    SUCCESS_SUBTLE = "border-bottom: 2px solid #2e7d32;"
    WARNING_SUBTLE = "border-bottom: 2px solid #f57c00;"

    # Large input styles
    ERROR_LARGE = "border: 3px solid #c62828; background-color: #ffebee; padding: 12px; font-size: 16px;"
    SUCCESS_LARGE = "border: 3px solid #2e7d32; background-color: #e8f5e8; padding: 12px; font-size: 16px;"
    NEUTRAL_LARGE = "border: 2px solid #ccc; background-color: white; padding: 12px; font-size: 16px;"

    @classmethod
    def get_style(cls, state: str, size: str = "normal") -> str:
        """Get a validation style by state and size.

        Args:
            state: One of 'error', 'success', 'neutral', 'warning'
            size: One of 'normal', 'subtle', 'large'

        Returns:
            CSS style string

        Example:
            >>> style = ValidationStyles.get_style('error', 'large')
        """
        attr_name = (
            f"{state.upper()}_{size.upper()}" if size != "normal" else state.upper()
        )
        return getattr(cls, attr_name, cls.NEUTRAL)
