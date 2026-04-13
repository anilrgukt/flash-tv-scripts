"""Base WizardStep class for all setup steps."""

from __future__ import annotations

from core.config import get_config
from core.event_store import get_event_store
from core.exceptions import ErrorType, FlashTVError, handle_step_error
from core.process_runner import ProcessRunner
from core.state_manager import StateManager
from models import StepDefinition, StepStatus, WizardState
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QWidget
from utils.adaptive_font import get_adaptive_scaler
from utils.logger import get_logger
from utils.ui_factory import get_ui_factory


class WizardStep(QWidget):
    """Base class for all wizard steps with new framework integration."""

    # Signals
    status_changed = Signal(StepStatus)
    step_completed = Signal(int)
    request_next_step = Signal()

    def __init__(
        self,
        step_definition: StepDefinition,
        state: WizardState,
        process_runner: ProcessRunner,
        state_manager: StateManager | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.step_definition = step_definition
        self.state = state
        self.process_runner = process_runner
        self.state_manager = state_manager
        self.current_status = StepStatus.PENDING

        self.config = get_config()
        self.ui_factory = get_ui_factory()
        self.adaptive_scaler = get_adaptive_scaler()
        self.logger = get_logger(f"step_{step_definition.step_id}")
        self.event_store = get_event_store()

        self._managed_timers: list[QTimer] = []
        self._reactivate_timers: set[int] = set()

        self._setup_ui()
        self.update_status(StepStatus.PENDING)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._safe_update_ui)
        self.update_timer.start(self.config.status_update_interval_ms)
        self._managed_timers.append(self.update_timer)

    def _setup_ui(self) -> None:
        """Initialize the base UI structure using UI factory."""
        self.main_layout = self.ui_factory.create_main_step_layout()
        self.setLayout(self.main_layout)

        self._create_header()

        self.content_widget = self.create_content_widget()
        if self.content_widget:
            self.main_layout.addWidget(self.content_widget, stretch=1)
            self.adaptive_scaler.apply_adaptive_scaling(
                self.content_widget, delay_ms=200
            )

    def _create_header(self) -> None:
        """Create the compact header section."""
        header_layout = self.ui_factory.create_vertical_layout(spacing=3)

        title_text = (
            f"Step {self.step_definition.step_id}: {self.step_definition.title}"
        )
        self.title_label = self.ui_factory.create_label(
            title_text, style="font-size: 14px; font-weight: bold; margin: 2px;"
        )
        header_layout.addWidget(self.title_label)

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

            status_text = self._get_status_text(status)

            self.status_label.setText(status_text)
            self.status_label.setStyleSheet(self._get_status_style(status))

            self.status_changed.emit(status)

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
            self.state.mark_step_completed(self.step_definition.step_id)

            if self.state_manager:
                self.state_manager.save_state(self.state)

            # Log step completion to event store
            self.event_store.log_step_completed(
                self.step_definition.step_id,
                self.step_definition.title,
            )

            self.step_completed.emit(self.step_definition.step_id)

            self.logger.info(
                f"Step {self.step_definition.step_id} completed successfully"
            )

        except Exception as e:
            self.logger.error(f"Error handling step completion: {e}")
            self.event_store.log_error(
                self.step_definition.step_id,
                "step_completion_failed",
                str(e),
            )
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

            if not self.update_timer.isActive():
                self.update_timer.start(self.config.status_update_interval_ms)

            for timer in self._managed_timers:
                if id(timer) in self._reactivate_timers and not timer.isActive():
                    timer.start(timer.interval())
            self._reactivate_timers.clear()

            # Log step activation to event store
            self.event_store.log_step_activated(
                self.step_definition.step_id,
                self.step_definition.title,
            )

            if self.is_completed():
                self.logger.info(
                    f"Step {self.step_definition.step_id} already completed, skipping prerequisite check"
                )
                self.update_status(StepStatus.COMPLETED)
            elif not self.check_prerequisites():
                self.update_status(StepStatus.PENDING)
                self.logger.warning(
                    f"Step {self.step_definition.step_id} prerequisites not met"
                )
            else:
                self.update_status(StepStatus.USER_ACTION_REQUIRED)

            if self.content_widget:
                self.adaptive_scaler.apply_adaptive_scaling(
                    self.content_widget, delay_ms=300
                )

        except Exception as e:
            self.logger.error(
                f"Error activating step {self.step_definition.step_id}: {e}"
            )
            self.update_status(StepStatus.FAILED)
            raise

    def create_timer(
        self, interval_ms: int, callback: callable, start: bool = True
    ) -> QTimer:
        """
        Create and track a timer for automatic cleanup.

        Args:
            interval_ms: Timer interval in milliseconds
            callback: Function to call on timeout
            start: Whether to start the timer immediately (default True)

        Returns:
            The created QTimer
        """
        timer = QTimer(self)
        timer.timeout.connect(callback)

        if start:
            timer.start(interval_ms)

        self._managed_timers.append(timer)
        return timer

    def stop_all_timers(self) -> None:
        """Stop all managed timers."""
        self._reactivate_timers.clear()
        for timer in self._managed_timers:
            if timer.isActive():
                self._reactivate_timers.add(id(timer))
                timer.stop()

    def deactivate_step(self) -> None:
        """Deactivate this step (called when user navigates away).

        Override in subclasses for step-specific deactivation logic.
        Base implementation stops all managed timers.
        """
        self.stop_all_timers()

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

            self.stop_all_timers()
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

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard events for navigation.

        - Enter/Return: Click the step's advance button if enabled
        - Escape: No action (could be used for cancel in future)
        """
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            for attribute_name in ("continue_button", "next_button"):
                advance_button = getattr(self, attribute_name, None)
                if advance_button is not None and advance_button.isEnabled():
                    advance_button.click()
                    return
        super().keyPressEvent(event)

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
            if not notes or not notes.strip():
                self.logger.debug(f"No notes to save for {step_name}")
                return True

            notes = notes.strip()
            notes = notes.replace("\x00", "")
            max_length = 50000
            if len(notes) > max_length:
                self.logger.warning(
                    f"Notes exceeded {max_length} characters, truncating"
                )
                notes = notes[:max_length] + "\n[... truncated ...]"

            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not all([participant_id, device_id, username]):
                self.logger.warning(
                    f"Cannot save notes for {step_name}: missing participant info "
                    f"(participant_id={participant_id}, device_id={device_id}, username={username})"
                )
                return False

            combined_id = f"{participant_id}{device_id}"
            data_folder = os.path.join("/home", username, "data", f"{combined_id}_data")

            os.makedirs(data_folder, exist_ok=True)

            notes_file = os.path.join(data_folder, f"{combined_id}_notes.txt")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
