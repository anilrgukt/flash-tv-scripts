"""Participant setup step implementation using new framework patterns."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QFileDialog

from constants import Templates, Messages, Patterns
from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus


class ParticipantSetupStep(WizardStep):
    """Step 1: Participant and Device Setup using new framework patterns."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def create_content_widget(self) -> QWidget:
        """Create the participant setup UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create main sections using horizontal layout factory method
        participant_section = self._create_participant_info_section()
        data_section = self._create_data_storage_section()

        sections_layout = self.ui_factory.create_horizontal_section(
            participant_section, data_section, spacing=12
        )
        main_layout.addLayout(sections_layout)

        # Add validation feedback using UI factory
        self._create_validation_section(main_layout)

        # Add stretch to push button to bottom
        main_layout.addStretch()

        # Add action buttons using UI factory
        self._create_button_section(main_layout)

        # Load existing values
        self._load_existing_values()

        return content

    def _create_participant_info_section(self) -> QWidget:
        """Create the participant information section using UI factory."""
        # Use UI factory to create group box
        participant_group, participant_layout = self.ui_factory.create_group_box(
            "Participant Information"
        )

        # Participant ID input with validation
        participant_layout.addWidget(self.ui_factory.create_label("Participant ID:"))

        # Create validator for participant ID
        def validate_participant_id(text: str) -> tuple[bool, str]:
            if not text.strip():
                return False, "Participant ID is required"
            import re

            if not re.match(Patterns.PARTICIPANT_ID, text):
                return False, "Format: P1-XXXX or ES-XXXX"
            return True, ""

        self.participant_id_input = self.ui_factory.create_input_field(
            Templates.PARTICIPANT_ID_PLACEHOLDER, validator=validate_participant_id
        )
        self.participant_id_input.textChanged.connect(self._on_participant_id_changed)
        participant_layout.addWidget(self.participant_id_input)

        # Device ID input
        participant_layout.addWidget(self.ui_factory.create_label("Device ID:"))

        def validate_device_id(text: str) -> tuple[bool, str]:
            if not text.strip():
                return False, "Device ID is required"
            if len(text.strip()) < 3:
                return False, "Device ID must be at least 3 characters"
            return True, ""

        self.device_id_input = self.ui_factory.create_input_field(
            Templates.DEVICE_ID_PLACEHOLDER, validator=validate_device_id
        )
        self.device_id_input.textChanged.connect(self._on_device_id_changed)
        participant_layout.addWidget(self.device_id_input)

        # Username input
        participant_layout.addWidget(self.ui_factory.create_label("Username:"))

        def validate_username(text: str) -> tuple[bool, str]:
            if not text.strip():
                return False, "Username is required"
            if len(text.strip()) < 2:
                return False, "Username must be at least 2 characters"
            return True, ""

        self.username_input = self.ui_factory.create_input_field(
            Templates.USERNAME_PLACEHOLDER, validator=validate_username
        )
        self.username_input.textChanged.connect(self._on_username_changed)
        participant_layout.addWidget(self.username_input)

        return participant_group

    def _create_data_storage_section(self) -> QWidget:
        """Create the data storage section using UI factory."""
        # Use UI factory to create group box
        data_group, data_layout = self.ui_factory.create_group_box("Data Storage")

        # Create horizontal layout for path selection
        path_layout = self.ui_factory.create_horizontal_layout()

        # Path label
        path_label = self.ui_factory.create_label("Data Path:")
        path_label.setMinimumWidth(80)
        path_layout.addWidget(path_label)

        # Path input with validation
        def validate_data_path(text: str) -> tuple[bool, str]:
            if not text.strip():
                return False, "Data path is required"
            import os

            if not os.path.isabs(text):
                return False, "Path must be absolute"
            return True, ""

        self.data_path_input = self.ui_factory.create_input_field(
            Templates.DATA_PATH_PLACEHOLDER, validator=validate_data_path
        )
        self.data_path_input.textChanged.connect(self._on_data_path_changed)
        path_layout.addWidget(self.data_path_input, stretch=1)

        # Browse button using UI factory
        self.browse_button = self.ui_factory.create_standard_button(
            "Browse...", callback=self._browse_data_path
        )
        self.browse_button.setMinimumWidth(80)
        path_layout.addWidget(self.browse_button)

        data_layout.addLayout(path_layout)
        return data_group

    def _create_validation_section(self, layout) -> None:
        """Create the validation feedback section using UI factory."""
        self.validation_label = self.ui_factory.create_status_label(
            "", status_type="error"
        )
        self.validation_label.setStyleSheet(
            f"color: {self.config.error_color}; font-weight: bold; padding: 8px; "
            f"border-radius: {self.config.border_radius}px; background-color: {self.config.error_bg};"
        )
        self.validation_label.setVisible(False)
        layout.addWidget(self.validation_label)

    def _create_button_section(self, layout) -> None:
        """Create the button section using UI factory."""
        # Use UI factory to create continue button with layout
        button_layout, self.next_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text="Continue to Next Step"
        )

        layout.addLayout(button_layout)

    @handle_step_error
    def _load_existing_values(self) -> None:
        """Load existing values from state with error handling."""
        try:
            self.participant_id_input.setText(
                self.state.get_user_input("participant_id", "")
            )
            self.device_id_input.setText(self.state.get_user_input("device_id", ""))
            self.username_input.setText(self.state.get_user_input("username", ""))
            self.data_path_input.setText(self.state.get_user_input("data_path", ""))

            self.logger.info("Loaded existing values from state")

        except Exception as e:
            self.logger.error(f"Error loading existing values: {e}")
            raise FlashTVError(
                f"Failed to load existing values: {e}",
                ErrorType.STATE_ERROR,
                recovery_action="Clear form and start fresh",
            )

    @handle_step_error
    def _on_participant_id_changed(self, text: str) -> None:
        """Handle participant ID input changes with state persistence."""
        self.state.set_user_input("participant_id", text)
        if self.state_manager:
            self.state_manager.save_state(self.state)
        self._validate_and_update_ui()

    @handle_step_error
    def _on_device_id_changed(self, text: str) -> None:
        """Handle device ID input changes with state persistence."""
        self.state.set_user_input("device_id", text)
        if self.state_manager:
            self.state_manager.save_state(self.state)
        self._validate_and_update_ui()

    @handle_step_error
    def _on_username_changed(self, text: str) -> None:
        """Handle username input changes with state persistence."""
        self.state.set_user_input("username", text)
        if self.state_manager:
            self.state_manager.save_state(self.state)
        self._validate_and_update_ui()

    @handle_step_error
    def _on_data_path_changed(self, text: str) -> None:
        """Handle data path input changes with state persistence."""
        self.state.set_user_input("data_path", text)
        if self.state_manager:
            self.state_manager.save_state(self.state)
        self._validate_and_update_ui()

    @handle_step_error
    def _browse_data_path(self, checked: bool = False) -> None:
        """Open file dialog to select data path with error handling."""
        try:
            current_path = self.data_path_input.text()
            directory = QFileDialog.getExistingDirectory(
                self, Messages.SELECT_DATA_DIRECTORY, current_path
            )

            if directory:
                self.data_path_input.setText(directory)
                self.logger.info(f"Selected data directory: {directory}")

        except Exception as e:
            self.logger.error(f"Error browsing for data path: {e}")
            raise FlashTVError(
                f"Failed to browse for data path: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try typing the path manually",
            )

    @handle_step_error
    def _validate_and_update_ui(self) -> None:
        """Validate inputs and update UI state with comprehensive validation."""
        try:
            is_valid, errors = self.validate_inputs()
            required_fields = ["participant_id", "device_id", "username", "data_path"]
            all_filled = all(
                self.state.get_user_input(field, "").strip()
                for field in required_fields
            )

            if errors:
                self._show_validation_error("\n".join(errors))
                self.logger.warning(f"Validation errors: {errors}")
            elif not all_filled:
                self._show_validation_error(Messages.FILL_ALL_FIELDS)
            else:
                self._hide_validation_error()
                self.logger.info("All fields validated successfully")

            self._update_continue_button(is_valid and all_filled)
            self.update_status(StepStatus.USER_ACTION_REQUIRED)

        except Exception as e:
            self.logger.error(f"Error during validation: {e}")
            self._show_validation_error(f"Validation error: {e}")
            self._update_continue_button(False)

    def _show_validation_error(self, message: str) -> None:
        """Show validation error message using status label."""
        self.validation_label.setText(message)
        self.validation_label.setVisible(True)

    def _hide_validation_error(self) -> None:
        """Hide validation error message."""
        self.validation_label.setVisible(False)

    def _update_continue_button(self, enabled: bool) -> None:
        """Update the continue button state with logging."""
        self.next_button.setEnabled(enabled)
        self.logger.debug(f"Continue button enabled: {enabled}")

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with comprehensive validation."""
        try:
            is_valid, errors = self.validate_inputs()

            if is_valid and self.next_button.isEnabled():
                # Log completion
                self.logger.info(
                    f"Participant setup completed for ID: {self.state.get_user_input('participant_id')}"
                )

                # Update status to completed
                self.update_status(StepStatus.COMPLETED)

                # Persist final state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                # Request next step
                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but validation failed")
                self._validate_and_update_ui()

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            self.update_status(StepStatus.FAILED)
            raise FlashTVError(
                f"Failed to complete step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Check all fields and try again",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the participant setup step with enhanced logic."""
        super().activate_step()

        # Validate and update UI
        self._validate_and_update_ui()

        # Focus first empty field for better UX
        self._focus_first_empty_field()

        self.logger.info("Participant setup step activated")

    def _focus_first_empty_field(self) -> None:
        """Focus on the first empty required field with logging."""
        input_fields = [
            (self.participant_id_input, "participant_id"),
            (self.device_id_input, "device_id"),
            (self.username_input, "username"),
            (self.data_path_input, "data_path"),
        ]

        for field_input, field_name in input_fields:
            if not field_input.text().strip():
                field_input.setFocus()
                self.logger.debug(f"Focused on empty field: {field_name}")
                break

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()

        # Check if state needs to be persisted
        if self.state_manager and hasattr(self, "_needs_state_save"):
            try:
                self.state_manager.save_state(self.state)
                self._needs_state_save = False
            except Exception as e:
                self.logger.error(f"Error saving state during UI update: {e}")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Participant setup step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
