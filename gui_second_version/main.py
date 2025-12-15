"""Main application file for FLASH-TV setup wizard."""

from __future__ import annotations

import sys
from pathlib import Path

# Add the current directory to Python path for proper imports
sys.path.insert(0, str(Path(__file__).parent))

from config.messages import MESSAGES
from config.ui_config import UI_CONFIG
from core import ProcessRunner, StateManager
from models import StepStatus, WizardState
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCloseEvent, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from steps import StepFactory
from utils import FlashLogger, get_logger, log_step_complete, log_step_start


class FlashTVSetupWizard(QMainWindow):
    """Main application window for FLASH-TV setup wizard."""

    def __init__(self):
        super().__init__()

        FlashLogger.setup_logging(debug=False)
        self.logger = get_logger("main")
        self.logger.info("FLASH-TV Setup Wizard starting")

        self.state = WizardState()
        self.state_manager = StateManager()
        self.process_runner = ProcessRunner(self.state)

        self.step_definitions = StepFactory.create_step_definitions()
        self.steps = {}
        self.current_step_widget = None

        self.setup_ui()

        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_state)
        self.auto_save_timer.start(UI_CONFIG.AUTO_SAVE_INTERVAL_MS)

        self.check_for_existing_session()
        self.navigate_to_step(self.state.current_step)

    def setup_ui(self) -> None:
        """Setup the main user interface."""
        self.setWindowTitle(MESSAGES.APP_NAME)
        self.setMinimumSize(
            UI_CONFIG.MIN_WINDOW_WIDTH, UI_CONFIG.MIN_WINDOW_HEIGHT - 200
        )

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with reduced margins
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(
            UI_CONFIG.DEFAULT_MARGIN,
            UI_CONFIG.DEFAULT_MARGIN,
            UI_CONFIG.DEFAULT_MARGIN,
            UI_CONFIG.DEFAULT_MARGIN,
        )
        main_layout.setSpacing(UI_CONFIG.SECTION_SPACING)

        # Compact header with step info and progress
        header_widget = self.create_compact_header()
        main_layout.addWidget(header_widget)

        # Step content area (takes most space)
        self.step_stack = QStackedWidget()
        main_layout.addWidget(self.step_stack)

        # Status bar
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("Welcome to FLASH-TV Setup Wizard")

    def create_compact_header(self) -> QWidget:
        """Create a compact header with title, step info, progress, and navigation."""
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(
            UI_CONFIG.DEFAULT_PADDING,
            UI_CONFIG.DEFAULT_PADDING,
            UI_CONFIG.DEFAULT_PADDING,
            UI_CONFIG.DEFAULT_PADDING,
        )
        header_layout.setSpacing(UI_CONFIG.CONTENT_SPACING)

        # Title row
        title_row = QHBoxLayout()
        title_label = QLabel("FLASH-TV System Setup Wizard")
        title_font = QFont()
        title_font.setPointSize(UI_CONFIG.TITLE_FONT_SIZE)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_row.addWidget(title_label)
        title_row.addStretch()

        # Current step indicator
        self.step_indicator = QLabel()
        self.step_indicator.setStyleSheet("font-weight: bold;")
        title_row.addWidget(self.step_indicator)
        header_layout.addLayout(title_row)

        # Progress and navigation row
        progress_nav_layout = QHBoxLayout()

        # Progress bar (compact)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(MESSAGES.TOTAL_STEPS)
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setMaximumHeight(20)
        progress_nav_layout.addWidget(self.progress_bar)

        # Navigation buttons (integrated)
        self.prev_button = QPushButton("← Previous")
        self.prev_button.clicked.connect(self.go_to_previous_step)
        self.prev_button.setEnabled(False)
        self.prev_button.setMaximumWidth(80)
        self.prev_button.setMinimumHeight(25)
        self.prev_button.setMaximumHeight(25)
        progress_nav_layout.addWidget(self.prev_button)

        # Status info (compact)
        self.nav_status_label = QLabel()
        self.nav_status_label.setMaximumWidth(150)
        progress_nav_layout.addWidget(self.nav_status_label)

        # Next/Finish buttons
        self.next_button = QPushButton("Next →")
        self.next_button.clicked.connect(self.go_to_next_step)
        self.next_button.setMaximumWidth(80)
        self.next_button.setMinimumHeight(25)
        self.next_button.setMaximumHeight(25)
        progress_nav_layout.addWidget(self.next_button)

        self.finish_button = QPushButton("Finish")
        self.finish_button.clicked.connect(self.finish_setup)
        self.finish_button.setVisible(False)
        self.finish_button.setMaximumWidth(80)
        self.finish_button.setMinimumHeight(25)
        self.finish_button.setMaximumHeight(25)
        progress_nav_layout.addWidget(self.finish_button)

        header_layout.addLayout(progress_nav_layout)
        return header_widget

    def check_for_existing_session(self) -> None:
        """Check for existing session and offer recovery."""
        if self.state_manager.detect_incomplete_session():
            if self.state_manager.create_recovery_dialog(self):
                loaded_state = self.state_manager.load_state()
                if loaded_state:
                    self.logger.info(
                        f"Loading session with current_step: {loaded_state.current_step}"
                    )
                    self.state = loaded_state
                    self.process_runner.state = self.state
                    self.logger.info(
                        f"Session recovered - will navigate to step {self.state.current_step}"
                    )
                    if status_bar := self.statusBar():
                        status_bar.showMessage("Session recovered successfully")
                else:
                    self.logger.warning("Failed to load existing session state")
                    if status_bar := self.statusBar():
                        status_bar.showMessage("Failed to recover session")
            else:
                self.logger.info("User chose to start fresh session")
                self.state_manager.clear_state()
                if status_bar := self.statusBar():
                    status_bar.showMessage("Starting new setup session")
        else:
            self.logger.info("No existing session detected, starting fresh")

    def navigate_to_step(self, step_id: int) -> None:
        """Navigate to a specific step."""
        self.logger.info(f"Navigating to step {step_id}")
        if step_id < 1 or step_id > MESSAGES.TOTAL_STEPS:
            self.logger.warning(f"Invalid step ID: {step_id}")
            return

        if self.current_step_widget:
            self.current_step_widget.deactivate_step()

        if step_id not in self.steps:
            step_def = next(
                (s for s in self.step_definitions if s.step_id == step_id), None
            )
            if step_def:
                step_widget = StepFactory.create_step_instance(
                    step_def, self.state, self.process_runner, self.state_manager, self
                )

                step_widget.status_changed.connect(self.on_step_status_changed)
                step_widget.step_completed.connect(self.on_step_completed)
                step_widget.request_next_step.connect(self.go_to_next_step)

                self.steps[step_id] = step_widget
                self.step_stack.addWidget(step_widget)

        if step_id in self.steps:
            self.current_step_widget = self.steps[step_id]
            self.step_stack.setCurrentWidget(self.current_step_widget)
            self.state.current_step = step_id

            step_name = MESSAGES.STEP_TITLES.get(step_id, f"Step {step_id}")
            log_step_start(step_id, step_name)

            self.current_step_widget.activate_step()
            self.update_ui()
            self.auto_save_state()

    def update_ui(self) -> None:
        """Update UI elements based on current state."""
        current_step = self.state.current_step
        completed_count = len(self.state.completed_steps)

        step_title = MESSAGES.STEP_TITLES.get(current_step, f"Step {current_step}")
        self.step_indicator.setText(
            f"Step {current_step} of {MESSAGES.TOTAL_STEPS}: {step_title}"
        )

        self.progress_bar.setValue(completed_count)
        self.progress_bar.setFormat(
            f"{completed_count}/{MESSAGES.TOTAL_STEPS} steps completed (%p%)"
        )

        self.prev_button.setEnabled(current_step > 1)
        self.next_button.setEnabled(current_step < MESSAGES.TOTAL_STEPS)

        # Show finish button on last step
        if current_step == MESSAGES.TOTAL_STEPS:
            self.next_button.setVisible(False)
            self.finish_button.setVisible(True)
        else:
            self.next_button.setVisible(True)
            self.finish_button.setVisible(False)

        # Update navigation status
        if self.current_step_widget:
            status_text = self.current_step_widget.current_status.value.replace(
                "_", " "
            ).title()
            self.nav_status_label.setText(f"Status: {status_text}")

    def go_to_previous_step(self) -> None:
        """Navigate to the previous step."""
        if self.state.current_step > 1:
            self.navigate_to_step(self.state.current_step - 1)

    def go_to_next_step(self) -> None:
        """Navigate to the next step."""
        if self.state.current_step < MESSAGES.TOTAL_STEPS:
            self.navigate_to_step(self.state.current_step + 1)

    def on_step_status_changed(self, status: StepStatus) -> None:
        """Handle step status changes."""
        self.update_ui()

        status_messages = {
            StepStatus.PENDING: "Step is pending prerequisite completion",
            StepStatus.USER_ACTION_REQUIRED: "User action required to continue",
            StepStatus.AUTOMATION_RUNNING: "Automation is running...",
            StepStatus.COMPLETED: "Step completed successfully",
            StepStatus.FAILED: "Step failed - review and retry",
        }

        message = status_messages.get(status, f"Step status: {status.value}")
        if status_bar := self.statusBar():
            status_bar.showMessage(message)

    def on_step_completed(self, step_id: int) -> None:
        """Handle step completion."""
        self.update_ui()
        self.auto_save_state()

        step_name = MESSAGES.STEP_TITLES.get(step_id, f"Step {step_id}")
        log_step_complete(step_id, step_name)
        if status_bar := self.statusBar():
            status_bar.showMessage(f"'{step_name}' completed successfully!")

    def auto_save_state(self) -> None:
        """Auto-save the current state."""
        try:
            self.state_manager.save_state(self.state)
            self.logger.debug("State auto-saved successfully")
        except Exception as e:
            self.logger.error(f"Auto-save failed: {e}")

    def finish_setup(self) -> None:
        """Complete the setup process."""
        from PyQt6.QtWidgets import QMessageBox

        completed_steps = len(self.state.completed_steps)

        if completed_steps < MESSAGES.TOTAL_STEPS:
            msg = QMessageBox(self)
            msg.setWindowTitle("Setup Incomplete")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText(
                f"Setup is not complete. {completed_steps}/{MESSAGES.TOTAL_STEPS} steps finished."
            )
            msg.setInformativeText("Are you sure you want to finish setup now?")
            msg.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            msg.setDefaultButton(QMessageBox.StandardButton.No)

            if msg.exec() != QMessageBox.StandardButton.Yes:
                return

        msg = QMessageBox(self)
        msg.setWindowTitle("Setup Complete")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText("FLASH-TV setup has been completed!")
        msg.setInformativeText(
            f"Your FLASH-TV system is now configured for participant: {self.state.get_user_input('participant_id', 'Unknown')}"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

        self.state_manager.clear_state()
        self.logger.info("Setup wizard completed successfully")
        self.close()

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """Handle application close event."""
        self.logger.info("Shutting down FLASH-TV Setup Wizard")

        self.process_runner.cleanup_all_processes()
        self.auto_save_state()
        if self.auto_save_timer.isActive():
            self.auto_save_timer.stop()

        if a0 is not None:
            a0.accept()


def main():
    """Main application entry point."""
    if sys.platform == "win32":
        sys.argv += ["-platform", "windows:darkmode=1"]
        sys.argv += ["--style=Fusion"]
    app = QApplication(sys.argv)

    app.setApplicationName(MESSAGES.APP_NAME)
    app.setApplicationVersion(MESSAGES.APP_VERSION)
    app.setOrganizationName(MESSAGES.APP_ORGANIZATION)

    wizard = FlashTVSetupWizard()
    wizard.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
