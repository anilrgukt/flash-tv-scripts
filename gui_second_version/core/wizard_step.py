"""Base WizardStep class for all setup steps."""

from __future__ import annotations

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget

from models import StepDefinition, StepStatus, WizardState
from core.process_runner import ProcessRunner
from core.state_manager import StateManager
from core.config import get_config
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from utils.ui_factory import get_ui_factory
from utils.logger import get_logger


class WizardStep(QWidget):
    """Base class for all wizard steps with new framework integration."""

    # Signals
    status_changed = pyqtSignal(StepStatus)
    step_completed = pyqtSignal(int)
    request_next_step = pyqtSignal()

    def __init__(
        self,
        step_definition: StepDefinition,
        state: WizardState,
        process_runner: ProcessRunner,
        state_manager: StateManager | None = None,
        parent=None,
    ):
        super().__init__(parent)

        # Core components
        self.step_definition = step_definition
        self.state = state
        self.process_runner = process_runner
        self.state_manager = state_manager
        self.current_status = StepStatus.PENDING

        # Framework components
        self.config = get_config()
        self.ui_factory = get_ui_factory()
        self.logger = get_logger(f"step_{step_definition.step_id}")

        # Initialize UI using factory
        self._setup_ui()

        # Initialize status
        self.update_status(StepStatus.PENDING)

        # Setup update timer for dynamic content
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._safe_update_ui)
        self.update_timer.start(self.config.status_update_interval_ms)

    def _setup_ui(self) -> None:
        """Initialize the base UI structure using UI factory."""
        self.main_layout = self.ui_factory.create_main_step_layout()
        self.setLayout(self.main_layout)

        # Create header section
        self._create_header()

        # Content widget (implemented by subclasses)
        self.content_widget = self.create_content_widget()
        if self.content_widget:
            self.main_layout.addWidget(self.content_widget, stretch=1)

    def _create_header(self) -> None:
        """Create the compact header section."""
        header_layout = self.ui_factory.create_vertical_layout(spacing=3)

        # Title label
        title_text = (
            f"Step {self.step_definition.step_id}: {self.step_definition.title}"
        )
        self.title_label = self.ui_factory.create_label(
            title_text, style="font-size: 14px; font-weight: bold; margin: 2px;"
        )
        header_layout.addWidget(self.title_label)

        # Status label
        self.status_label = self.ui_factory.create_status_label(
            "Loading...", status_type="info"
        )
        header_layout.addWidget(self.status_label)

        self.main_layout.addLayout(header_layout)

    def create_content_widget(self) -> QWidget | None:
        """Create the main content widget for this step.

        Must be implemented by subclasses to provide step-specific UI.
        """
        raise NotImplementedError("Subclasses must implement create_content_widget()")

    @handle_step_error
    def update_status(self, status: StepStatus) -> None:
        """Update the status of this step with error handling."""
        try:
            self.current_status = status
            self.logger.info(
                f"Step {self.step_definition.step_id} status changed to {status.value}"
            )

            # Update status label using status type mapping
            status_type = self._map_status_to_type(status)
            status_text = self._get_status_text(status)

            # Use UI factory to update status label
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet(self._get_status_style(status))

            # Emit signal
            self.status_changed.emit(status)

            # Handle completion with state persistence
            if status == StepStatus.COMPLETED:
                self._handle_step_completion()

        except Exception as e:
            self.logger.error(
                f"Error updating status for step {self.step_definition.step_id}: {e}"
            )
            raise FlashTVError(
                f"Failed to update step status: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try refreshing the step or restart the wizard",
            )

    def _map_status_to_type(self, status: StepStatus) -> str:
        """Map step status to UI status type."""
        mapping = {
            StepStatus.PENDING: "info",
            StepStatus.USER_ACTION_REQUIRED: "info",
            StepStatus.AUTOMATION_RUNNING: "warning",
            StepStatus.COMPLETED: "success",
            StepStatus.FAILED: "error",
        }
        return mapping.get(status, "info")

    def _get_status_text(self, status: StepStatus) -> str:
        """Get display text for status."""
        text_mapping = {
            StepStatus.PENDING: "⚪ PENDING",
            StepStatus.USER_ACTION_REQUIRED: "🔵 USER ACTION REQUIRED",
            StepStatus.AUTOMATION_RUNNING: "🔄 AUTOMATION RUNNING",
            StepStatus.COMPLETED: "✅ COMPLETED",
            StepStatus.FAILED: "❌ FAILED",
        }
        return text_mapping.get(status, "⚪ PENDING")

    def _get_status_style(self, status: StepStatus) -> str:
        """Get CSS style for status display."""
        styles = {
            StepStatus.PENDING: f"color: {self.config.pending_color}; font-weight: bold; padding: 5px;",
            StepStatus.USER_ACTION_REQUIRED: f"color: {self.config.info_color}; font-weight: bold; padding: 5px;",
            StepStatus.AUTOMATION_RUNNING: f"color: {self.config.warning_color}; font-weight: bold; padding: 5px;",
            StepStatus.COMPLETED: f"color: {self.config.success_color}; font-weight: bold; padding: 5px;",
            StepStatus.FAILED: f"color: {self.config.error_color}; font-weight: bold; padding: 5px;",
        }
        return styles.get(status, styles[StepStatus.PENDING])

    def _handle_step_completion(self) -> None:
        """Handle step completion with state persistence."""
        try:
            # Mark in wizard state
            self.state.mark_step_completed(self.step_definition.step_id)

            # Persist state if state manager available
            if self.state_manager:
                self.state_manager.save_state(self.state)

            # Emit completion signal
            self.step_completed.emit(self.step_definition.step_id)

            self.logger.info(
                f"Step {self.step_definition.step_id} completed successfully"
            )

        except Exception as e:
            self.logger.error(f"Error handling step completion: {e}")
            raise

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites for this step are met."""
        return self.step_definition.has_prerequisites_met(self.state.completed_steps)

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate current inputs against step validation rules."""
        return self.step_definition.validate_inputs(self.state.user_inputs)

    def _safe_update_ui(self) -> None:
        """Safely update UI with error handling."""
        try:
            self.update_ui()
        except Exception as e:
            self.logger.error(
                f"Error updating UI for step {self.step_definition.step_id}: {e}"
            )
            # Don't re-raise to avoid breaking the timer

    def update_ui(self) -> None:
        """Update UI elements that may change over time.

        Called periodically by update_timer. Override in subclasses
        for step-specific updates.
        """
        pass

    @handle_step_error
    def activate_step(self) -> None:
        """Activate this step with error handling.

        Override in subclasses for step-specific activation logic.
        """
        try:
            self.logger.info(f"Activating step {self.step_definition.step_id}")

            if not self.check_prerequisites():
                self.update_status(StepStatus.PENDING)
                self.logger.warning(
                    f"Step {self.step_definition.step_id} prerequisites not met"
                )
            else:
                self.update_status(StepStatus.USER_ACTION_REQUIRED)

        except Exception as e:
            self.logger.error(
                f"Error activating step {self.step_definition.step_id}: {e}"
            )
            self.update_status(StepStatus.FAILED)
            raise

    def deactivate_step(self) -> None:
        """Deactivate this step (called when user navigates away).

        Override in subclasses for step-specific deactivation logic.
        """
        pass

    def is_completed(self) -> bool:
        """Check if this step is completed."""
        return self.state.is_step_completed(self.step_definition.step_id)

    def get_completion_percentage(self) -> int:
        """Get the completion percentage for this step (0-100).

        Override in subclasses for more granular progress tracking.
        """
        return 100 if self.is_completed() else 0

    def cleanup(self) -> None:
        """Clean up resources when step is destroyed."""
        try:
            self.logger.info(f"Cleaning up step {self.step_definition.step_id}")

            # Stop timer
            if self.update_timer.isActive():
                self.update_timer.stop()

            # Clean up step-specific resources
            self._cleanup_step_resources()

        except Exception as e:
            self.logger.error(
                f"Error during cleanup for step {self.step_definition.step_id}: {e}"
            )

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources.

        Override in subclasses for custom cleanup logic.
        """
        pass

    def _save_notes_to_file(self, step_name: str, notes: str) -> bool:
        """
        Safely save notes to the participant's notes file.

        Args:
            step_name: Name of the step (e.g., "Cord Checking", "Device Locking")
            notes: The notes content to save

        Returns:
            bool: True if saved successfully, False otherwise
        """
        import os
        from datetime import datetime

        try:
            # Validate inputs
            if not notes or not notes.strip():
                self.logger.debug(f"No notes to save for {step_name}")
                return True  # Not an error, just nothing to save

            notes = notes.strip()

            # Sanitize notes (remove null bytes, limit length)
            notes = notes.replace('\x00', '')  # Remove null bytes
            max_length = 50000  # 50KB limit for notes
            if len(notes) > max_length:
                self.logger.warning(f"Notes exceeded {max_length} characters, truncating")
                notes = notes[:max_length] + "\n[... truncated ...]"

            # Get participant information from state
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            # Validate required fields
            if not all([participant_id, device_id, username]):
                self.logger.warning(
                    f"Cannot save notes for {step_name}: missing participant info "
                    f"(participant_id={participant_id}, device_id={device_id}, username={username})"
                )
                return False

            # Construct safe file path
            combined_id = f"{participant_id}{device_id}"
            data_folder = os.path.join("/home", username, "data", f"{combined_id}_data")

            # Ensure data folder exists
            os.makedirs(data_folder, exist_ok=True)

            notes_file = os.path.join(data_folder, f"{combined_id}_notes.txt")

            # Generate timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Safely append notes to file
            with open(notes_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 60}\n")
                f.write(f"{step_name} Notes - {timestamp}\n")
                f.write(f"{'=' * 60}\n")
                f.write(notes)
                f.write("\n\n")

            self.logger.info(f"Saved {step_name} notes to {notes_file}")
            return True

        except PermissionError as e:
            self.logger.error(f"Permission denied saving notes for {step_name}: {e}")
            return False
        except OSError as e:
            self.logger.error(f"OS error saving notes for {step_name}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error saving notes for {step_name}: {e}")
            return False
