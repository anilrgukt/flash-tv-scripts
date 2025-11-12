"""Participant setup step implementation using new framework patterns."""

from __future__ import annotations

import os
import glob
import re
from typing import Tuple, Optional

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal

from constants import Templates, Messages, Patterns
from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus


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
    device_detected = pyqtSignal(str, str, str)  # device_id, username, data_path

    def __init__(self, *args, **kwargs) -> None:
        # Initialize auto-detected values BEFORE calling super().__init__()
        # because parent's __init__ calls _setup_ui() which calls create_content_widget()
        self._device_id: Optional[str] = None
        self._username: Optional[str] = None
        self._detection_error: Optional[str] = None
        
        # Perform auto-detection BEFORE parent initialization
        self._auto_detect_device_info()
        
        # Now call parent's __init__ which will set up the UI
        super().__init__(*args, **kwargs)

    def _auto_detect_device_info(self) -> None:
        """Auto-detect device ID and username.
        
        Scans for /home/flashsysXXX folders using glob, extracts device ID (XXX) and username (flashsysXXX),
        checks $USER environment variable as validation, returns tuple of (device_id, username, success).
        """
        try:
            # Method 1: Scan for /home/flashsysXXX folders using glob
            flashsys_pattern = "/home/flashsys[0-9]*"
            matching_folders = glob.glob(flashsys_pattern)
            
            # Filter to only valid flashsys directories with numeric suffixes
            valid_folders = []
            for folder_path in matching_folders:
                if os.path.isdir(folder_path):
                    basename = os.path.basename(folder_path)
                    # Match exactly flashsys followed by digits
                    if re.match(r'^flashsys\d+$', basename):
                        valid_folders.append(folder_path)
            
            detected_from_folders = None
            if valid_folders:
                # Use the first valid folder found
                folder_path = valid_folders[0]
                username_from_folder = os.path.basename(folder_path)
                # Extract device ID (digits after 'flashsys')
                device_id_match = re.search(r'^flashsys(\d+)$', username_from_folder)
                if device_id_match:
                    device_id = device_id_match.group(1)
                    detected_from_folders = (device_id, username_from_folder)
                    # Can't use self.logger here as it's not initialized yet
                    print(f"Auto-detected from folder scan: device_id={device_id}, username={username_from_folder}")
            
            # Method 2: Check $USER environment variable as validation
            current_user = os.environ.get("USER", "")
            detected_from_user = None
            
            if current_user and current_user != "root":
                user_match = re.match(r'^flashsys(\d+)$', current_user)
                if user_match:
                    device_id = user_match.group(1)
                    detected_from_user = (device_id, current_user)
                    # Can't use self.logger here as it's not initialized yet
                    print(f"Validated from $USER environment: device_id={device_id}, username={current_user}")
            
            # Choose detection method with validation
            if detected_from_folders and detected_from_user:
                # Both methods worked - validate they match
                folder_device_id, folder_username = detected_from_folders
                user_device_id, user_username = detected_from_user
                
                if folder_device_id == user_device_id and folder_username == user_username:
                    self._device_id = folder_device_id
                    self._username = folder_username
                    print(f"Auto-detection successful: Both methods agree on device_id={self._device_id}, username={self._username}")
                else:
                    print(f"WARNING: Detection methods disagree - folder: {detected_from_folders}, $USER: {detected_from_user}")
                    # Use folder method as primary since it scans actual filesystem
                    self._device_id, self._username = detected_from_folders
                    print(f"Using folder detection as primary: device_id={self._device_id}, username={self._username}")
                    
            elif detected_from_folders:
                # Only folder scanning worked (most reliable method)
                self._device_id, self._username = detected_from_folders
                print(f"Auto-detection via folder scan: device_id={self._device_id}, username={self._username}")
                
            elif detected_from_user:
                # Only user environment worked (verify home directory exists)
                device_id, username = detected_from_user
                expected_home = f"/home/{username}"
                if os.path.isdir(expected_home):
                    self._device_id, self._username = detected_from_user
                    print(f"Auto-detection via $USER (verified home exists): device_id={self._device_id}, username={self._username}")
                else:
                    self._detection_error = f"$USER is {username} but /home/{username} directory does not exist"
                    print(f"ERROR: {self._detection_error}")
                    
            else:
                # No detection method succeeded
                self._detection_error = (
                    "Could not auto-detect device information. "
                    "No /home/flashsysXXX folders found and $USER is not in flashsysXXX format. "
                    "Expected format: flashsys followed by digits (e.g., flashsys001, flashsys123)"
                )
                print(f"ERROR: {self._detection_error}")
                
        except Exception as e:
            self._detection_error = f"Error during auto-detection: {e}"
            print(f"ERROR: Auto-detection failed with exception: {e}")

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
        main_layout.addLayout(sections_layout)

        self._create_validation_section(main_layout)

        main_layout.addStretch()

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

        instruction_label = self.ui_factory.create_label(
            "Enter the participant ID. Device information will be auto-detected."
        )
        instruction_label.setStyleSheet("color: #666; font-size: 24px; margin-bottom: 8px;")
        participant_layout.addWidget(instruction_label)

        participant_id_label = self.ui_factory.create_label("Participant ID:")
        participant_id_label.setStyleSheet("font-weight: bold; margin-top: 8px; font-size: 24px;")
        participant_layout.addWidget(participant_id_label)

        def validate_participant_id(text: str) -> tuple[bool, str]:
            if not text.strip():
                return False, "Participant ID is required"

            if not re.match(Patterns.PARTICIPANT_ID, text):
                return False, "Format must be P1-XXXX or ES-XXXX (e.g., P1-0123, ES-0456)"
            return True, ""

        self.participant_id_input = self.ui_factory.create_input_field(
            Templates.PARTICIPANT_ID_PLACEHOLDER, validator=validate_participant_id
        )
        self.participant_id_input.textChanged.connect(self._on_participant_id_changed)
        self.participant_id_input.setStyleSheet("padding: 8px; font-size: 28px;")
        participant_layout.addWidget(self.participant_id_input)

        participant_layout.addSpacing(15)

        sudo_password_label = self.ui_factory.create_label("Sudo Password:")
        sudo_password_label.setStyleSheet("font-weight: bold; margin-top: 8px; font-size: 24px;")
        participant_layout.addWidget(sudo_password_label)

        self.sudo_password_input = self.ui_factory.create_input_field(
            "Enter sudo password for system operations..."
        )
        self.sudo_password_input.setEchoMode(self.sudo_password_input.EchoMode.Password)
        self.sudo_password_input.textChanged.connect(self._on_sudo_password_changed)
        self.sudo_password_input.setStyleSheet("padding: 8px; font-size: 28px;")
        participant_layout.addWidget(self.sudo_password_input)

        participant_layout.addStretch()

        return participant_group

    def _create_detection_info_section(self) -> QWidget:
        """Create the auto-detection information section showing read-only detected values."""
        # Use UI factory to create group box
        detection_group, detection_layout = self.ui_factory.create_group_box("Auto-Detected System Information")

        if self._detection_error:
            error_label = self.ui_factory.create_status_label(
                f"❌ Auto-Detection Failed", status_type="error"
            )
            error_label.setStyleSheet("font-weight: bold; color: #c62828; margin-bottom: 8px;")
            detection_layout.addWidget(error_label)

            error_detail = self.ui_factory.create_label(self._detection_error)
            error_detail.setStyleSheet("color: #666; font-size: 24px; padding: 8px; background-color: #ffebee; border-radius: 4px;")
            error_detail.setWordWrap(True)
            detection_layout.addWidget(error_detail)
        else:
            success_header = self.ui_factory.create_status_label(
                "✅ Auto-Detection Successful", status_type="success"
            )
            success_header.setStyleSheet("font-weight: bold; color: #2e7d32; margin-bottom: 12px;")
            detection_layout.addWidget(success_header)

            device_id_label = self.ui_factory.create_label(f"Device ID: {self._device_id}")
            device_id_label.setStyleSheet("font-weight: bold; color: #2e7d32; padding: 4px; background-color: #e8f5e8; border-radius: 4px;")
            detection_layout.addWidget(device_id_label)

            username_label = self.ui_factory.create_label(f"Username: {self._username}")
            username_label.setStyleSheet("font-weight: bold; color: #2e7d32; padding: 4px; background-color: #e8f5e8; border-radius: 4px;")
            detection_layout.addWidget(username_label)

            if self._device_id and self._username:
                participant_id = self.state.get_user_input("participant_id", "").strip()
                if participant_id and self._device_id:
                    data_path = f"/home/{self._username}/data/{participant_id}{self._device_id}_data"
                elif self._device_id:
                    data_path = f"/home/{self._username}/data/[PARTICIPANT_ID]{self._device_id}_data"
                else:
                    data_path = f"/home/{self._username}/data/[PARTICIPANT_ID][DEVICE_ID]_data"

                self.data_path_label = self.ui_factory.create_label(f"Data Path: {data_path}")
                self.data_path_label.setStyleSheet("font-weight: bold; color: #1976d2; padding: 4px; background-color: #e3f2fd; border-radius: 4px;")
                detection_layout.addWidget(self.data_path_label)

                info_note = self.ui_factory.create_label("* Data directory will be created when you continue to the next step")
                info_note.setStyleSheet("color: #666; font-size: 22px; font-style: italic; margin-top: 8px;")
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
            self.sudo_password_input.setText(
                self.state.get_user_input("sudo_password", "")
            )

            if self._device_id and self._username and not self._detection_error:
                self.state.set_user_input("device_id", self._device_id)
                self.state.set_user_input("username", self._username)

                participant_id = self.state.get_user_input("participant_id", "")
                if participant_id and self._device_id:
                    data_path = f"/home/{self._username}/data/{participant_id}{self._device_id}_data"
                    self.state.set_user_input("data_path", data_path)

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
        self.state.set_user_input("participant_id", participant_id)

        if self._device_id and self._username and not self._detection_error:
            if participant_id:
                data_path = f"/home/{self._username}/data/{participant_id}{self._device_id}_data"
                self.state.set_user_input("data_path", data_path)

                if hasattr(self, 'data_path_label'):
                    self.data_path_label.setText(f"Data Path: {data_path}")
                    self.data_path_label.setStyleSheet(
                        "font-weight: bold; color: #1976d2; padding: 4px; "
                        "background-color: #e3f2fd; border-radius: 4px;"
                    )
            else:
                placeholder_path = f"/home/{self._username}/data/[PARTICIPANT_ID]{self._device_id}_data"
                if hasattr(self, 'data_path_label'):
                    self.data_path_label.setText(f"Data Path: {placeholder_path}")
                    self.data_path_label.setStyleSheet(
                        "font-weight: normal; color: #666; padding: 4px; "
                        "background-color: #f5f5f5; border-radius: 4px; font-style: italic;"
                    )
                self.state.set_user_input("data_path", "")

        if self.state_manager:
            self.state_manager.save_state(self.state)
        self._validate_and_update_ui()

    @handle_step_error
    def _on_sudo_password_changed(self, text: str) -> None:
        """Handle sudo password input changes."""
        sudo_password = text.strip()
        self.state.set_user_input("sudo_password", sudo_password)

        # Persist state
        if self.state_manager:
            self.state_manager.save_state(self.state)
        self._validate_and_update_ui()

    @handle_step_error
    def _validate_and_update_ui(self) -> None:
        """Validate inputs and update UI state.

        Simplified validation focusing on:
        - Participant ID format validation
        - Auto-detection success
        """
        try:
            is_valid, errors = self.validate_inputs()

            participant_id = self.state.get_user_input("participant_id", "").strip()
            sudo_password = self.state.get_user_input("sudo_password", "").strip()
            has_detection = self._device_id and self._username and not self._detection_error

            all_requirements_met = bool(participant_id and sudo_password and has_detection and is_valid)

            if errors:
                error_message = "\n".join(errors)
                self._show_validation_error(error_message)
                self.logger.warning(f"Validation failed: {errors}")
            else:
                self._hide_validation_error()
                if all_requirements_met:
                    self.logger.info(f"Validation successful - Participant: {participant_id}, Device: {self._device_id}, User: {self._username}")

            self._update_continue_button(all_requirements_met)

            if all_requirements_met:
                self.update_status(StepStatus.COMPLETED)
            else:
                self.update_status(StepStatus.USER_ACTION_REQUIRED)

        except Exception as e:
            self.logger.error(f"Error during validation and UI update: {e}", exc_info=True)
            self._show_validation_error(f"Validation error: {e}")
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
        """Handle continue button click with comprehensive validation."""
        try:
            is_valid, errors = self.validate_inputs()
            participant_id = self.state.get_user_input("participant_id", "").strip()

            if is_valid and self.next_button.isEnabled() and participant_id and self._device_id and self._username:
                if self._device_id:
                    data_path = f"/home/{self._username}/data/{participant_id}{self._device_id}_data"
                    self.state.set_user_input("data_path", data_path)

                    os.makedirs(data_path, exist_ok=True)
                    self.logger.info(f"Created data directory: {data_path}")

                self.device_detected.emit(self._device_id, self._username, data_path)

                self.logger.info(
                    f"Participant setup completed - ID: {participant_id}, "
                    f"Device: {self._device_id}, Username: {self._username}, "
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
                recovery_action="Check all fields and try again",
            )

    def validate_inputs(self) -> Tuple[bool, list[str]]:
        """Validate participant_id format, sudo password, and auto-detection success.

        Validates:
        1. Participant ID format (P1-XXXX or ES-XXXX)
        2. Sudo password is provided
        3. Auto-detection succeeded (device_id and username available)

        Returns:
            tuple: (is_valid, list_of_error_messages)
        """
        errors = []

        try:
            # 1. Validate participant ID format
            participant_id = self.state.get_user_input("participant_id", "").strip()
            if not participant_id:
                errors.append("Participant ID is required")
            elif not re.match(Patterns.PARTICIPANT_ID, participant_id):
                errors.append("Participant ID must be in format P1-XXXX or ES-XXXX (e.g., P1-0123, ES-0456)")

            # 2. Validate sudo password
            sudo_password = self.state.get_user_input("sudo_password", "").strip()
            if not sudo_password:
                errors.append("Sudo password is required for system operations")

            # 3. Ensure auto-detection succeeded
            if self._detection_error:
                errors.append(f"Auto-detection failed: {self._detection_error}")
            elif not (self._device_id and self._username):
                errors.append("Device information could not be auto-detected")
            
            # Optional: Validate that the detected username home directory exists
            if self._username and not self._detection_error:
                home_path = f"/home/{self._username}"
                if not os.path.isdir(home_path):
                    errors.append(f"Auto-detected home directory does not exist: {home_path}")
                    
        except Exception as e:
            errors.append(f"Validation error: {e}")
            self.logger.error(f"Exception during input validation: {e}", exc_info=True)
        
        is_valid = len(errors) == 0
        return is_valid, errors

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the participant setup step with enhanced logic."""
        super().activate_step()

        # Validate and update UI
        self._validate_and_update_ui()

        # Focus on participant ID input (only user-editable field)
        if hasattr(self, 'participant_id_input'):
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

    def get_device_info(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
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
        
    def get_generated_data_path(self, participant_id: str = None) -> str:
        """Get the auto-generated data path for a participant.
        
        Args:
            participant_id: Participant ID to use, or None to use current state value
            
        Returns:
            str: Generated data path or empty string if auto-detection failed
        """
        if not self.is_auto_detection_successful():
            return ""
            
        if participant_id is None:
            participant_id = self.state.get_user_input("participant_id", "").strip()
            
        if not participant_id:
            return ""
            
        if self._device_id:
            return f"/home/{self._username}/data/{participant_id}{self._device_id}_data"
        return f"/home/{self._username}/data/{participant_id}_data"  # Fallback if no device_id