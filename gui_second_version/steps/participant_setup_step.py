"""Participant setup step implementation using new framework patterns."""

from __future__ import annotations

import os
import re
import subprocess

from config.messages import MESSAGES
from config.participant_contract import (
    build_participant_full_id,
    get_participant_data_dir,
)
from config.validation_patterns import VALIDATION
from core import WizardStep
from core.exceptions import ErrorType, FlashTVError, handle_step_error
from models import StepStatus
from models.state_keys import UserInputKey
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget
from utils.identity_detection import (
    IdentityDetectionResult,
    derive_device_id_from_username,
    detect_flash_tv_identity,
)


class ParticipantSetupStep(WizardStep):
    """Step 1: Participant and Device Setup with auto-detection.

    This step simplifies the setup process by:
    1. Auto-detecting device ID and username from /home/flashsysXXX folders
    2. Only requiring user to input participant ID (P1-XXXX or ES-XXXX format)
    3. Auto-generating data path as /home/{username}/data/{participant_id}{device_id}_data
    4. Validating participant ID format and auto-detection success

    The UI shows:
    - Single participant ID input field (only user input needed)
    - Read-only auto-detected device information display
    - Dynamic data path preview that updates with participant ID input
    - Error messages if auto-detection fails
    """

    # Signal emitted when device detection completes
    device_detected = Signal(str, str, str)  # device_id, username, data_path

    def __init__(self, *args, **kwargs) -> None:
        # Initialize auto-detected values BEFORE calling super().__init__()
        # because parent's __init__ calls _setup_ui() which calls create_content_widget()
        self._device_id: str | None = None
        self._username: str | None = None
        self._detection_error: str | None = None
        self._detection_details: str = ""
        self._manual_username: str = ""
        self._manual_device_id: str = ""

        # Perform auto-detection BEFORE parent initialization
        self._auto_detect_device_info()

        # Now call parent's __init__ which will set up the UI
        super().__init__(*args, **kwargs)

    def _auto_detect_device_info(self) -> None:
        try:
            detection: IdentityDetectionResult = detect_flash_tv_identity()
            self._detection_details = detection.reason or ""

            if detection.success:
                self._username = detection.username
                self._device_id = detection.device_id
                self._detection_error = None
            else:
                self._username = None
                self._device_id = None
                self._detection_error = detection.fallback_reason or detection.reason

        except Exception as e:
            self._username = None
            self._device_id = None
            self._detection_details = ""
            self._detection_error = f"Error during auto-detection: {e}"

    def _get_effective_identity(self) -> tuple[str | None, str | None]:
        username = self._username or self._manual_username.strip() or None
        manual_device_id = self._manual_device_id.strip()
        device_id = self._device_id or (
            manual_device_id if self._is_valid_manual_device_id(manual_device_id) else None
        )
        return username, device_id

    def _is_valid_manual_device_id(self, device_id: str) -> bool:
        return bool(re.fullmatch(r"\d{3}", device_id.strip()))

    def _get_manual_identity_message(self) -> str:
        manual_username = self._manual_username.strip()
        manual_device_id = self._manual_device_id.strip()

        if not manual_username:
            return (
                "Fallback: enter the FLASH-TV Linux username. If it looks like flashsys###, "
                "the device ID will be derived automatically."
            )

        derived_device_id = derive_device_id_from_username(manual_username)
        if derived_device_id:
            return (
                f"Username '{manual_username}' looks valid. Device ID '{derived_device_id}' "
                "was derived automatically from the username suffix."
            )

        if not manual_device_id:
            return (
                "That username does not end in digits, so the device ID could not be derived. "
                "Enter the device ID explicitly below."
            )

        if not self._is_valid_manual_device_id(manual_device_id):
            return "Enter the 3-digit device ID using numbers only (for example 007)."

        return f"Using manual fallback values: username '{manual_username}' and device ID '{manual_device_id}'."

    def create_content_widget(self) -> QWidget:
        """Create the participant setup UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        participant_section = self._create_participant_info_section()
        detection_section = self._create_detection_info_section()

        sections_layout = self.ui_factory.create_horizontal_section(
            participant_section, detection_section, spacing=12
        )
        main_layout.addLayout(
            sections_layout
        )  # No stretch - sections take natural height

        self._create_validation_section(main_layout)

        main_layout.addStretch()  # Push button to bottom

        self._create_button_section(main_layout)

        self._load_existing_values()

        return content

    def _create_participant_info_section(self) -> QWidget:
        """Create the participant information section - only requires participant ID input.

        This section is simplified to only collect the participant ID, as device_id and username
        are now auto-detected. The UI shows only the single required input field.
        """
        # Use UI factory to create group box
        participant_group, participant_layout = self.ui_factory.create_group_box(
            "Participant Information"
        )

        participant_id_label = self.ui_factory.create_label("Participant ID:")
        participant_id_label.setStyleSheet("font-weight: bold;")
        participant_layout.addWidget(participant_id_label)

        def validate_participant_id(text: str) -> tuple[bool, str]:
            if not text.strip():
                return False, "Participant ID is required"

            if not re.match(VALIDATION.PARTICIPANT_ID, text):
                return (
                    False,
                    "Format must be P1-XXXX or ES-XXXX (e.g., P1-0123, ES-0456)",
                )
            return True, ""

        self.participant_id_input = self.ui_factory.create_input_field(
            MESSAGES.Placeholders.PARTICIPANT_ID, validator=validate_participant_id
        )
        self.participant_id_input.textChanged.connect(self._on_participant_id_changed)
        participant_layout.addWidget(self.participant_id_input)

        participant_layout.addSpacing(8)

        sudo_password_label = self.ui_factory.create_label("Sudo Password:")
        sudo_password_label.setStyleSheet("font-weight: bold;")
        participant_layout.addWidget(sudo_password_label)

        self.sudo_password_input = self.ui_factory.create_input_field(
            "Enter sudo password for system operations..."
        )
        self.sudo_password_input.setEchoMode(self.sudo_password_input.EchoMode.Password)
        self.sudo_password_input.textChanged.connect(self._on_sudo_password_changed)
        participant_layout.addWidget(self.sudo_password_input)

        # Sudo password validation status label
        self.sudo_validation_label = self.ui_factory.create_status_label(
            "", status_type="info"
        )
        self.sudo_validation_label.setVisible(False)
        participant_layout.addWidget(self.sudo_validation_label)

        # Track sudo validation state
        self._sudo_validated = False
        self._sudo_validation_in_progress = False

        participant_layout.addStretch()

        return participant_group

    def _create_detection_info_section(self) -> QWidget:
        """Create the auto-detection information section showing read-only detected values."""
        # Use UI factory to create group box
        detection_group, detection_layout = self.ui_factory.create_group_box(
            "Auto-Detected System Information"
        )

        if self._detection_error:
            error_label = self.ui_factory.create_status_label(
                "❌ Auto-Detection Failed", status_type="error"
            )
            detection_layout.addWidget(error_label)

            error_detail = self.ui_factory.create_label(self._detection_error)
            error_detail.setStyleSheet(
                "color: #666; padding: 8px; background-color: #ffebee; border-radius: 4px;"
            )
            error_detail.setWordWrap(True)
            detection_layout.addWidget(error_detail)

            self.manual_username_label = self.ui_factory.create_label(
                "Fallback Username:"
            )
            self.manual_username_label.setStyleSheet("font-weight: bold;")
            detection_layout.addWidget(self.manual_username_label)

            self.manual_username_input = self.ui_factory.create_input_field(
                "Enter the FLASH-TV Linux username (for example flashsys007)"
            )
            self.manual_username_input.textChanged.connect(
                self._on_manual_username_changed
            )
            detection_layout.addWidget(self.manual_username_input)

            self.manual_device_label = self.ui_factory.create_label(
                "Fallback Device ID:"
            )
            self.manual_device_label.setStyleSheet("font-weight: bold;")
            detection_layout.addWidget(self.manual_device_label)

            self.manual_device_input = self.ui_factory.create_input_field(
                "Only needed if the username does not end with digits"
            )
            self.manual_device_input.textChanged.connect(
                self._on_manual_device_id_changed
            )
            detection_layout.addWidget(self.manual_device_input)

            self.manual_device_label.setVisible(False)
            self.manual_device_input.setVisible(False)

            self.manual_identity_status = self.ui_factory.create_label(
                self._get_manual_identity_message()
            )
            self.manual_identity_status.setWordWrap(True)
            self.manual_identity_status.setStyleSheet(
                "color: #444; padding: 8px; background-color: #fff8e1; border-radius: 4px;"
            )
            detection_layout.addWidget(self.manual_identity_status)
        else:
            success_header = self.ui_factory.create_status_label(
                "✅ Auto-Detection Successful", status_type="success"
            )
            detection_layout.addWidget(success_header)

            if self._detection_details:
                detection_note = self.ui_factory.create_label(self._detection_details)
                detection_note.setWordWrap(True)
                detection_note.setStyleSheet(
                    "color: #555; padding: 6px; background-color: #f5f5f5; border-radius: 4px;"
                )
                detection_layout.addWidget(detection_note)

            device_id_label = self.ui_factory.create_label(
                f"Device ID: {self._device_id}"
            )
            device_id_label.setStyleSheet(
                "font-weight: bold; color: #2e7d32; padding: 4px; background-color: #e8f5e8; border-radius: 4px;"
            )
            detection_layout.addWidget(device_id_label)

            username_label = self.ui_factory.create_label(f"Username: {self._username}")
            username_label.setStyleSheet(
                "font-weight: bold; color: #2e7d32; padding: 4px; background-color: #e8f5e8; border-radius: 4px;"
            )
            detection_layout.addWidget(username_label)

            if self._device_id and self._username:
                participant_id = self.state.get_user_input(
                    UserInputKey.PARTICIPANT_ID, ""
                ).strip()
                if participant_id and self._device_id:
                    data_path = str(
                        get_participant_data_dir(
                            self._username, participant_id, self._device_id
                        )
                    )
                elif self._device_id:
                    data_path = str(
                        get_participant_data_dir(
                            self._username, "[PARTICIPANT_ID]", self._device_id
                        )
                    )
                else:
                    data_path = (
                        f"/home/{self._username}/data/[PARTICIPANT_ID][DEVICE_ID]_data"
                    )

                self.data_path_label = self.ui_factory.create_label(
                    f"Data Path: {data_path}"
                )
                self.data_path_label.setStyleSheet(
                    "font-weight: bold; color: #1976d2; padding: 4px; background-color: #e3f2fd; border-radius: 4px;"
                )
                detection_layout.addWidget(self.data_path_label)

                info_note = self.ui_factory.create_label(
                    "* Data directory will be created when you continue"
                )
                info_note.setStyleSheet("color: #666; font-style: italic;")
                detection_layout.addWidget(info_note)

        return detection_group

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
            callback=self._on_continue_clicked, text=MESSAGES.UI.CONTINUE
        )

        layout.addLayout(button_layout)

    @handle_step_error
    def _load_existing_values(self) -> None:
        """Load existing values from state with error handling."""
        try:
            self.participant_id_input.setText(
                self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            )

            existing_password = self.state.get_user_input(
                UserInputKey.SUDO_PASSWORD, ""
            )
            self.sudo_password_input.setText(existing_password)

            if self._detection_error:
                self._manual_username = self.state.get_user_input(
                    UserInputKey.USERNAME, ""
                ).strip()
                self._manual_device_id = self.state.get_user_input(
                    UserInputKey.DEVICE_ID, ""
                ).strip()

                if hasattr(self, "manual_username_input") and self._manual_username:
                    self.manual_username_input.setText(self._manual_username)
                if hasattr(self, "manual_device_input") and self._manual_device_id:
                    self.manual_device_input.setText(self._manual_device_id)

            # Reset validation state when loading - password needs to be re-validated
            self._sudo_validated = False
            if existing_password:
                self.sudo_validation_label.setText(
                    "⏳ Password loaded. It will be checked when you continue."
                )
                self.sudo_validation_label.setStyleSheet(
                    "color: #666; font-style: italic; padding: 4px;"
                )
            self.sudo_validation_label.setVisible(True)

            effective_username, effective_device_id = self._get_effective_identity()
            if effective_device_id and effective_username:
                self.state.set_user_input(UserInputKey.DEVICE_ID, effective_device_id)
                self.state.set_user_input(UserInputKey.USERNAME, effective_username)

                participant_id = self.state.get_user_input(
                    UserInputKey.PARTICIPANT_ID, ""
                )
                if participant_id and effective_device_id:
                    data_path = str(
                        get_participant_data_dir(
                            effective_username, participant_id, effective_device_id
                        )
                    )
                    self.state.set_user_input(UserInputKey.DATA_PATH, data_path)
            else:
                self.state.remove_user_input(UserInputKey.DEVICE_ID)
                self.state.remove_user_input(UserInputKey.USERNAME)
                self.state.remove_user_input(UserInputKey.DATA_PATH)

            self.logger.info("Loaded existing values from state")

        except Exception as e:
            self.logger.error(f"Error loading existing values: {e}")
            raise FlashTVError(
                f"Failed to load existing values: {e}",
                ErrorType.VALIDATION_ERROR,
                recovery_action="Clear form and start fresh",
            )

    @handle_step_error
    def _on_participant_id_changed(self, text: str) -> None:
        """Handle participant ID input changes with automatic data path generation.

        Updates the auto-generated data path dynamically as user types participant ID.
        Format: /home/{username}/data/{participant_id}{device_id}_data
        """
        participant_id = text.strip()
        self.state.set_user_input(UserInputKey.PARTICIPANT_ID, participant_id)

        effective_username, effective_device_id = self._get_effective_identity()
        if effective_device_id and effective_username:
            self.state.set_user_input(UserInputKey.USERNAME, effective_username)
            self.state.set_user_input(UserInputKey.DEVICE_ID, effective_device_id)
            if participant_id:
                data_path = str(
                    get_participant_data_dir(
                        effective_username, participant_id, effective_device_id
                    )
                )
                self.state.set_user_input(UserInputKey.DATA_PATH, data_path)

                if hasattr(self, "data_path_label"):
                    self.data_path_label.setText(f"Data Path: {data_path}")
                    self.data_path_label.setStyleSheet(
                        "font-weight: bold; color: #1976d2; padding: 4px; "
                        "background-color: #e3f2fd; border-radius: 4px;"
                    )
            else:
                placeholder_path = str(
                    get_participant_data_dir(
                        effective_username, "[PARTICIPANT_ID]", effective_device_id
                    )
                )
                if hasattr(self, "data_path_label"):
                    self.data_path_label.setText(f"Data Path: {placeholder_path}")
                    self.data_path_label.setStyleSheet(
                        "font-weight: normal; color: #666; padding: 4px; "
                        "background-color: #f5f5f5; border-radius: 4px; font-style: italic;"
                    )
                self.state.set_user_input(UserInputKey.DATA_PATH, "")
        else:
            self.state.remove_user_input(UserInputKey.USERNAME)
            self.state.remove_user_input(UserInputKey.DEVICE_ID)
            self.state.remove_user_input(UserInputKey.DATA_PATH)

        if self.state_manager:
            self.state_manager.save_state(self.state)
        self._validate_and_update_ui()

    @handle_step_error
    def _on_manual_username_changed(self, text: str) -> None:
        self._manual_username = text.strip()
        derived_device_id = derive_device_id_from_username(self._manual_username)

        if derived_device_id:
            self._manual_device_id = derived_device_id
            self.manual_device_input.setText(derived_device_id)
            self.manual_device_label.setVisible(False)
            self.manual_device_input.setVisible(False)
        else:
            if self.manual_device_input.text().strip() == self._manual_device_id:
                self.manual_device_input.clear()
            self._manual_device_id = self.manual_device_input.text().strip()
            self.manual_device_label.setVisible(bool(self._manual_username))
            self.manual_device_input.setVisible(bool(self._manual_username))

        self.manual_identity_status.setText(self._get_manual_identity_message())

        effective_username, effective_device_id = self._get_effective_identity()
        if effective_username:
            self.state.set_user_input(UserInputKey.USERNAME, effective_username)
        else:
            self.state.remove_user_input(UserInputKey.USERNAME)
        if effective_device_id:
            self.state.set_user_input(UserInputKey.DEVICE_ID, effective_device_id)
        else:
            self.state.remove_user_input(UserInputKey.DEVICE_ID)

        self._on_participant_id_changed(self.participant_id_input.text())

    @handle_step_error
    def _on_manual_device_id_changed(self, text: str) -> None:
        if derive_device_id_from_username(self._manual_username):
            return

        self._manual_device_id = text.strip()
        self.manual_identity_status.setText(self._get_manual_identity_message())

        effective_username, effective_device_id = self._get_effective_identity()
        if effective_username:
            self.state.set_user_input(UserInputKey.USERNAME, effective_username)
        else:
            self.state.remove_user_input(UserInputKey.USERNAME)
        if effective_device_id:
            self.state.set_user_input(UserInputKey.DEVICE_ID, effective_device_id)
        else:
            self.state.remove_user_input(UserInputKey.DEVICE_ID)

        self._on_participant_id_changed(self.participant_id_input.text())

    @handle_step_error
    def _on_sudo_password_changed(self, text: str) -> None:
        """Handle sudo password input changes."""
        sudo_password = text.strip()
        self.state.set_user_input(UserInputKey.SUDO_PASSWORD, sudo_password)

        # Reset validation state when password changes
        self._sudo_validated = False

        # Update validation label to show pending state
        if sudo_password:
            self.sudo_validation_label.setText(
                "⏳ Password entered. It will be checked when you continue."
            )
            self.sudo_validation_label.setStyleSheet(
                "color: #666; font-style: italic; padding: 4px;"
            )
            self.sudo_validation_label.setVisible(True)
        else:
            self.sudo_validation_label.setVisible(False)

        # Persist state
        if self.state_manager:
            self.state_manager.save_state(self.state)
        self._validate_and_update_ui()

    def _validate_sudo_password(self, password: str) -> tuple[bool, str]:
        """Validate sudo password by attempting a test sudo command.

        Args:
            password: The sudo password to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        if not password:
            return (
                False,
                "Enter the sudo password to continue. If you do not know it, ask the study technician for help.",
            )

        try:
            self.logger.info("Validating sudo password...")

            subprocess.run(
                ["sudo", "-k"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )

            process = subprocess.Popen(
                ["sudo", "-S", "-k", "-v"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Send password followed by newline
            stdout, stderr = process.communicate(input=password + "\n", timeout=10)

            if process.returncode == 0:
                self.logger.info("Sudo password validated successfully")
                return True, ""
            else:
                # Check for common error messages
                error_lower = stderr.lower() if stderr else ""
                if "incorrect password" in error_lower or "sorry" in error_lower:
                    self.logger.warning(
                        "Sudo password validation failed: incorrect password"
                    )
                    return (
                        False,
                        "That password was not accepted. Re-enter it and try again. If it keeps failing, ask the study technician for help.",
                    )
                elif "not in the sudoers file" in error_lower:
                    self.logger.warning(
                        "Sudo password validation failed: user not in sudoers"
                    )
                    return (
                        False,
                        "This account cannot perform setup tasks. Sign in with the correct setup account or ask the study technician for help.",
                    )
                else:
                    self.logger.warning(f"Sudo password validation failed: {stderr}")
                    return (
                        False,
                        "The password could not be checked right now. Try again once. If it still fails, ask the study technician for help.",
                    )

        except subprocess.TimeoutExpired:
            self.logger.error("Sudo password validation timed out")
            return (
                False,
                "Password check took too long. Try again once. If it keeps timing out, ask the study technician for help.",
            )
        except FileNotFoundError:
            self.logger.error("sudo command not found")
            return (
                False,
                "This device is missing a required setup tool. Please ask technical support for help.",
            )
        except Exception as e:
            self.logger.error(f"Error validating sudo password: {e}")
            return (
                False,
                "The password could not be checked because of an unexpected problem. Try again once, then ask technical support for help if needed.",
            )

    @handle_step_error
    def _validate_and_update_ui(self) -> None:
        """Validate inputs and update UI state.

        Simplified validation focusing on:
        - Participant ID format validation
        - Auto-detection success
        """
        try:
            is_valid, errors = self.validate_inputs()

            participant_id = self.state.get_user_input(
                UserInputKey.PARTICIPANT_ID, ""
            ).strip()
            sudo_password = self.state.get_user_input(
                UserInputKey.SUDO_PASSWORD, ""
            ).strip()
            effective_username, effective_device_id = self._get_effective_identity()
            has_detection = bool(effective_device_id and effective_username)

            all_requirements_met = bool(
                participant_id and sudo_password and has_detection and is_valid
            )

            if errors:
                error_message = "\n".join(errors)
                self._show_validation_error(error_message)
                self.logger.warning(f"Validation failed: {errors}")
            else:
                self._hide_validation_error()
                if all_requirements_met:
                    self.logger.info(
                        f"Validation successful - Participant: {participant_id}, Device: {effective_device_id}, User: {effective_username}"
                    )

            self._update_continue_button(all_requirements_met)
            self.update_status(StepStatus.USER_ACTION_REQUIRED)

        except Exception as e:
            self.logger.error(
                f"Error during validation and UI update: {e}", exc_info=True
            )
            self._show_validation_error(
                "This step could not be checked because of an unexpected problem. Try again once. If it still fails, ask technical support for help."
            )
            self._update_continue_button(False)
            self.update_status(StepStatus.FAILED)

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
        """Handle continue button click with comprehensive validation including sudo password test."""
        try:
            is_valid, errors = self.validate_inputs()
            participant_id = self.state.get_user_input(
                UserInputKey.PARTICIPANT_ID, ""
            ).strip()
            sudo_password = self.state.get_user_input(
                UserInputKey.SUDO_PASSWORD, ""
            ).strip()

            if is_valid and self.next_button.isEnabled() and participant_id:
                effective_username, effective_device_id = self._get_effective_identity()
                if not effective_username or not effective_device_id:
                    self.logger.warning(
                        "Continue clicked without a usable username/device ID"
                    )
                    self._validate_and_update_ui()
                    return

                # Validate sudo password if not already validated
                if not self._sudo_validated:
                    self.sudo_validation_label.setText("🔄 Validating sudo password...")
                    self.sudo_validation_label.setStyleSheet(
                        "color: #1976d2; font-weight: bold; padding: 4px;"
                    )
                    self.sudo_validation_label.setVisible(True)

                    # Force UI update to show validation message
                    from PySide6.QtWidgets import QApplication

                    QApplication.processEvents()

                    # Validate the sudo password
                    password_valid, password_error = self._validate_sudo_password(
                        sudo_password
                    )

                    if not password_valid:
                        self.sudo_validation_label.setText(f"❌ {password_error}")
                        self.sudo_validation_label.setStyleSheet(
                            "color: #c62828; font-weight: bold; padding: 4px; "
                            "background-color: #ffebee; border-radius: 4px;"
                        )
                        self.sudo_validation_label.setVisible(True)
                        self.logger.warning(
                            f"Sudo password validation failed: {password_error}"
                        )
                        return

                    # Password is valid
                    self._sudo_validated = True
                    self.sudo_validation_label.setText("✅ Sudo password verified")
                    self.sudo_validation_label.setStyleSheet(
                        "color: #2e7d32; font-weight: bold; padding: 4px; "
                        "background-color: #e8f5e9; border-radius: 4px;"
                    )
                    self.sudo_validation_label.setVisible(True)
                    self.logger.info("Sudo password validated successfully")

                data_path = ""
                if effective_device_id:
                    self.state.set_user_input(UserInputKey.USERNAME, effective_username)
                    self.state.set_user_input(
                        UserInputKey.DEVICE_ID, effective_device_id
                    )
                    full_participant_id = build_participant_full_id(
                        participant_id, effective_device_id
                    )
                    data_path = str(
                        get_participant_data_dir(
                            effective_username, participant_id, effective_device_id
                        )
                    )
                    self.state.set_user_input(UserInputKey.DATA_PATH, data_path)

                    os.makedirs(data_path, exist_ok=True)
                    self.logger.info(f"Created data directory: {data_path}")

                    # Configure event store with participant info for audit logging
                    self.event_store.configure(
                        participant_id=full_participant_id,
                        data_path=data_path,
                        auto_save=True,
                    )
                    self.logger.info("Event store configured for audit logging")

                self.device_detected.emit(
                    effective_device_id, effective_username, data_path
                )

                self.logger.info(
                    f"Participant setup completed - ID: {participant_id}, "
                    f"Device: {effective_device_id}, Username: {effective_username}, "
                    f"Data Path: {data_path}"
                )

                self.update_status(StepStatus.COMPLETED)

                if self.state_manager:
                    self.state_manager.save_state(self.state)

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
                recovery_action="Check the highlighted fields and try again. If the step still will not continue, ask the study technician for help.",
            )

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate participant_id format, sudo password, and auto-detection success.

        Validates:
        1. Participant ID format (P1-XXXX or ES-XXXX)
        2. Sudo password is provided
        3. Auto-detection succeeded (device_id and username available)

        Returns:
            tuple: (is_valid, list_of_error_messages)
        """
        errors = []
        has_detection_error = False

        try:
            # 1. Validate participant ID format
            participant_id = self.state.get_user_input(
                UserInputKey.PARTICIPANT_ID, ""
            ).strip()
            if not participant_id:
                errors.append(
                    "Enter the participant ID to continue. If you are unsure which ID to use, ask the study technician before continuing."
                )
            elif not re.match(VALIDATION.PARTICIPANT_ID, participant_id):
                errors.append(
                    "The participant ID format is not valid. Use P1-XXXX or ES-XXXX, then try again. If you are unsure, ask the study technician."
                )

            # 2. Validate sudo password
            sudo_password = self.state.get_user_input(
                UserInputKey.SUDO_PASSWORD, ""
            ).strip()
            if not sudo_password:
                errors.append(
                    "Enter the sudo password to continue. If you do not know it, ask the study technician for help."
                )

            effective_username, effective_device_id = self._get_effective_identity()
            has_detection_error = not (effective_device_id and effective_username)

            if self._detection_error and not effective_username:
                errors.append(
                    "The device account was not found automatically. Use the fallback username field on the right. If that still does not work, ask the study technician for help."
                )
            elif self._manual_username and not derive_device_id_from_username(
                self._manual_username
            ):
                manual_device_id = self._manual_device_id.strip()
                if not manual_device_id:
                    errors.append(
                        "The device ID is still missing. Enter a username ending in digits or fill in the fallback device ID. If you are unsure, ask the study technician."
                    )
                elif not self._is_valid_manual_device_id(manual_device_id):
                    errors.append(
                        "Enter the 3-digit device ID using numbers only (for example 007). If you are unsure, ask the study technician."
                    )
            elif effective_username and not effective_device_id:
                errors.append(
                    "The device ID is still missing. Enter a username ending in digits or fill in the fallback device ID. If you are unsure, ask the study technician."
                )

            if effective_username:
                home_path = f"/home/{effective_username}"
                if not os.path.isdir(home_path):
                    errors.append(
                        "The selected setup account is not available on this device. Check the fallback username/device ID entries. If they look correct and this still fails, ask technical support for help."
                    )

        except Exception as e:
            errors.append(
                "This step could not be checked because of an unexpected problem. Try again once. If it still fails, ask technical support for help."
            )
            self.logger.error(f"Exception during input validation: {e}", exc_info=True)

        # is_valid requires no errors AND successful auto-detection
        is_valid = len(errors) == 0 and not has_detection_error
        return is_valid, errors

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the participant setup step with enhanced logic."""
        super().activate_step()

        # Validate and update UI
        self._validate_and_update_ui()

        # Focus on participant ID input (only user-editable field)
        if hasattr(self, "participant_id_input"):
            self.participant_id_input.setFocus()
            self.logger.debug("Focused on participant ID input")

        self.logger.info("Participant setup step activated")

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()

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

    def get_device_info(self) -> tuple[str | None, str | None, str | None]:
        """Get the auto-detected device information.

        Returns:
            tuple: (device_id, username, detection_error)
                - device_id: Detected device ID (e.g., '001', '123') or None
                - username: Detected username (e.g., 'flashsys001') or None
                - detection_error: Error message if detection failed, None if successful
        """
        return self._device_id, self._username, self._detection_error

    def is_auto_detection_successful(self) -> bool:
        """Check if auto-detection was successful.

        Returns:
            bool: True if device_id and username were successfully detected, False otherwise
        """
        return bool(self._device_id and self._username and not self._detection_error)

    def get_generated_data_path(self, participant_id: str | None = None) -> str:
        """Get the auto-generated data path for a participant.

        Args:
            participant_id: Participant ID to use, or None to use current state value

        Returns:
            str: Generated data path or empty string if auto-detection failed
        """
        effective_username, effective_device_id = self._get_effective_identity()
        if not (effective_username and effective_device_id):
            return ""

        if participant_id is None:
            participant_id = self.state.get_user_input(
                UserInputKey.PARTICIPANT_ID, ""
            ).strip()

        if not participant_id:
            return ""

        if effective_device_id:
            return str(
                get_participant_data_dir(
                    effective_username, participant_id, effective_device_id
                )
            )
        return f"/home/{effective_username}/data/{participant_id}_data"
