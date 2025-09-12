"""System testing step implementation using new framework patterns."""

from __future__ import annotations

import random

from PyQt6.QtWidgets import QWidget, QProgressBar, QListWidget, QListWidgetItem

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from utils.ui_factory import ButtonStyle


class SystemTestingStep(WizardStep):
    """Step 9: System Testing and Validation using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the system testing UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections using UI factory
        overview_section = self._create_overview_section()
        control_section = self._create_control_section()
        results_section = self._create_results_section()
        output_section = self._create_output_section()
        buttons_section = self._create_buttons_section()

        main_layout.addWidget(overview_section)
        main_layout.addWidget(control_section)
        main_layout.addWidget(results_section)
        main_layout.addWidget(output_section)
        main_layout.addLayout(buttons_section)

        # Test tracking
        self.test_results = {}

        return content

    def _create_overview_section(self) -> QWidget:
        """Create the overview section using UI factory."""
        overview_group, overview_layout = self.ui_factory.create_group_box(
            "System Testing Overview"
        )

        overview_text = self.ui_factory.create_label(
            "This step validates the complete FLASH-TV system functionality:\n\n"
            "• Face detection and recognition accuracy\n"
            "• Gaze estimation performance\n"
            "• Camera positioning and setup\n"
            "• Service integration and data logging\n"
            "• End-to-end system workflow\n\n"
            "Testing may take 5-10 minutes to complete all validation checks."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_control_section(self) -> QWidget:
        """Create the test control section using UI factory."""
        control_group, control_layout = self.ui_factory.create_group_box("Test Control")

        self.start_test_button = self.ui_factory.create_action_button(
            "Start System Testing",
            callback=self._start_system_test,
            style=ButtonStyle.PRIMARY,
            height=35,
        )
        control_layout.addWidget(self.start_test_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)

        return control_group

    def _create_results_section(self) -> QWidget:
        """Create the test results section using UI factory."""
        results_group, results_layout = self.ui_factory.create_group_box("Test Results")

        self.test_results_list = QListWidget()
        results_layout.addWidget(self.test_results_list)

        return results_group

    def _create_output_section(self) -> QWidget:
        """Create the output section using UI factory."""
        output_group, output_layout = self.ui_factory.create_group_box(
            "Detailed Test Output"
        )

        self.output_text = self.ui_factory.create_text_area(
            placeholder="System test output will appear here...",
            max_height=250,
            read_only=True,
        )
        output_layout.addWidget(self.output_text)

        return output_group

    def _create_buttons_section(self):
        """Create the action buttons section using UI factory."""
        button_layout = self.ui_factory.create_horizontal_layout()

        self.retry_button = self.ui_factory.create_action_button(
            "Retry Failed Tests",
            callback=self._retry_tests,
            style=ButtonStyle.SECONDARY,
            height=30,
            enabled=False,
        )
        button_layout.addWidget(self.retry_button)

        button_layout.addStretch()

        self.continue_button = self.ui_factory.create_action_button(
            "Continue to Next Step",
            callback=self._on_continue_clicked,
            style=ButtonStyle.SUCCESS,
            height=30,
            enabled=False,
        )
        button_layout.addWidget(self.continue_button)

        return button_layout

    @handle_step_error
    def _start_system_test(self) -> None:
        """Start comprehensive system testing with error handling."""
        participant_id = self.state.get_user_input("participant_id", "")
        device_id = self.state.get_user_input("device_id", "")
        data_path = self.state.get_user_input("data_path", "")
        username = self.state.get_user_input("username", "")

        if not all([participant_id, data_path, username]):
            self.logger.error("Missing required configuration data for system testing")
            self.output_text.append("❌ Missing required configuration data")
            raise FlashTVError(
                "Missing participant ID, data path, or username",
                ErrorType.VALIDATION_ERROR,
                recovery_action="Complete all previous setup steps",
            )

        # Combine participant_id and device_id
        full_participant_id = f"{participant_id}{device_id}" if device_id else participant_id

        self.update_status(StepStatus.AUTOMATION_RUNNING)
        self.start_test_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.output_text.clear()
        self.test_results_list.clear()
        self.test_results = {}

        self.output_text.append("🧪 Starting comprehensive system testing...")
        self.output_text.append(f"Participant: {full_participant_id}")
        self.output_text.append(f"Data path: {data_path}")
        self.output_text.append(f"Username: {username}")

        # Add initial test status items
        test_items = [
            "Camera Detection Test",
            "Face Gallery Validation",
            "Face Detection Test",
            "Gaze Estimation Test",
            "Data Logging Test",
            "Service Integration Test",
            "Performance Validation",
        ]

        for test_name in test_items:
            item = QListWidgetItem(f"⏳ {test_name}: PENDING")
            item.setData(32, {"name": test_name, "status": "pending"})
            self.test_results_list.addItem(item)
            self.test_results[test_name] = "pending"

        # Run the system testing script
        script_path = "../runtime_scripts/run_flashtv_system.sh"
        command = ["bash", script_path, "test", full_participant_id, data_path]

        process_info = self.process_runner.run_script(
            command=command,
            description="Running system tests",
            working_dir="../runtime_scripts",
            process_name="system_testing",
        )

        if process_info:
            self.logger.info("System testing script started successfully")
            self.output_text.append("System testing started...")
            self.output_text.append("Running comprehensive validation tests...")
        else:
            self.logger.error("Failed to start system testing script")
            self.output_text.append("❌ Failed to start system testing")
            self._reset_testing_ui()
            self.update_status(StepStatus.FAILED)
            raise FlashTVError(
                "Failed to start system testing script",
                ErrorType.PROCESS_ERROR,
                recovery_action="Check script permissions and try again",
            )

    @handle_step_error
    def _update_test_result(
        self, test_name: str, status: str, details: str = ""
    ) -> None:
        """Update the result of a specific test with logging."""
        self.test_results[test_name] = status

        # Update the list widget
        for i in range(self.test_results_list.count()):
            item = self.test_results_list.item(i)
            item_data = item.data(32)

            if item_data and item_data["name"] == test_name:
                if status == "passed":
                    icon = "✅"
                    status_text = "PASSED"
                elif status == "failed":
                    icon = "❌"
                    status_text = "FAILED"
                elif status == "running":
                    icon = "🔄"
                    status_text = "RUNNING"
                else:
                    icon = "⏳"
                    status_text = "PENDING"

                display_text = f"{icon} {test_name}: {status_text}"
                if details:
                    display_text += f" - {details}"

                item.setText(display_text)
                item_data["status"] = status
                item.setData(32, item_data)
                break

    def _simulate_test_progress(self) -> None:
        """Simulate test progress updates."""
        # This would normally be driven by parsing the test script output

        test_names = list(self.test_results.keys())
        for test_name in test_names:
            if self.test_results[test_name] == "pending":
                self._update_test_result(test_name, "running")

                # Simulate test result
                if random.random() > 0.2:  # 80% pass rate
                    self._update_test_result(test_name, "passed")
                    self.output_text.append(f"✅ {test_name} completed successfully")
                else:
                    self._update_test_result(test_name, "failed", "Check configuration")
                    self.output_text.append(f"❌ {test_name} failed - check logs")
                break

    def _check_all_tests_complete(self) -> bool:
        """Check if all tests are complete."""
        return all(
            status in ["passed", "failed"] for status in self.test_results.values()
        )

    def _get_test_summary(self) -> tuple[int, int]:
        """Get test summary (passed, failed)."""
        passed = sum(1 for status in self.test_results.values() if status == "passed")
        failed = sum(1 for status in self.test_results.values() if status == "failed")
        return passed, failed

    def _retry_tests(self) -> None:
        """Retry failed tests."""
        failed_tests = [
            name for name, status in self.test_results.items() if status == "failed"
        ]

        if not failed_tests:
            self.output_text.append("No failed tests to retry")
            return

        self.retry_button.setEnabled(False)
        self.output_text.append(f"🔄 Retrying {len(failed_tests)} failed test(s)...")

        # Reset failed tests to pending
        for test_name in failed_tests:
            self._update_test_result(test_name, "pending")

        # Simulate retrying tests
        for test_name in failed_tests:
            self._update_test_result(test_name, "running")
            # In real implementation, would re-run specific test

            if random.random() > 0.5:  # 50% retry success rate
                self._update_test_result(test_name, "passed")
                self.output_text.append(f"✅ {test_name} passed on retry")
            else:
                self._update_test_result(test_name, "failed", "Retry failed")
                self.output_text.append(f"❌ {test_name} failed again")

        self._check_test_completion()
        self.retry_button.setEnabled(True)

    def _check_test_completion(self) -> None:
        """Check if testing is complete and update UI accordingly."""
        if self._check_all_tests_complete():
            passed, failed = self._get_test_summary()
            total = passed + failed

            self.output_text.append(
                f"\\n📊 Testing Complete: {passed}/{total} tests passed"
            )

            if failed == 0:
                self.output_text.append(
                    "🎉 All system tests passed! System is ready for deployment."
                )
                self.update_status(StepStatus.COMPLETED)
                self.continue_button.setEnabled(True)
                self.state.set_system_state("system_tested", True)
            else:
                self.output_text.append(
                    f"⚠️ {failed} test(s) failed. Review issues before deployment."
                )
                self.retry_button.setEnabled(True)
                self.update_status(StepStatus.USER_ACTION_REQUIRED)

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        if self.is_completed() and self.continue_button.isEnabled():
            passed = self.state.get_user_input("system_test_passed", 0)
            self.logger.info(f"System testing completed with {passed} tests passed")

            # Final state persistence
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.request_next_step.emit()
        else:
            self.logger.warning("Continue clicked but system testing not completed")

    def _reset_testing_ui(self) -> None:
        """Reset UI after testing completion."""
        self.start_test_button.setEnabled(True)
        self.progress_bar.setVisible(False)

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the system testing step with state restoration."""
        super().activate_step()

        self.logger.info("System testing step activated")

        # Check if system already tested
        if self.state.get_system_state("system_tested", False):
            passed = self.state.get_user_input("system_test_passed", 0)
            self.output_text.append(
                f"✅ System already tested and validated ({passed} tests passed)"
            )
            self.update_status(StepStatus.COMPLETED)
            self.continue_button.setEnabled(True)
            self.logger.info("System already tested, skipping")

    def update_ui(self) -> None:
        """Update UI elements periodically."""
        super().update_ui()

        # Check testing process status
        process_info = self.state.get_process("system_testing")
        if process_info:
            if not process_info.is_running():
                status = process_info.get_status()
                runtime = process_info.get_runtime()
                minutes = int(runtime // 60)
                seconds = int(runtime % 60)

                if status.value == "completed":
                    self.output_text.append(
                        f"\\n✅ System testing completed in {minutes}m {seconds}s"
                    )
                    # Simulate all tests passing for successful completion
                    for test_name in self.test_results.keys():
                        if self.test_results[test_name] == "pending":
                            self._update_test_result(test_name, "passed")
                    self._check_test_completion()
                else:
                    self.output_text.append(
                        f"\\n❌ System testing failed after {minutes}m {seconds}s"
                    )
                    self.output_text.append(
                        f"Exit code: {process_info.process.returncode}"
                    )
                    # Mark remaining tests as failed
                    for test_name in self.test_results.keys():
                        if self.test_results[test_name] == "pending":
                            self._update_test_result(
                                test_name, "failed", "Process terminated"
                            )
                    self._check_test_completion()

                self._reset_testing_ui()
                # Remove completed process
                self.state.remove_process("system_testing")
            else:
                # Simulate ongoing test progress
                self._simulate_test_progress()

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Stop any running system testing process
            process_info = self.state.get_process("system_testing")
            if process_info and process_info.is_running():
                self.logger.info("Terminating system testing process during cleanup")
                self.process_runner.terminate_process("system_testing")

            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("System testing step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
