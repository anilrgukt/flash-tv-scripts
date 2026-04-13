"""WizardState model for FLASH-TV setup wizard."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config.participant_contract import (
    build_participant_full_id,
    get_gallery_dir,
    get_participant_data_dir,
)
from models.process_info import ProcessInfo
from models.state_keys import (
    STEP_DEPENDENCIES,
    STEP_REQUIRED_INPUTS,
    SystemStateKey,
    UserInputKey,
    WizardStep,
)


@dataclass
class WizardState:
    """Central state container for the FLASH-TV setup wizard with business logic.

    Uses type-safe Enums for step IDs and state keys to prevent typos and
    enable IDE autocomplete. The class maintains backwards compatibility by
    accepting both Enum and primitive types where appropriate.
    """

    current_step: int = 1
    completed_steps: set[int] = field(default_factory=set)
    user_inputs: dict[str, Any] = field(default_factory=dict)
    system_state: dict[str, Any] = field(default_factory=dict)
    process_status: dict[str, ProcessInfo] = field(default_factory=dict)

    # Use enum-based dependencies from state_keys module
    STEP_DEPENDENCIES = STEP_DEPENDENCIES
    STEP_REQUIRED_INPUTS = STEP_REQUIRED_INPUTS

    def mark_step_completed(self, step_id: WizardStep | int) -> None:
        """Mark a step as completed.

        Args:
            step_id: Step to mark completed (WizardStep enum or int for compatibility)
        """
        step_num = int(step_id) if isinstance(step_id, WizardStep) else step_id
        self.completed_steps.add(step_num)

    def is_step_completed(self, step_id: WizardStep | int) -> bool:
        """Check if a step is completed.

        Args:
            step_id: Step to check (WizardStep enum or int for compatibility)

        Returns:
            True if step is completed, False otherwise
        """
        step_num = int(step_id) if isinstance(step_id, WizardStep) else step_id
        return step_num in self.completed_steps

    def get_completion_percentage(self) -> int:
        """
        Get overall wizard completion percentage.

        Returns:
            Percentage (0-100) of completed steps
        """
        if not self.STEP_DEPENDENCIES:
            return 0

        total_steps = len(self.STEP_DEPENDENCIES)
        completed_count = len(self.completed_steps)

        return int((completed_count / total_steps) * 100)

    def can_proceed_to_step(self, step_number: WizardStep | int) -> tuple[bool, str]:
        """Check if user can proceed to a specific step.

        Args:
            step_number: Step to check (WizardStep enum or int for compatibility)

        Returns:
            Tuple of (can_proceed: bool, reason: str)
        """
        # Convert to WizardStep enum if int provided
        if isinstance(step_number, int):
            try:
                step_enum = WizardStep(step_number)
            except ValueError:
                return False, f"Invalid step number: {step_number}"
        else:
            step_enum = step_number

        required_steps = self.STEP_DEPENDENCIES.get(step_enum, [])
        missing_steps = [
            s for s in required_steps if int(s) not in self.completed_steps
        ]

        if missing_steps:
            return False, f"Must complete steps {[int(s) for s in missing_steps]} first"

        required_inputs = self.STEP_REQUIRED_INPUTS.get(step_enum, [])
        missing_inputs = [
            i.value for i in required_inputs if i.value not in self.user_inputs
        ]

        if missing_inputs:
            return False, f"Missing required information: {', '.join(missing_inputs)}"

        return True, ""

    def get_next_incomplete_step(self) -> int | None:
        """Get the next step that hasn't been completed.

        Returns:
            Step number of next incomplete step, or None if all complete
        """
        for step_enum in sorted(self.STEP_DEPENDENCIES.keys()):
            step_num = int(step_enum)
            if step_num not in self.completed_steps:
                return step_num
        return None

    def get_user_input(self, key: UserInputKey | str, default: Any = None) -> Any:
        """Get user input value with optional default.

        Args:
            key: User input key (UserInputKey enum or str for compatibility)
            default: Default value if key not found

        Returns:
            User input value or default
        """
        key_str = key.value if isinstance(key, UserInputKey) else key
        return self.user_inputs.get(key_str, default)

    def set_user_input(self, key: UserInputKey | str, value: Any) -> None:
        """Set user input value.

        Args:
            key: User input key (UserInputKey enum or str for compatibility)
            value: Value to store
        """
        key_str = key.value if isinstance(key, UserInputKey) else key
        self.user_inputs[key_str] = value

    def has_user_input(self, key: UserInputKey | str) -> bool:
        """Check if a user input exists.

        Args:
            key: User input key (UserInputKey enum or str for compatibility)

        Returns:
            True if key exists, False otherwise
        """
        key_str = key.value if isinstance(key, UserInputKey) else key
        return key_str in self.user_inputs

    def remove_user_input(self, key: UserInputKey | str) -> Any:
        """Remove and return a user input value.

        Args:
            key: User input key (UserInputKey enum or str for compatibility)

        Returns:
            Removed value or None if key didn't exist
        """
        key_str = key.value if isinstance(key, UserInputKey) else key
        return self.user_inputs.pop(key_str, None)

    def get_participant_id(self) -> str | None:
        """Get validated participant ID."""
        return self.user_inputs.get(UserInputKey.PARTICIPANT_ID.value)

    def get_device_id(self) -> str | None:
        """Get validated device ID."""
        return self.user_inputs.get(UserInputKey.DEVICE_ID.value)

    def get_combined_id(self) -> str | None:
        """
        Get combined participant+device ID (e.g., 'P1-0001-A').

        Returns:
            Combined ID or None if either component is missing
        """
        participant_id = self.get_participant_id()
        device_id = self.get_device_id()

        if participant_id and device_id:
            return build_participant_full_id(participant_id, device_id)
        return None

    def get_username(self) -> str | None:
        """Get system username."""
        return self.user_inputs.get(UserInputKey.USERNAME.value)

    def get_data_directory(self) -> Path | None:
        """
        Get participant's data directory path.

        Returns:
            Path object or None if components are missing
        """
        username = self.get_username()
        combined_id = self.get_combined_id()

        if username and combined_id:
            participant_id = self.get_participant_id()
            device_id = self.get_device_id()
            if participant_id and device_id:
                return get_participant_data_dir(username, participant_id, device_id)
        return None

    def get_gallery_directory(self) -> Path | None:
        """
        Get gallery directory path for participant.

        Returns:
            Path object or None if components are missing
        """
        data_dir = self.get_data_directory()
        combined_id = self.get_combined_id()

        if data_dir and combined_id:
            username = self.get_username()
            participant_id = self.get_participant_id()
            device_id = self.get_device_id()
            if username and participant_id and device_id:
                return get_gallery_dir(username, participant_id, device_id)
        return None

    def get_log_file_path(self, log_type: str = "main") -> Path | None:
        """
        Get log file path for participant.

        Args:
            log_type: Type of log file (main, rot, reg, etc.)

        Returns:
            Path object or None if components are missing
        """
        data_dir = self.get_data_directory()
        combined_id = self.get_combined_id()

        if data_dir and combined_id:
            if log_type == "main":
                filename = f"{combined_id}_flash_log.txt"
            else:
                filename = f"{combined_id}_flash_log_{log_type}.txt"

            return data_dir / filename
        return None

    def get_wifi_ssid(self) -> str | None:
        """Get connected WiFi SSID."""
        return self.user_inputs.get(UserInputKey.WIFI_SSID.value)

    def is_wifi_connected(self) -> bool:
        """Check if WiFi is connected."""
        return self.user_inputs.get(UserInputKey.WIFI_CONNECTED.value, False)

    def set_wifi_info(self, ssid: str, connected: bool = True) -> None:
        """Set WiFi connection information."""
        self.user_inputs[UserInputKey.WIFI_SSID.value] = ssid
        self.user_inputs[UserInputKey.WIFI_CONNECTED.value] = connected

    def get_system_state(self, key: SystemStateKey | str, default: Any = None) -> Any:
        """Get system state value with optional default.

        Args:
            key: System state key (SystemStateKey enum or str for compatibility)
            default: Default value if key not found

        Returns:
            System state value or default
        """
        key_str = key.value if isinstance(key, SystemStateKey) else key
        return self.system_state.get(key_str, default)

    def set_system_state(self, key: SystemStateKey | str, value: Any) -> None:
        """Set system state value.

        Args:
            key: System state key (SystemStateKey enum or str for compatibility)
            value: Value to store
        """
        key_str = key.value if isinstance(key, SystemStateKey) else key
        self.system_state[key_str] = value

    def has_system_state(self, key: SystemStateKey | str) -> bool:
        """Check if a system state key exists.

        Args:
            key: System state key (SystemStateKey enum or str for compatibility)

        Returns:
            True if key exists, False otherwise
        """
        key_str = key.value if isinstance(key, SystemStateKey) else key
        return key_str in self.system_state

    def add_process(self, process_name: str, process_info: ProcessInfo) -> None:
        """Add a tracked process."""
        self.process_status[process_name] = process_info

    def remove_process(self, process_name: str) -> ProcessInfo | None:
        """Remove a tracked process and return it if it existed."""
        return self.process_status.pop(process_name, None)

    def get_process(self, process_name: str) -> ProcessInfo | None:
        """Get a tracked process."""
        return self.process_status.get(process_name)

    def get_all_processes(self) -> dict[str, ProcessInfo]:
        """Get all tracked processes."""
        return self.process_status.copy()

    def has_running_processes(self) -> bool:
        """Check if there are any running processes."""
        return any(p.is_running() for p in self.process_status.values())

    def get_running_process_count(self) -> int:
        """Get count of currently running processes."""
        return sum(1 for p in self.process_status.values() if p.is_running())

    # ==================== Validation Methods ====================

    def validate_for_step(
        self, step_number: WizardStep | int
    ) -> tuple[bool, list[str]]:
        """Validate state for a specific step.

        Args:
            step_number: Step to validate (WizardStep enum or int for compatibility)

        Returns:
            Tuple of (is_valid: bool, error_messages: list[str])
        """
        errors = []

        # Convert to int for comparison
        step_num = (
            int(step_number) if isinstance(step_number, WizardStep) else step_number
        )

        # Check prerequisites
        can_proceed, reason = self.can_proceed_to_step(step_number)
        if not can_proceed:
            errors.append(reason)

        # Step-specific validation using WizardStep enum
        if step_num == WizardStep.WIFI_CONNECTION:
            if not self.get_username():
                errors.append("Username is required")

        elif step_num == WizardStep.SMART_PLUG_PHYSICAL:
            if not self.get_combined_id():
                errors.append("Participant and device IDs are required")

        elif step_num == WizardStep.SERVICE_STARTUP:
            if not self.get_data_directory():
                errors.append("Data directory path cannot be determined")

        return len(errors) == 0, errors

    # ==================== Serialization Methods ====================

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "current_step": self.current_step,
            "completed_steps": list(self.completed_steps),
            "user_inputs": self.user_inputs,
            "system_state": self.system_state,
            # Note: process_status is not serialized as processes don't survive across sessions
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WizardState:
        """Create state from dictionary."""
        state = cls()
        state.current_step = data.get("current_step", 1)
        state.completed_steps = set(data.get("completed_steps", []))
        state.user_inputs = data.get("user_inputs", {})
        state.system_state = data.get("system_state", {})
        # process_status starts empty on deserialization
        return state

    # ==================== Debug/Display Methods ====================

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of the current wizard state for debugging/display.

        Returns:
            Dictionary with state summary
        """
        return {
            "current_step": self.current_step,
            "completed_steps": sorted(self.completed_steps),
            "completion_percentage": self.get_completion_percentage(),
            "participant_id": self.get_participant_id(),
            "device_id": self.get_device_id(),
            "combined_id": self.get_combined_id(),
            "username": self.get_username(),
            "selected_camera": self.get_user_input(UserInputKey.SELECTED_CAMERA),
            "camera_tested": self.get_user_input(UserInputKey.CAMERA_TESTED, False),
            "gallery_validated": self.get_user_input(
                UserInputKey.GALLERY_VALIDATED, False
            ),
            "wifi_connected": self.is_wifi_connected(),
            "wifi_ssid": self.get_wifi_ssid(),
            "running_processes": self.get_running_process_count(),
            "next_incomplete_step": self.get_next_incomplete_step(),
        }
