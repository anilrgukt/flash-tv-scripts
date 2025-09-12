"""Log file verification step implementation using new framework patterns."""

from __future__ import annotations

import os
import shutil

from PyQt6.QtWidgets import QWidget, QMessageBox, QListWidget, QListWidgetItem
from PyQt6.QtCore import QTimer

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from utils.ui_factory import ButtonStyle


class LogFileVerificationStep(WizardStep):
    """Step 10: Log File Verification using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the log file verification UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections using UI factory
        overview_section = self._create_overview_section()
        top_row = self._create_top_row()
        middle_row = self._create_middle_row()
        continue_section = self._create_continue_section()

        main_layout.addWidget(overview_section)
        main_layout.addLayout(top_row)
        main_layout.addLayout(middle_row, 1)
        main_layout.addLayout(continue_section)

        # Test timer
        self.test_timer = QTimer()
        self.test_timer.setSingleShot(True)
        self.test_timer.timeout.connect(self._test_complete)

        return content

    def _create_overview_section(self) -> QWidget:
        """Create the overview section using UI factory."""
        overview_group, overview_layout = self.ui_factory.create_group_box(
            "Log File Verification Overview"
        )

        overview_text = self.ui_factory.create_label(
            "This step verifies that FLASH-TV is generating log files correctly. "
            "We'll run a brief test to check data collection and log file creation. "
            "The test will run for 30 seconds with the target child in view."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_top_row(self):
        """Create the top row with test details and control."""
        top_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Test details section
        test_details_section = self._create_test_details_section()
        control_section = self._create_control_section()

        top_row.addWidget(test_details_section, 3)  # 60% width
        top_row.addWidget(control_section, 2)  # 40% width

        return top_row

    def _create_test_details_section(self) -> QWidget:
        """Create the test details section using UI factory."""
        test_overview_group, test_overview_layout = self.ui_factory.create_group_box(
            "Log File Test Details"
        )

        test_info = self.ui_factory.create_label(
            "The test will:\n"
            "• Start FLASH-TV data collection for 30 seconds\n"
            "• Check for proper log file generation\n"
            "• Verify timestamp formatting and data structure\n"
            "• Confirm gaze detection data is being recorded\n\n"
            "During the test:\n"
            "• Have the target child sit in viewing position\n"
            "• Child should look at the TV occasionally\n"
            "• Test will run for 30 seconds\n"
            "• Log files will be checked automatically"
        )
        test_overview_layout.addWidget(test_info)
        test_overview_layout.addStretch()

        return test_overview_group

    def _create_control_section(self) -> QWidget:
        """Create the control section using UI factory."""
        control_group, control_layout = self.ui_factory.create_group_box("Test Control")

        self.test_button = self.ui_factory.create_action_button(
            "🗂️ Run Log File Test",
            callback=self._run_log_test,
            style=ButtonStyle.PRIMARY,
            height=40,
        )
        control_layout.addWidget(self.test_button)

        control_layout.addSpacing(10)

        self.test_status_label = self.ui_factory.create_status_label(
            "🗂️ Log test not started", status_type="info"
        )
        control_layout.addWidget(self.test_status_label)
        control_layout.addStretch()

        return control_group

    def _create_middle_row(self):
        """Create the middle row with output and results."""
        middle_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Output and results sections
        output_section = self._create_output_section()
        results_section = self._create_results_section()

        middle_row.addWidget(output_section, 1)  # 50% width
        middle_row.addWidget(results_section, 1)  # 50% width

        return middle_row

    def _create_output_section(self) -> QWidget:
        """Create the output section using UI factory."""
        output_group, output_layout = self.ui_factory.create_group_box("Test Progress")

        self.output_text = self.ui_factory.create_text_area(
            placeholder="Log file test progress will appear here...", read_only=True
        )
        output_layout.addWidget(self.output_text)

        return output_group

    def _create_results_section(self) -> QWidget:
        """Create the results section using UI factory."""
        results_group, results_layout = self.ui_factory.create_group_box(
            "Log File Analysis"
        )

        self.log_files_list = QListWidget()
        results_layout.addWidget(self.log_files_list)

        # Verification buttons
        verification_layout = self.ui_factory.create_horizontal_layout(spacing=8)

        self.logs_good_button = self.ui_factory.create_action_button(
            "✅ Log Files Look Good",
            callback=self._logs_verified,
            style=ButtonStyle.SUCCESS,
            height=30,
            enabled=False,
        )
        verification_layout.addWidget(self.logs_good_button)

        self.logs_problem_button = self.ui_factory.create_action_button(
            "❌ Log File Issues",
            callback=self._logs_have_issues,
            style=ButtonStyle.DANGER,
            height=30,
            enabled=False,
        )
        verification_layout.addWidget(self.logs_problem_button)

        results_layout.addLayout(verification_layout)

        return results_group

    def _create_continue_section(self):
        """Create the continue button section using UI factory."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text="Log Files Verified - Continue"
        )

        return button_layout

    @handle_step_error
    def _run_log_test(self, checked: bool = False) -> None:
        """Run the log file generation test with comprehensive error handling."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")
            
            # Debug logging
            self.logger.info(f"Retrieved from state - participant_id: '{participant_id}', device_id: '{device_id}', username: '{username}'")
            
            # Combine participant_id and device_id (handle empty/None device_id)
            if device_id:
                full_participant_id = f"{participant_id}{device_id}"
            else:
                full_participant_id = participant_id
                self.logger.warning(f"Device ID is empty/None - using only participant_id: '{participant_id}'")
            
            self.logger.info(f"Constructed full_participant_id: '{full_participant_id}'")

            if not participant_id or not username:
                self.logger.error("Missing participant ID or username for log test")
                self.output_text.append("❌ Missing required information")
                raise FlashTVError(
                    "Missing participant ID or username",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first",
                )

            self.logger.info(
                f"Starting log file test for participant: {participant_id}"
            )

            self.test_button.setEnabled(False)
            self.test_status_label.setText("🗂️ Starting log file test...")
            self.update_status(StepStatus.AUTOMATION_RUNNING)

            # Clear previous results
            self.log_files_list.clear()
            self.output_text.clear()

            # Prepare command for short data collection test
            # Use expanduser to get the correct path relative to home directory
            script_path = os.path.expanduser("~/flash-tv-scripts/python_scripts/run_flash_data_collection.py")
            working_dir = os.path.expanduser("~/flash-tv-scripts/python_scripts")

            command = [
                f"/home/{username}/py38/bin/python",
                script_path,
                full_participant_id,
                f"/home/{username}/data/{full_participant_id}_data",
                "save-image",
                username,
            ]

            # Launch the test process
            process_info = self.process_runner.run_script(
                command=command,
                description=f"Log file test for {full_participant_id}",
                working_dir=working_dir,
                process_name="log_test",
            )

            if process_info:
                self.logger.info("Log file test script started successfully")
                self.test_status_label.setText("✅ Log test running (30 seconds)")
                self.output_text.append("Log file test started...")
                self.output_text.append("Data collection will run for 30 seconds")
                self.output_text.append("Please have child look at TV occasionally")

                # Set timer for 30 seconds
                self.test_timer.start(30000)
            else:
                self.logger.error("Failed to start log file test script")
                self.test_status_label.setText("❌ Failed to start log test")
                self.test_button.setEnabled(True)
                self.update_status(StepStatus.FAILED)
                raise FlashTVError(
                    "Failed to start log file test",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check script permissions and try again",
                )

        except Exception as e:
            self.logger.error(f"Error running log test: {e}")
            self.test_button.setEnabled(True)
            self.update_status(StepStatus.FAILED)
            raise

    @handle_step_error
    def _test_complete(self) -> None:
        """Handle test completion after 30 seconds with comprehensive error handling."""
        try:
            self.logger.info("Log file test timer completed (30 seconds)")

            # Stop the test process
            process_info = self.state.get_process("log_test")
            if process_info and process_info.is_running():
                self.logger.info("Terminating log test process")
                self.process_runner.terminate_process("log_test")

            self.test_status_label.setText("✅ Test complete - analyzing log files")
            self.output_text.append("\n🗂️ Test complete - checking log files...")

            # Analyze log files
            self._analyze_log_files()

        except Exception as e:
            self.logger.error(f"Error during test completion: {e}")
            raise FlashTVError(
                f"Failed to complete log test: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try running the test again",
            )

    @handle_step_error
    def _analyze_log_files(self) -> None:
        """Analyze generated log files with comprehensive error handling."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")
            
            # Debug logging
            self.logger.info(f"Retrieved from state for analysis - participant_id: '{participant_id}', device_id: '{device_id}', username: '{username}'")
            
            # Combine participant_id and device_id (handle empty/None device_id)
            if device_id:
                full_participant_id = f"{participant_id}{device_id}"
            else:
                full_participant_id = participant_id
                self.logger.warning(f"Device ID is empty/None for analysis - using only participant_id: '{participant_id}'")
            
            self.logger.info(f"Constructed full_participant_id for analysis: '{full_participant_id}'")

            if not participant_id or not username:
                self.logger.warning(
                    "Missing participant ID or username for log analysis"
                )
                return

            self.logger.info(f"Analyzing log files for participant: {full_participant_id}")

            data_path = f"/home/{username}/data/{full_participant_id}_data"

            if not os.path.exists(data_path):
                self.logger.error(f"Data directory not found: {data_path}")
                self.output_text.append(f"❌ Data directory not found: {data_path}")
                self.logs_problem_button.setEnabled(True)
                raise FlashTVError(
                    f"Data directory not found: {data_path}",
                    ErrorType.SYSTEM_ERROR,
                    recovery_action="Check data path configuration",
                )

            # Look for log files
            log_files = []
            for file in os.listdir(data_path):
                if file.startswith(f"{full_participant_id}_flash_log") and file.endswith(
                    ".txt"
                ):
                    log_files.append(file)

            if not log_files:
                self.logger.warning("No log files found in data directory")
                self.output_text.append("❌ No log files found")
                self.logs_problem_button.setEnabled(True)
                raise FlashTVError(
                    "No log files found",
                    ErrorType.SYSTEM_ERROR,
                    recovery_action="Run the test again or check data permissions",
                )

            # Analyze each log file
            self.logger.info(f"Found {len(log_files)} log files for analysis")
            self.output_text.append(f"✅ Found {len(log_files)} log file(s)")

            for log_file in log_files:
                log_path = os.path.join(data_path, log_file)

                # Check file size
                file_size = os.path.getsize(log_path)

                # Add to list widget
                item = QListWidgetItem(f"{log_file} ({file_size} bytes)")
                self.log_files_list.addItem(item)

                # Basic content check
                if file_size > 0:
                    try:
                        with open(log_path, "r") as f:
                            lines = f.readlines()
                            if len(lines) > 1:  # Header + at least one data line
                                self.output_text.append(
                                    f"✅ {log_file}: {len(lines)} lines"
                                )
                            else:
                                self.output_text.append(
                                    f"⚠️ {log_file}: Only {len(lines)} lines"
                                )
                    except Exception as file_error:
                        self.logger.error(
                            f"Error reading log file {log_file}: {file_error}"
                        )
                        self.output_text.append(
                            f"❌ Error reading {log_file}: {file_error}"
                        )
                else:
                    self.logger.warning(f"Log file {log_file} is empty")
                    self.output_text.append(f"⚠️ {log_file}: Empty file")

            # Enable verification buttons
            self.logs_good_button.setEnabled(True)
            self.logs_problem_button.setEnabled(True)

            self.output_text.append("\n🔍 Please verify the log files look correct")
            self.logger.info("Log file analysis completed successfully")

        except Exception as e:
            self.logger.error(f"Error analyzing log files: {e}")
            self.output_text.append(f"Error analyzing logs: {e}")
            self.logs_problem_button.setEnabled(True)
            raise

    @handle_step_error
    def _logs_verified(self) -> None:
        """Handle log verification confirmation with comprehensive validation."""
        try:
            self.logger.info("User initiated log file verification")

            reply = QMessageBox.question(
                self,
                "Confirm Log Files",
                "Please confirm the log files meet these criteria:\n\n"
                "✓ At least one log file was generated\n"
                "✓ Log files contain data (not empty)\n"
                "✓ File names include participant ID\n"
                "✓ Multiple lines of data were recorded\n\n"
                "Are the log files properly generated?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("User confirmed log files are properly generated")

                # Clean up test files/folders
                self._cleanup_test_data()

                # Mark as complete
                self.state.set_user_input("log_files_verified", True)
                self.state.set_user_input("log_test_complete", True)

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)

                QMessageBox.information(
                    self,
                    "Verification Complete",
                    "Log file verification completed successfully!\n"
                    "FLASH-TV is properly generating data logs.",
                )
                self.logger.info("Log file verification completed successfully")
            else:
                self.logger.info(
                    "User did not confirm log files are properly generated"
                )
                self.output_text.append("\n⚠️ Please check log file generation settings")

        except Exception as e:
            self.logger.error(f"Error during log verification: {e}")
            raise FlashTVError(
                f"Failed to complete log verification: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try the verification again",
            )

    @handle_step_error
    def _logs_have_issues(self) -> None:
        """Handle log file issues with comprehensive error handling."""
        try:
            self.logger.warning("User reported log file issues")

            # Stop any running process
            process_info = self.state.get_process("log_test")
            if process_info and process_info.is_running():
                self.logger.info("Terminating log test process due to issues")
                self.process_runner.terminate_process("log_test")

            self.test_status_label.setText("❌ Log file issues detected")
            self.test_button.setEnabled(True)
            self.update_status(StepStatus.FAILED)

            QMessageBox.information(
                self,
                "Log Issues",
                "Log file generation issues detected.\n\n"
                "Common issues:\n"
                "• No log files created\n"
                "• Empty log files\n"
                "• Permission problems\n"
                "• Data path issues\n\n"
                "Check face gallery and camera setup, then rerun the test.",
            )

            self.output_text.append("\n❌ Test failed - troubleshooting needed")
            self.output_text.append(
                "Check: data permissions, face gallery, camera connection"
            )

            # Reset verification buttons
            self.logs_good_button.setEnabled(False)
            self.logs_problem_button.setEnabled(False)

        except Exception as e:
            self.logger.error(f"Error handling log file issues: {e}")
            raise FlashTVError(
                f"Failed to handle log file issues: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try restarting the test",
            )

    def _cleanup_test_data(self) -> None:
        """Clean up test data files with error handling."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")
            
            # Combine participant_id and device_id (handle empty/None device_id)
            if device_id:
                full_participant_id = f"{participant_id}{device_id}"
            else:
                full_participant_id = participant_id
                self.logger.warning(f"Device ID is empty/None for cleanup - using only participant_id: '{participant_id}'")

            if participant_id and username:
                self.output_text.append("\n🧹 Cleaning up test data...")
                self.logger.info("Starting test data cleanup")

                # Clean up any test image folders
                test_folders = ["test_res", "test_frames", "temp_images"]
                cleaned_folders = 0

                for folder in test_folders:
                    if os.path.exists(folder):
                        shutil.rmtree(folder)
                        self.output_text.append(f"Removed {folder}/")
                        cleaned_folders += 1
                        self.logger.debug(f"Removed test folder: {folder}")

                self.output_text.append("✅ Test cleanup completed")
                self.logger.info(
                    f"Test data cleanup completed - removed {cleaned_folders} folders"
                )

        except Exception as e:
            self.logger.error(f"Error during test data cleanup: {e}")
            self.output_text.append(f"⚠️ Cleanup error: {e}")
            # Don't raise error - cleanup failure shouldn't block progress

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            if self.state.get_user_input("log_files_verified", False):
                self.logger.info("Log file verification step completed successfully")

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but log files not verified")

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete log verification step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Verify log files first",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the log file verification step with state restoration."""
        super().activate_step()

        self.logger.info("Log file verification step activated")

        # Check if already verified
        if self.state.get_user_input("log_files_verified", False):
            self.test_status_label.setText("✅ Log files already verified")
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)
            self.logger.info("Log files already verified, skipping")

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()

        # Check log test process status
        process_info = self.state.get_process("log_test")
        if process_info and not process_info.is_running():
            status = process_info.get_status()
            if status.value == "completed":
                self.logger.info("Log test process ended normally")
                self.output_text.append("\n⚠️ Log test process ended")
                self.output_text.append("Please verify if testing was successful")
            else:
                self.logger.warning(f"Log test process ended with status: {status}")

            # Reset test button
            self.test_button.setEnabled(True)
            # Remove completed process
            self.state.remove_process("log_test")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Stop test timer if active
            if self.test_timer.isActive():
                self.test_timer.stop()
                self.logger.info("Stopped test timer during cleanup")

            # Stop any running log test process
            process_info = self.state.get_process("log_test")
            if process_info and process_info.is_running():
                self.logger.info("Terminating log test process during cleanup")
                self.process_runner.terminate_process("log_test")

            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Log file verification step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")

    def cleanup(self) -> None:
        """Clean up resources when step is destroyed."""
        self._cleanup_step_resources()
        super().cleanup()
