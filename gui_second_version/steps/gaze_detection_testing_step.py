"""Gaze detection testing step implementation using new framework patterns."""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta

from PyQt6.QtWidgets import QWidget, QMessageBox, QTextEdit, QProgressBar
from PyQt6.QtCore import QTimer

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from utils.ui_factory import ButtonStyle


class GazeDetectionTestingStep(WizardStep):
    """Step 8: Test Gaze Detection using new framework patterns."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Progress tracking for model loading
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self._update_loading_progress)
        self.loading_start_time = None
        self.loading_duration_seconds = 300  # 5 minutes

    def create_content_widget(self) -> QWidget:
        """Create the gaze detection testing UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections in single column
        instructions_section = self._create_instructions_section()
        main_layout.addWidget(instructions_section)

        launch_section = self._create_launch_section()
        main_layout.addWidget(launch_section)

        verification_section = self._create_verification_section()
        main_layout.addWidget(verification_section)

        notes_section = self._create_notes_section()
        main_layout.addWidget(notes_section)

        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        return content

    def _create_instructions_section(self) -> QWidget:
        """Create the setup instructions section."""
        instructions_group, instructions_layout = self.ui_factory.create_group_box(
            "Gaze Testing Setup"
        )

        instructions = self.ui_factory.create_label(
            "Please let the parent(s) and target child know that they will need to participate in a test "
            "where they will actually watch TV for a few minutes."
        )
        instructions_layout.addWidget(instructions)

        return instructions_group

    def _create_launch_section(self) -> QWidget:
        """Create the launch section."""
        launch_group, launch_layout = self.ui_factory.create_group_box(
            "Gaze Detection Test"
        )

        self.launch_button = self.ui_factory.create_action_button(
            "🎯 Launch Gaze Detection Test",
            callback=self._launch_gaze_test,
            style=ButtonStyle.PRIMARY,
            height=40,
        )
        launch_layout.addWidget(self.launch_button)

        # Progress bar for loading countdown
        self.loading_progress_bar = QProgressBar()
        self.loading_progress_bar.setVisible(False)
        self.loading_progress_bar.setMinimum(0)
        self.loading_progress_bar.setMaximum(100)
        self.loading_progress_bar.setValue(0)
        self.loading_progress_bar.setFormat("Estimated loading time: %p% complete")
        self.loading_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        launch_layout.addWidget(self.loading_progress_bar)

        launch_layout.addSpacing(15)

        test_info = self.ui_factory.create_label(
            "<b>Status Indicators:</b><br><br>"
            "<b>Gaze Arrows (on target child):</b><br>"
            "<b style='color: green;'>GREEN arrow</b> = Looking at TV (gaze detected on-screen)<br>"
            "<b style='color: blue;'>BLUE arrow</b> = Looking away from TV (gaze detected off-screen)<br><br>"
            "<b>Face Box Colors:</b><br>"
            "<b style='color: red;'>RED box</b> = Target child (TC) detected but no gaze estimation<br>"
            "<b>No overlay</b> = No faces detected in frame<br><br>"
            "All detected faces are shown with colored boxes based on their verified identity."
        )
        test_info.setWordWrap(True)
        test_info.setMinimumHeight(250)
        test_info.setMaximumHeight(350)
        launch_layout.addWidget(test_info)

        return launch_group

    def _create_verification_section(self) -> QWidget:
        """Create the verification section."""
        verify_group, verify_layout = self.ui_factory.create_group_box(
            "Test Verification"
        )

        verify_text = self.ui_factory.create_label(
            "After running the test, confirm that you observed:\n\n"
            "✓ Face detection working on child and family members\n"
            "✓ Gaze arrows showing direction child is looking\n"
            "✓ Target child correctly identified\n"
            "✓ System responding to child's gaze changes"
        )
        verify_layout.addWidget(verify_text)

        verification_layout = self.ui_factory.create_horizontal_layout(spacing=12)

        self.working_button = self.ui_factory.create_action_button(
            "✅ Gaze Detection Working",
            callback=self._gaze_working_confirmed,
            style=ButtonStyle.SUCCESS,
            height=35,
            enabled=False,
        )
        verification_layout.addWidget(self.working_button, 1)

        self.not_working_button = self.ui_factory.create_action_button(
            "❌ Issues Detected",
            callback=self._gaze_not_working,
            style=ButtonStyle.DANGER,
            height=35,
            enabled=False,
        )
        verification_layout.addWidget(self.not_working_button, 1)

        verify_layout.addLayout(verification_layout)

        return verify_group

    def _create_notes_section(self) -> QWidget:
        """Create notes section for gaze testing observations."""
        notes_group, notes_layout = self.ui_factory.create_group_box("Testing Notes")

        notes_label = self.ui_factory.create_label(
            "Document observations (detection accuracy, environmental factors, issues):"
        )
        notes_layout.addWidget(notes_label)

        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        self.notes_text.setPlaceholderText(
            "Example: Gaze detection accurate when child centered, issues with side angles, bright window behind TV affects detection..."
        )
        notes_layout.addWidget(self.notes_text)

        return notes_group

    def _create_continue_section(self):
        """Create the continue section."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked,
            text="Gaze Detection Verified - Continue"
        )
        self.continue_button.setEnabled(False)

        return button_layout

    @handle_step_error
    def _launch_gaze_test(self, checked: bool = False) -> None:
        """Launch the gaze detection test."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not participant_id or not username:
                self.logger.error("Missing participant ID or username for gaze test")
                QMessageBox.warning(
                    self,
                    "Missing Information",
                    "Participant ID and username are required.",
                )
                raise FlashTVError(
                    "Missing participant ID or username",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first",
                )

            # Combine participant_id and device_id
            full_participant_id = f"{participant_id}{device_id}" if device_id else participant_id

            self.logger.info(f"Starting gaze detection test for participant: {full_participant_id}")
            self.launch_button.setEnabled(False)
            self.update_status(StepStatus.AUTOMATION_RUNNING)

            # Start loading progress bar countdown
            self.loading_progress_bar.setVisible(True)
            self.loading_progress_bar.setValue(0)
            self.loading_start_time = datetime.now()
            self.loading_timer.start(1000)  # Update every second

            # Prepare command for gaze test
            script_path = os.path.join(
                f"/home/{username}/flash-tv-scripts/python_scripts",
                "run_flash_gaze_test.py",
            )

            command = [
                f"/home/{username}/py38/bin/python",
                script_path,
                full_participant_id,
                f"/home/{username}/data/{full_participant_id}_data",
                "save-image",
                username,
            ]

            # Launch the gaze test process
            process_info = self.process_runner.run_script(
                command=command,
                description=f"Gaze detection test for {full_participant_id}",
                working_dir=f"/home/{username}/flash-tv-scripts/python_scripts",
                process_name="gaze_test",
            )

            if process_info:
                self.logger.info("Gaze detection test script started successfully")

                # Enable verification buttons
                self.working_button.setEnabled(True)
                self.not_working_button.setEnabled(True)
            else:
                self.logger.error("Failed to start gaze detection test script")
                self.launch_button.setEnabled(True)
                self.update_status(StepStatus.FAILED)
                raise FlashTVError(
                    "Failed to start gaze detection test",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check script permissions and try again",
                )

        except Exception as e:
            self.logger.error(f"Error launching gaze test: {e}")
            self.launch_button.setEnabled(True)
            self.update_status(StepStatus.FAILED)
            raise

    def _update_loading_progress(self) -> None:
        """Update the loading progress bar based on elapsed time."""
        if self.loading_start_time is None:
            return

        elapsed = (datetime.now() - self.loading_start_time).total_seconds()
        progress_percent = min(100, int((elapsed / self.loading_duration_seconds) * 100))

        self.loading_progress_bar.setValue(progress_percent)

        # Update format text with remaining time
        remaining_seconds = max(0, self.loading_duration_seconds - int(elapsed))
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60

        if progress_percent >= 100:
            self.loading_progress_bar.setFormat("Models loaded - Window should be ready!")
            self.loading_timer.stop()
        else:
            self.loading_progress_bar.setFormat(
                f"Loading models... {minutes}m {seconds}s remaining (~{progress_percent}% complete)"
            )

    @handle_step_error
    def _gaze_working_confirmed(self, checked: bool = False) -> None:
        """Handle confirmation that gaze detection is working."""
        try:
            reply = QMessageBox.question(
                self,
                "Confirm Gaze Detection",
                "Please confirm you observed:\n\n"
                "✓ Face detection working properly\n"
                "✓ Gaze arrows showing on target child\n"
                "✓ Arrows following child's gaze direction\n"
                "✓ System responding to gaze changes\n\n"
                "Is gaze detection working correctly?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("User confirmed gaze detection is working")

                # Stop the loading timer and hide progress bar
                self.loading_timer.stop()
                self.loading_progress_bar.setVisible(False)

                # Stop the gaze test process
                process_info = self.state.get_process("gaze_test")
                if process_info and process_info.is_running():
                    self.logger.info("Terminating gaze test process")
                    self.process_runner.terminate_process("gaze_test")

                # Clean up test files
                self._cleanup_test_files()

                # Mark as complete
                self.state.set_user_input("gaze_detection_verified", True)
                self.state.set_user_input("gaze_test_complete", True)

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)

                QMessageBox.information(
                    self,
                    "Test Complete",
                    "Gaze detection test completed successfully!\nTest files have been cleaned up.",
                )
                self.logger.info("Gaze detection test completed successfully")
            else:
                self.logger.info("User did not confirm gaze detection is working")
                self.output_text.append("\n⚠️ Please verify gaze detection is working before continuing")

        except Exception as e:
            self.logger.error(f"Error during gaze confirmation: {e}")
            raise FlashTVError(
                f"Failed to complete gaze confirmation: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try the verification again",
            )

    def _cleanup_test_files(self) -> None:
        """Clean up test files."""
        try:
            self.logger.info("Starting test file cleanup")

            test_folders = ["test_res", "test_frames"]
            cleaned_folders = 0

            for folder in test_folders:
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                    cleaned_folders += 1
                    self.logger.debug(f"Removed test folder: {folder}")

            self.logger.info(f"Test file cleanup completed - removed {cleaned_folders} folders")

        except Exception as e:
            self.logger.error(f"Error during test file cleanup: {e}")
            # Don't raise error - cleanup failure shouldn't block progress

    @handle_step_error
    def _gaze_not_working(self, checked: bool = False) -> None:
        """Handle gaze detection issues."""
        try:
            self.logger.warning("User reported gaze detection issues")

            # Stop the loading timer and hide progress bar
            self.loading_timer.stop()
            self.loading_progress_bar.setVisible(False)

            # Stop the test process
            process_info = self.state.get_process("gaze_test")
            if process_info and process_info.is_running():
                self.logger.info("Terminating gaze test process due to issues")
                self.process_runner.terminate_process("gaze_test")

            self.launch_button.setEnabled(True)
            self.update_status(StepStatus.FAILED)

            QMessageBox.information(
                self,
                "Gaze Issues",
                "Please check camera positioning, lighting, and gallery quality.\n\n"
                "You can rerun the test after making adjustments.",
            )

            # Reset verification buttons
            self.working_button.setEnabled(False)
            self.not_working_button.setEnabled(False)

        except Exception as e:
            self.logger.error(f"Error handling gaze detection issues: {e}")
            raise FlashTVError(
                f"Failed to handle gaze detection issues: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try restarting the test",
            )

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            if self.state.get_user_input("gaze_detection_verified", False):
                self.logger.info("Gaze detection test step completed successfully")

                # Save notes if any
                notes = self.notes_text.toPlainText().strip()
                if notes:
                    self.state.set_user_input("gaze_detection_notes", notes)
                    self._save_notes_to_file("Gaze Detection Testing", notes)

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but gaze detection not verified")

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete gaze detection step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Verify gaze detection first",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the gaze detection testing step with state restoration."""
        super().activate_step()

        self.logger.info("Gaze detection testing step activated")

        # Load any saved notes
        saved_notes = self.state.get_user_input("gaze_detection_notes", "")
        if saved_notes:
            self.notes_text.setText(saved_notes)

        # Check if already verified
        if self.state.get_user_input("gaze_detection_verified", False):
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)
            self.logger.info("Gaze detection already verified, skipping")

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()

        # Check if gaze test process completed
        process_info = self.state.get_process("gaze_test")
        if process_info and not process_info.is_running():
            status = process_info.get_status()

            # Get output for debugging
            stdout_lines, stderr_lines = process_info.get_output()

            if status.value == "completed":
                self.logger.info("Gaze test process ended normally")
            else:
                self.logger.warning(f"Gaze test process ended with status: {status}")

                # Log error output
                if stderr_lines:
                    for line in stderr_lines[-10:]:  # Log last 10 lines
                        self.logger.error(f"Gaze test stderr: {line}")

            # Reset launch button
            self.launch_button.setEnabled(True)
            # Remove completed process
            self.state.remove_process("gaze_test")

    def deactivate_step(self) -> None:
        """Deactivate step when navigating away - stop timers."""
        try:
            self.logger.info("Deactivating gaze detection testing step")

            # Stop loading timer to prevent resource leaks
            if hasattr(self, "loading_timer") and self.loading_timer.isActive():
                self.loading_timer.stop()
                self.logger.info("Stopped loading timer on deactivation")

        except Exception as e:
            self.logger.error(f"Error during step deactivation: {e}")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Stop loading timer
            if hasattr(self, "loading_timer") and self.loading_timer.isActive():
                self.loading_timer.stop()
                self.logger.info("Stopped loading timer")

            # Stop any running gaze test process
            process_info = self.state.get_process("gaze_test")
            if process_info and process_info.is_running():
                self.logger.info("Terminating gaze test process during cleanup")
                self.process_runner.terminate_process("gaze_test")

            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Gaze detection testing step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
