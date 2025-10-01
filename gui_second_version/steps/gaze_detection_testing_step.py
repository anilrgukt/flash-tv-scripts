"""Gaze detection testing step implementation using new framework patterns."""

from __future__ import annotations

import os
import shutil

from PyQt6.QtWidgets import QWidget, QMessageBox

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from utils.ui_factory import ButtonStyle


class GazeDetectionTestingStep(WizardStep):
    """Step 9: Test Gaze Detection using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the gaze detection testing UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections using UI factory
        top_row = self._create_top_row()
        middle_row = self._create_middle_row()
        bottom_row = self._create_bottom_row()

        main_layout.addLayout(top_row)
        main_layout.addLayout(middle_row)
        main_layout.addLayout(bottom_row)

        # Add notes section
        notes_section = self._create_notes_section()
        main_layout.addWidget(notes_section)

        return content

    def _create_top_row(self):
        """Create the top row with setup and launch sections."""
        top_row_layout = self.ui_factory.create_horizontal_layout(spacing=12)

        # Setup section using UI factory
        setup_section = self._create_setup_section()
        top_row_layout.addWidget(setup_section, 1)

        # Launch section using UI factory
        launch_section = self._create_launch_section()
        top_row_layout.addWidget(launch_section, 1)

        return top_row_layout

    def _create_setup_section(self) -> QWidget:
        """Create the setup instructions section using UI factory."""
        setup_group, setup_layout = self.ui_factory.create_group_box(
            "Gaze Testing Setup"
        )

        instructions = self.ui_factory.create_label(
            "Testing Preparation:\n\n"
            "1. Position target child 3-6 feet from TV at eye level\n"
            "2. Turn on TV with engaging content (cartoons work well)\n"
            "3. Ensure good room lighting (not too dark)\n"
            "4. Have child look at TV, then away, then back at TV\n"
            "5. Verify camera can see child's face clearly"
        )
        setup_layout.addWidget(instructions)

        self.setup_check = self.ui_factory.create_checkbox(
            "✓ Child is positioned and TV is on", callback=self._update_test_readiness
        )
        setup_layout.addWidget(self.setup_check)
        setup_layout.addStretch()

        return setup_group

    def _create_launch_section(self) -> QWidget:
        """Create the launch section using UI factory."""
        launch_group, launch_layout = self.ui_factory.create_group_box(
            "Gaze Detection Test"
        )

        self.launch_button = self.ui_factory.create_action_button(
            "🎯 Launch Gaze Detection Test",
            callback=self._launch_gaze_test,
            style=ButtonStyle.PRIMARY,
            height=35,
            enabled=False,
        )
        launch_layout.addWidget(self.launch_button)

        test_info = self.ui_factory.create_label(
            "This will start the FLASH-TV gaze detection system.\n\n"
            "Arrow Color Meanings:\n"
            "• GREEN arrow = Looking at TV (gaze detected on-screen)\n"
            "• BLUE arrow = Looking away from TV (gaze detected off-screen)\n\n"
            "Face Box Colors:\n"
            "• BLUE box = Target child (TC)\n"
            "• GREEN box = Parent or sibling\n"
            "• WHITE box = Unidentified face"
        )
        launch_layout.addWidget(test_info)
        launch_layout.addStretch()

        return launch_group

    def _create_middle_row(self):
        """Create the middle row with status and verification sections."""
        middle_row_layout = self.ui_factory.create_horizontal_layout(spacing=12)

        # Status section using UI factory
        status_section = self._create_status_section()
        middle_row_layout.addWidget(status_section, 1)

        # Verification section using UI factory
        verify_section = self._create_verification_section()
        middle_row_layout.addWidget(verify_section, 1)

        return middle_row_layout

    def _create_status_section(self) -> QWidget:
        """Create the test status section using UI factory."""
        status_group, status_layout = self.ui_factory.create_group_box("Test Status")

        self.test_status_label = self.ui_factory.create_status_label(
            "🎯 Gaze test not started", status_type="info"
        )
        status_layout.addWidget(self.test_status_label)

        self.output_text = self.ui_factory.create_text_area(
            placeholder="Gaze test output will appear here...",
            max_height=120,
            read_only=True,
        )
        status_layout.addWidget(self.output_text)

        return status_group

    def _create_verification_section(self) -> QWidget:
        """Create the verification section using UI factory."""
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

        verification_layout = self.ui_factory.create_vertical_layout(spacing=6)

        self.working_button = self.ui_factory.create_action_button(
            "✅ Gaze Detection Working",
            callback=self._gaze_working_confirmed,
            style=ButtonStyle.SUCCESS,
            height=30,
            enabled=False,
        )
        verification_layout.addWidget(self.working_button)

        self.not_working_button = self.ui_factory.create_action_button(
            "❌ Issues Detected",
            callback=self._gaze_not_working,
            style=ButtonStyle.DANGER,
            height=30,
            enabled=False,
        )
        verification_layout.addWidget(self.not_working_button)

        verify_layout.addLayout(verification_layout)

        return verify_group

    def _create_bottom_row(self):
        """Create the bottom row with help and continue sections."""
        bottom_row_layout = self.ui_factory.create_horizontal_layout(spacing=12)

        # Help section using UI factory
        help_section = self._create_help_section()
        bottom_row_layout.addWidget(help_section, 1)

        # Continue section using UI factory
        continue_section = self._create_continue_section()
        bottom_row_layout.addWidget(continue_section, 1)

        return bottom_row_layout

    def _create_help_section(self) -> QWidget:
        """Create the help section using UI factory."""
        help_group, help_layout = self.ui_factory.create_group_box("Troubleshooting")

        self.help_button = self.ui_factory.create_action_button(
            "❓ Gaze Detection Help",
            callback=self._show_gaze_help,
            style=ButtonStyle.SECONDARY,
            height=30,
        )
        help_layout.addWidget(self.help_button)
        help_layout.addStretch()

        return help_group

    def _create_notes_section(self) -> QWidget:
        """Create notes section for gaze testing observations."""
        from PyQt6.QtWidgets import QTextEdit

        notes_group, notes_layout = self.ui_factory.create_group_box("Testing Notes")

        notes_label = self.ui_factory.create_label(
            "Document observations (detection accuracy, environmental factors, issues):"
        )
        notes_layout.addWidget(notes_label)

        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(100)
        self.notes_text.setPlaceholderText(
            "Example: Gaze detection accurate when child centered, issues with side angles, bright window behind TV affects detection..."
        )
        notes_layout.addWidget(self.notes_text)

        return notes_group

    def _create_continue_section(self) -> QWidget:
        """Create the continue section using UI factory."""
        continue_group, continue_layout = self.ui_factory.create_group_box("Next Step")

        self.continue_button = self.ui_factory.create_action_button(
            "Gaze Detection Verified - Continue",
            callback=self._on_continue_clicked,
            style=ButtonStyle.SUCCESS,
            height=30,
            enabled=False,
        )
        continue_layout.addWidget(self.continue_button)
        continue_layout.addStretch()

        return continue_group

    @handle_step_error
    def _update_test_readiness(self, checked: bool = False) -> None:
        """Update test launch button based on readiness with logging."""
        try:
            is_ready = self.setup_check.isChecked()
            self.launch_button.setEnabled(is_ready)

            if is_ready:
                self.logger.debug("Gaze test ready - setup completed")
            else:
                self.logger.debug("Gaze test not ready - setup incomplete")

        except Exception as e:
            self.logger.error(f"Error updating test readiness: {e}")
            raise FlashTVError(
                f"Failed to update test readiness: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try checking the setup box again",
            )

    @handle_step_error
    def _launch_gaze_test(self, checked: bool = False) -> None:
        """Launch the gaze detection test with comprehensive error handling."""
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

            self.logger.info(
                f"Starting gaze detection test for participant: {full_participant_id}"
            )
            self.launch_button.setEnabled(False)
            self.test_status_label.setText("🎯 Launching gaze detection test...")
            self.update_status(StepStatus.AUTOMATION_RUNNING)

            # Prepare command for gaze test - use the new real-time testing script
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
                self.test_status_label.setText("✅ Gaze detection test running")
                self.output_text.append("Gaze detection test started...")
                self.output_text.append(
                    "Watch for face detection boxes and gaze arrows"
                )
                self.output_text.append(
                    "Test the system by having child look at different areas"
                )
                self.output_text.append("\nObserve the following:")
                self.output_text.append("• Face detection boxes around all faces")
                self.output_text.append("• Gaze direction arrows on target child")
                self.output_text.append("• System tracking child's gaze changes")

                # Enable verification buttons
                self.working_button.setEnabled(True)
                self.not_working_button.setEnabled(True)
            else:
                self.logger.error("Failed to start gaze detection test script")
                self.test_status_label.setText("❌ Failed to launch gaze test")
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

    @handle_step_error
    def _gaze_working_confirmed(self, checked: bool = False) -> None:
        """Handle confirmation that gaze detection is working with comprehensive validation."""
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
                self.output_text.append(
                    "\n⚠️ Please verify gaze detection is working before continuing"
                )

        except Exception as e:
            self.logger.error(f"Error during gaze confirmation: {e}")
            raise FlashTVError(
                f"Failed to complete gaze confirmation: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try the verification again",
            )

    def _cleanup_test_files(self) -> None:
        """Clean up test files with error handling."""
        try:
            self.output_text.append("\n🧹 Cleaning up test files...")
            self.logger.info("Starting test file cleanup")

            test_folders = ["test_res", "test_frames"]
            cleaned_folders = 0

            for folder in test_folders:
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                    self.output_text.append(f"Removed {folder}/")
                    cleaned_folders += 1
                    self.logger.debug(f"Removed test folder: {folder}")

            self.output_text.append("✅ Test cleanup completed")
            self.logger.info(
                f"Test file cleanup completed - removed {cleaned_folders} folders"
            )

        except Exception as e:
            self.logger.error(f"Error during test file cleanup: {e}")
            self.output_text.append(f"⚠️ Cleanup error: {e}")
            # Don't raise error - cleanup failure shouldn't block progress

    @handle_step_error
    def _gaze_not_working(self, checked: bool = False) -> None:
        """Handle gaze detection issues with comprehensive error handling."""
        try:
            self.logger.warning("User reported gaze detection issues")

            # Stop the test process
            process_info = self.state.get_process("gaze_test")
            if process_info and process_info.is_running():
                self.logger.info("Terminating gaze test process due to issues")
                self.process_runner.terminate_process("gaze_test")

            self.test_status_label.setText("❌ Gaze detection issues detected")
            self.launch_button.setEnabled(True)
            self.update_status(StepStatus.FAILED)

            QMessageBox.information(
                self,
                "Gaze Issues",
                "Please check camera positioning, lighting, and gallery quality.\n"
                "Try the troubleshooting steps in the Help section.\n\n"
                "You can rerun the test after making adjustments.",
            )

            self.output_text.append("\n❌ Test failed - troubleshooting needed")
            self.output_text.append(
                "Check: camera position, lighting, face gallery quality"
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
    def _show_gaze_help(self, checked: bool = False) -> None:
        """Show gaze detection troubleshooting help with logging."""
        try:
            self.logger.info("Showing gaze detection help dialog")

            help_text = """Gaze Detection Troubleshooting:

Common Issues:
• No face detection boxes:
  - Check camera positioning and focus
  - Verify adequate lighting
  - Ensure faces are clearly visible

• No gaze arrows:
  - Target child may not be identified
  - Check face gallery quality
  - Verify child is in camera view

• Incorrect gaze direction:
  - Camera angle may need adjustment
  - Check for reflections on TV screen
  - Verify child is looking at TV

• Poor performance:
  - Too many people in frame
  - Insufficient lighting
  - Camera too far from child

Solutions:
• Adjust camera angle/position
• Improve room lighting
• Rebuild face gallery if needed
• Check camera focus and cleanliness

The gaze detection system tracks where the target child is looking relative to the TV screen."""

            QMessageBox.information(self, "Gaze Detection Help", help_text)

        except Exception as e:
            self.logger.error(f"Error showing gaze help: {e}")
            raise FlashTVError(
                f"Failed to show help dialog: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try clicking help again",
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
            self.test_status_label.setText("✅ Gaze detection already verified")
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
                self.output_text.append("\n⚠️ Gaze test process ended")
                self.output_text.append("Please verify if testing was successful")
            else:
                self.logger.warning(f"Gaze test process ended with status: {status}")
                self.output_text.append(f"\n❌ Process failed with status: {status}")
                
                # Show error output
                if stderr_lines:
                    self.output_text.append("\nError output:")
                    for line in stderr_lines[-10:]:  # Show last 10 lines
                        self.output_text.append(f"  {line}")
                        self.logger.error(f"Gaze test stderr: {line}")
                
                if stdout_lines:
                    self.output_text.append("\nLast output:")
                    for line in stdout_lines[-5:]:  # Show last 5 lines
                        self.output_text.append(f"  {line}")

            # Reset launch button
            self.launch_button.setEnabled(True)
            # Remove completed process
            self.state.remove_process("gaze_test")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
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
