"""Service startup and log monitoring step implementation."""

from __future__ import annotations

import glob
import os
import shutil
from datetime import datetime

from config.messages import MESSAGES
from config.participant_contract import (
    build_participant_full_id,
    get_participant_data_dir,
)
from core import WizardStep
from core.exceptions import ErrorType, FlashTVError, handle_step_error
from models import StepStatus
from models.state_keys import UserInputKey
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMessageBox,
    QTextEdit,
    QWidget,
)
from utils.gaze_log_parser import GazeLogParser
from utils.log_tailer import StderrLogTailer
from utils.ui_factory import ButtonStyle
from widgets import GazeArrowWidget


class ServiceStartupStep(WizardStep):
    """Step 10: Starting and Verifying Long Term FLASH-TV Services."""

    def __init__(self, *args, **kwargs):
        # Initialize attributes BEFORE super().__init__() because parent calls create_content_widget()
        # which needs these to exist
        self.service_running = False
        self.log_monitoring_active = False
        self.last_log_check = None

        super().__init__(*args, **kwargs)

        # Initialize gaze log parser (handles location limits loading and efficient tailing)
        self.gaze_parser = GazeLogParser()

        # Initialize stderr log tailer for efficient error log reading
        self.stderr_tailer = StderrLogTailer(
            is_error_func=self.gaze_parser.is_known_minor_error,
            max_buffer_lines=500,
        )

        # Log monitoring timer - use base class create_timer for automatic cleanup
        self.log_monitor_timer = self.create_timer(5000, self._check_logs, start=False)

    def create_content_widget(self) -> QWidget:
        """Create the service startup and log monitoring UI."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections
        overview_section = self._create_overview_section()
        service_section = self._create_service_section()
        log_section = self._create_log_section()
        continue_section = self._create_continue_section()

        main_layout.addWidget(overview_section)
        main_layout.addWidget(service_section)
        main_layout.addWidget(log_section, 1)
        main_layout.addLayout(continue_section)

        return content

    def _update_service_action_buttons(self, busy: bool = False) -> None:
        self.start_services_button.setEnabled(not self.service_running and not busy)
        self.stop_services_button.setEnabled(self.service_running and not busy)
        self.restart_services_button.setEnabled(self.service_running and not busy)

    def _create_overview_section(self) -> QWidget:
        """Create the overview section."""
        overview_group, overview_layout = self.ui_factory.create_group_box(
            "FLASH-TV Service Management and Log Monitoring"
        )

        overview_text = self.ui_factory.create_label(
            "Start services and monitor logs for errors. Services run continuously for data collection."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_service_section(self) -> QWidget:
        """Create the service control section."""
        service_group, service_layout = self.ui_factory.create_group_box(
            "Service Control"
        )

        # Service status
        self.service_status_label = self.ui_factory.create_status_label(
            "Services not started", status_type="info"
        )
        service_layout.addWidget(self.service_status_label)

        # Service control buttons
        button_layout = self.ui_factory.create_horizontal_layout(spacing=10)

        self.start_services_button = self.ui_factory.create_action_button(
            "🚀 Start FLASH-TV Services",
            callback=self._start_services,
            style=ButtonStyle.PRIMARY,
            height=40,
        )
        button_layout.addWidget(self.start_services_button)

        self.stop_services_button = self.ui_factory.create_action_button(
            "🛑 Stop Services",
            callback=self._stop_services,
            style=ButtonStyle.DANGER,
            height=40,
            enabled=False,
        )
        button_layout.addWidget(self.stop_services_button)

        self.restart_services_button = self.ui_factory.create_action_button(
            "🔄 Restart Services",
            callback=self._restart_services,
            style=ButtonStyle.SECONDARY,
            height=40,
            enabled=False,
        )
        button_layout.addWidget(self.restart_services_button)

        service_layout.addLayout(button_layout)

        # Service info
        service_info = self.ui_factory.create_label(
            "Services to be started:\n"
            "flash-run-on-boot.service (systemd)\n"
            "flash-periodic-restart.service (systemd)\n"
            "Home Assistant Docker container\n\n"
            "These manage FLASH-TV data collection and restarts."
        )
        service_layout.addWidget(service_info)

        return service_group

    def _create_log_section(self) -> QWidget:
        """Create the 4-column log monitoring section."""
        log_group, log_layout = self.ui_factory.create_group_box("Service Monitoring")

        # Create horizontal layout for 4 columns
        columns_layout = self.ui_factory.create_horizontal_layout()

        # Column 1: Potential Error Log
        stderr_column_layout = self.ui_factory.create_vertical_layout()
        stderr_label = self.ui_factory.create_label("Error Log:")
        stderr_label.setStyleSheet("font-weight: bold;")
        stderr_column_layout.addWidget(stderr_label)

        self.stderr_output = QTextEdit()
        self.stderr_output.setReadOnly(True)
        self.stderr_output.setPlaceholderText("Potential error log will appear here...")
        self.stderr_output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        stderr_column_layout.addWidget(self.stderr_output)

        columns_layout.addLayout(stderr_column_layout)

        # Column 2: Main log file gaze output with arrow
        main_column_layout = self.ui_factory.create_vertical_layout(spacing=2)
        main_label = self.ui_factory.create_label("Main:")
        main_label.setStyleSheet("font-weight: bold;")
        main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_column_layout.addWidget(main_label)

        self.gaze_main_arrow = GazeArrowWidget()
        main_column_layout.addWidget(
            self.gaze_main_arrow, alignment=Qt.AlignmentFlag.AlignCenter
        )

        self.gaze_main_output = QTextEdit()
        self.gaze_main_output.setReadOnly(True)
        self.gaze_main_output.setPlaceholderText("Waiting for data...")
        self.gaze_main_output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        main_column_layout.addWidget(self.gaze_main_output)

        columns_layout.addLayout(main_column_layout)

        # Column 3: Rotation log file gaze output with arrow
        rot_column_layout = self.ui_factory.create_vertical_layout(spacing=2)
        rot_label = self.ui_factory.create_label("Rot:")
        rot_label.setStyleSheet("font-weight: bold;")
        rot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rot_column_layout.addWidget(rot_label)

        self.gaze_rot_arrow = GazeArrowWidget()
        rot_column_layout.addWidget(
            self.gaze_rot_arrow, alignment=Qt.AlignmentFlag.AlignCenter
        )

        self.gaze_rot_output = QTextEdit()
        self.gaze_rot_output.setReadOnly(True)
        self.gaze_rot_output.setPlaceholderText("Waiting for data...")
        self.gaze_rot_output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        rot_column_layout.addWidget(self.gaze_rot_output)

        columns_layout.addLayout(rot_column_layout)

        # Column 4: Secondary log file gaze output with arrow
        reg_column_layout = self.ui_factory.create_vertical_layout(spacing=2)
        reg_label = self.ui_factory.create_label("Reg:")
        reg_label.setStyleSheet("font-weight: bold;")
        reg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reg_column_layout.addWidget(reg_label)

        self.gaze_reg_arrow = GazeArrowWidget()
        reg_column_layout.addWidget(
            self.gaze_reg_arrow, alignment=Qt.AlignmentFlag.AlignCenter
        )

        self.gaze_reg_output = QTextEdit()
        self.gaze_reg_output.setReadOnly(True)
        self.gaze_reg_output.setPlaceholderText("Waiting for data...")
        self.gaze_reg_output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        reg_column_layout.addWidget(self.gaze_reg_output)

        columns_layout.addLayout(reg_column_layout)

        log_layout.addLayout(columns_layout)

        # Verification buttons at the bottom
        verification_layout = self.ui_factory.create_horizontal_layout(spacing=8)

        self.services_working_button = self.ui_factory.create_action_button(
            "✅ Services Running Properly",
            callback=self._services_verified,
            style=ButtonStyle.SUCCESS,
            height=30,
            enabled=False,
        )
        verification_layout.addWidget(self.services_working_button)

        self.services_issue_button = self.ui_factory.create_action_button(
            "❌ Service Issues Detected",
            callback=self._services_have_issues,
            style=ButtonStyle.DANGER,
            height=30,
            enabled=False,
        )
        verification_layout.addWidget(self.services_issue_button)

        log_layout.addLayout(verification_layout)

        return log_group

    def _create_continue_section(self):
        """Create the continue button section."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text=MESSAGES.UI.CONTINUE
        )
        return button_layout

    def _cleanup_test_data(
        self, username: str, participant_id: str, device_id: str
    ) -> None:
        """Clean up test data from previous steps while preserving gallery faces.

        Removes:
        - test_res/ folder (gaze test results)
        - test_frames/ folder (gaze test frames)
        - Temporary gaze test images/videos

        Preserves:
        - *_faces/ gallery folder
        - Any existing production log files
        """
        try:
            full_id = build_participant_full_id(participant_id, device_id)
            data_path = str(get_participant_data_dir(username, participant_id, device_id))
            scripts_path = f"/home/{username}/flash-tv-scripts/python_scripts"

            self.logger.info(f"Cleaning up test data for {full_id}")

            from core.event_store import EventType

            # Log to event store
            self.event_store.log_event(
                EventType.DATA_DELETED,
                step_id=self.step_definition.step_id,
                action="cleanup_test_data_started",
                details={"participant_id": full_id, "data_path": data_path},
            )

            cleaned_items = []

            # Clean test_res folder in scripts directory
            test_res_path = os.path.join(scripts_path, "test_res")
            if os.path.exists(test_res_path):
                shutil.rmtree(test_res_path)
                cleaned_items.append("test_res/")
                self.logger.info(f"Removed test_res folder: {test_res_path}")

            # Clean test_frames folder in scripts directory
            test_frames_path = os.path.join(scripts_path, "test_frames")
            if os.path.exists(test_frames_path):
                shutil.rmtree(test_frames_path)
                cleaned_items.append("test_frames/")
                self.logger.info(f"Removed test_frames folder: {test_frames_path}")

            # Clean any test output in data folder (but NOT gallery faces or production logs)
            # Pattern: files with "test" in name but not in _faces folder
            if os.path.exists(data_path):
                # Remove test-specific files
                for pattern in [
                    f"{full_id}_test_*.jpg",
                    f"{full_id}_test_*.png",
                    f"{full_id}_gaze_test_*.log",
                ]:
                    for filepath in glob.glob(os.path.join(data_path, pattern)):
                        try:
                            os.remove(filepath)
                            cleaned_items.append(os.path.basename(filepath))
                            self.logger.debug(f"Removed test file: {filepath}")
                        except OSError as e:
                            self.logger.warning(f"Could not remove {filepath}: {e}")

            if cleaned_items:
                self.logger.info(
                    f"Test data cleanup completed - removed {len(cleaned_items)} items: "
                    f"{', '.join(cleaned_items[:5])}{'...' if len(cleaned_items) > 5 else ''}"
                )

                # Log cleanup success to event store
                self.event_store.log_event(
                    EventType.DATA_DELETED,
                    step_id=self.step_definition.step_id,
                    action="cleanup_test_data_completed",
                    details={
                        "participant_id": full_id,
                        "items_removed": len(cleaned_items),
                        "items": cleaned_items[:10],  # Log first 10 items
                    },
                )
            else:
                self.logger.info("No test data to clean up")

        except Exception as e:
            # Log error but don't fail - cleanup failure shouldn't block services
            self.logger.warning(f"Error during test data cleanup: {e}")
            self.event_store.log_error(
                step_id=self.step_definition.step_id,
                action="cleanup_test_data_failed",
                error_message=str(e),
            )

    @handle_step_error
    def _start_services(self, checked: bool = False) -> None:
        """Start FLASH-TV services using the actual service scripts."""
        try:
            # Get all required values from state
            username = self.state.get_user_input(UserInputKey.USERNAME, "")
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")

            if not username:
                raise FlashTVError(
                    "Missing username",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first",
                )

            if not participant_id:
                raise FlashTVError(
                    "Missing participant ID",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first",
                )

            if not device_id:
                raise FlashTVError(
                    "Missing device ID",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first",
                )

            self.logger.info("Starting FLASH-TV systemd services")

            # Clean up test data from previous steps (gaze test, etc.) but preserve gallery
            self._cleanup_test_data(username, participant_id, device_id)

            # Set sudo password from state for service operations
            if not self.process_runner.set_sudo_password_from_state():
                raise FlashTVError(
                    "Sudo password required for service operations",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Ensure sudo password is entered in participant setup",
                )

            self._update_service_action_buttons(busy=True)
            self.service_status_label.setText("Starting services...")
            self.update_status(StepStatus.AUTOMATION_RUNNING)

            self._configure_service_files(username, participant_id, device_id)

            self.logger.info("Starting FLASH-TV services...")

            # Run each service command individually using sudo support
            all_success = True

            # Enable flash-periodic-restart.service
            self.logger.info("Enabling flash-periodic-restart.service...")
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "enable", "flash-periodic-restart.service"],
                "Enable flash-periodic-restart service",
                timeout_ms=15000,
            )
            if not (result and result.returncode == 0):
                all_success = False

            # Enable flash-run-on-boot.service
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "enable", "flash-run-on-boot.service"],
                "Enable flash-run-on-boot service",
                timeout_ms=15000,
            )
            if not (result and result.returncode == 0):
                all_success = False

            # Start flash-periodic-restart.service
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "start", "flash-periodic-restart.service"],
                "Start flash-periodic-restart service",
                timeout_ms=15000,
            )
            if not (result and result.returncode == 0):
                all_success = False

            # Start flash-run-on-boot.service
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "start", "flash-run-on-boot.service"],
                "Start flash-run-on-boot service",
                timeout_ms=15000,
            )
            if not (result and result.returncode == 0):
                all_success = False

            # Start Home Assistant Docker container
            result = self.process_runner.run_command(
                ["docker", "compose", "up", "-d"],
                working_dir=f"/home/{username}/homeassistant-compose",
                timeout_ms=30000,
            )
            if not (result and result.returncode == 0):
                all_success = False

            # Check service status
            result, error = self.process_runner.run_sudo_command(
                [
                    "systemctl",
                    "status",
                    "--no-pager",
                    "flash-periodic-restart.service",
                    "flash-run-on-boot.service",
                ],
                "Check service status",
                timeout_ms=10000,
            )
            if all_success:
                self.service_running = True
                self.state.set_user_input(UserInputKey.SERVICES_RUNNING, True)
                self._update_service_action_buttons()
                self.service_status_label.setText("FLASH-TV services running")

                # Start log monitoring
                self._start_log_monitoring()

                # Enable verification immediately since services are now started
                self.services_working_button.setEnabled(True)
                self.services_issue_button.setEnabled(True)

                self.logger.info("FLASH-TV services started successfully")
            else:
                error_msg = result.stderr if result else "Script execution failed"
                raise FlashTVError(
                    f"Failed to start FLASH-TV services: {error_msg}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check service script permissions and systemd status",
                )

        except Exception as e:
            self.logger.error(f"Error starting services: {e}")
            self.service_running = False
            self.state.set_user_input(UserInputKey.SERVICES_RUNNING, False)
            self._update_service_action_buttons()
            self.service_status_label.setText(
                "Could not start services. Check the message above and try again."
            )
            self.update_status(StepStatus.FAILED)
            raise

    @handle_step_error
    def _stop_services(self, checked: bool = False) -> None:
        """Stop FLASH-TV services using the actual service scripts."""
        try:
            username = self.state.get_user_input(UserInputKey.USERNAME, "")
            self.logger.info("Stopping FLASH-TV systemd services")
            self._update_service_action_buttons(busy=True)
            self.service_status_label.setText("Stopping services...")

            if not self.process_runner.set_sudo_password_from_state():
                self.service_running = True
                self._update_service_action_buttons()
                self.service_status_label.setText(
                    "Could not stop services. Enter the sudo password and try again."
                )
                raise FlashTVError(
                    "Sudo password required for stopping services",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Enter the sudo password and try stopping the services again",
                )

            self._stop_log_monitoring()
            failed_actions = []

            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "stop", "flash-periodic-restart.service"],
                "Stop flash-periodic-restart service",
                timeout_ms=15000,
            )
            if not (result and result.returncode == 0):
                failed_actions.append(
                    f"stop flash-periodic-restart.service ({error or (result.stderr if result else 'no output')})"
                )

            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "stop", "flash-run-on-boot.service"],
                "Stop flash-run-on-boot service",
                timeout_ms=15000,
            )
            if not (result and result.returncode == 0):
                failed_actions.append(
                    f"stop flash-run-on-boot.service ({error or (result.stderr if result else 'no output')})"
                )

            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "disable", "flash-periodic-restart.service"],
                "Disable flash-periodic-restart service",
                timeout_ms=15000,
            )
            if not (result and result.returncode == 0):
                failed_actions.append(
                    f"disable flash-periodic-restart.service ({error or (result.stderr if result else 'no output')})"
                )

            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "disable", "flash-run-on-boot.service"],
                "Disable flash-run-on-boot service",
                timeout_ms=15000,
            )
            if not (result and result.returncode == 0):
                failed_actions.append(
                    f"disable flash-run-on-boot.service ({error or (result.stderr if result else 'no output')})"
                )

            result = self.process_runner.run_command(
                ["docker", "compose", "down"],
                working_dir=f"/home/{username}/homeassistant-compose",
                timeout_ms=30000,
            )
            if not (result and result.returncode == 0):
                failed_actions.append(
                    f"stop Home Assistant container ({result.stderr if result else 'no output'})"
                )

            if failed_actions:
                self.service_running = True
                self.state.set_user_input(UserInputKey.SERVICES_RUNNING, True)
                self._update_service_action_buttons()
                self._start_log_monitoring()
                self.service_status_label.setText(
                    "Could not stop all services. Review the error and try again."
                )
                raise FlashTVError(
                    "Could not stop all FLASH-TV services cleanly. "
                    f"Details: {'; '.join(failed_actions[:3])}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Review the error details, then try stopping the services again or use manual systemctl and docker commands",
                )

            self.service_running = False
            self.state.set_user_input(UserInputKey.SERVICES_RUNNING, False)
            self._update_service_action_buttons()
            self.service_status_label.setText("Services stopped")

            self.logger.info("FLASH-TV service stop script executed")

        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")
            raise FlashTVError(
                f"Failed to stop services: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try manual systemctl commands",
            )

    @handle_step_error
    def _restart_services(self, checked: bool = False) -> None:
        """Restart FLASH-TV services using the restart script."""
        try:
            username = self.state.get_user_input(UserInputKey.USERNAME, "")
            self.logger.info("Restarting FLASH-TV services")
            self._update_service_action_buttons(busy=True)
            self.service_status_label.setText("Restarting services...")

            if not self.process_runner.set_sudo_password_from_state():
                self.service_running = True
                self._update_service_action_buttons()
                self.service_status_label.setText(
                    "Could not restart services. Enter the sudo password and try again."
                )
                raise FlashTVError(
                    "Sudo password required for restarting services",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Enter the sudo password and try restarting the services again",
                )

            # Run the restart services script with username as argument
            script_path = (
                f"/home/{username}/flash-tv-scripts/services/restart_services.sh"
            )
            result, error = self.process_runner.run_sudo_command(
                ["bash", script_path, username],
                "Restart FLASH-TV services",
                timeout_ms=30000,
            )

            if error:
                raise FlashTVError(
                    f"Failed to restart services: {error}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check service script and try manual restart",
                )

            self.service_running = True
            self.state.set_user_input(UserInputKey.SERVICES_RUNNING, True)
            self._update_service_action_buttons()
            self.service_status_label.setText("FLASH-TV services restarted")

            self._stop_log_monitoring()
            self._start_log_monitoring()

            self.logger.info("FLASH-TV services restarted successfully")

        except Exception as e:
            self.logger.error(f"Error restarting services: {e}")
            self.service_running = True
            self.state.set_user_input(UserInputKey.SERVICES_RUNNING, True)
            self._update_service_action_buttons()
            self.service_status_label.setText(
                "Could not restart services. Check the message above and try again."
            )
            raise

    def _start_log_monitoring(self) -> None:
        """Start monitoring logs for errors."""
        try:
            self.log_monitoring_active = True
            # Removed old log_status_label widget
            self.log_monitor_timer.start(5000)  # Check every 5 seconds
            self.last_log_check = datetime.now()

            self.logger.info("Log monitoring started")

        except Exception as e:
            self.logger.error(f"Error starting log monitoring: {e}")

    def _stop_log_monitoring(self) -> None:
        """Stop monitoring logs."""
        self.log_monitoring_active = False
        # Timer is stopped by base class deactivate_step() or stop_all_timers()
        self.logger.info("Log monitoring stopped")

    def _check_logs(self) -> None:
        """Check logs for new errors (excluding known minor errors)."""
        try:
            if not self.log_monitoring_active:
                return

            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            username = self.state.get_user_input(UserInputKey.USERNAME, "")

            if not participant_id or not username:
                return

            full_participant_id = build_participant_full_id(participant_id, device_id)
            data_path = str(get_participant_data_dir(username, participant_id, device_id))

            if not os.path.exists(data_path):
                return

            # Look for stderr log files specifically
            current_time = datetime.now()

            # Check stderr log file and display full content with red highlighting
            stderr_log_file = os.path.join(
                data_path, f"{full_participant_id}_flash_logstderr.log"
            )
            if os.path.exists(stderr_log_file):
                self._display_stderr_log(stderr_log_file)

            # Check gaze output files and update the 3 gaze columns
            self._update_gaze_columns(data_path, full_participant_id)

            # Update last check time
            self.last_log_check = current_time

        except Exception as e:
            self.logger.error(f"Error checking logs: {e}")

    def _display_stderr_log(self, log_path: str) -> None:
        """Display the stderr log with errors highlighted in red.

        Uses efficient log tailing - only reads new content since last call.
        """
        try:
            # Use efficient tailer to get new lines and identify errors
            new_lines, error_lines = self.stderr_tailer.get_new_content_with_errors(log_path)

            # Only update if there are new lines
            if not new_lines:
                return

            # Append new lines to the output (don't clear - we're incrementally updating)
            default_color = self.stderr_output.palette().color(
                self.stderr_output.foregroundRole()
            )

            for line in new_lines:
                if not line.strip():
                    self.stderr_output.append(line)
                    continue

                # Check if this line is an error (not a known safe message)
                is_error = line in error_lines

                if is_error:
                    # Highlight errors in red
                    self.stderr_output.append(
                        f'<span style="color: red;">{line}</span>'
                    )
                else:
                    # Normal lines in default color
                    self.stderr_output.setTextColor(default_color)
                    self.stderr_output.append(line)

            # Auto-scroll to bottom
            scrollbar = self.stderr_output.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            self.logger.error(f"Error displaying stderr log {log_path}: {e}")

    def _update_gaze_columns(self, data_path: str, full_participant_id: str) -> None:
        """Update the 3 gaze output columns with latest data."""
        try:
            import glob

            # Find the most recent gaze log files
            base_pattern = os.path.join(
                data_path, f"{full_participant_id}_flash_log_*.txt"
            )
            all_gaze_files = glob.glob(base_pattern)

            # Group files by timestamp
            file_groups = {}
            for filepath in all_gaze_files:
                filename = os.path.basename(filepath)
                if "_flash_log_" in filename:
                    parts = filename.split("_flash_log_")
                    if len(parts) == 2:
                        timestamp_part = (
                            parts[1]
                            .replace(".txt", "")
                            .replace("_rot", "")
                            .replace("_reg", "")
                        )
                        base_name = f"{full_participant_id}_flash_log_{timestamp_part}"

                        if base_name not in file_groups:
                            file_groups[base_name] = {}

                        if filepath.endswith("_rot.txt"):
                            file_groups[base_name]["rot"] = filepath
                        elif filepath.endswith("_reg.txt"):
                            file_groups[base_name]["reg"] = filepath
                        elif filepath.endswith(f"{timestamp_part}.txt"):
                            file_groups[base_name]["main"] = filepath

            # Find the most recent complete set
            most_recent_group = None
            most_recent_time = None

            for base_name, files in file_groups.items():
                if "main" in files:
                    mtime = os.path.getmtime(files["main"])
                    if most_recent_time is None or mtime > most_recent_time:
                        most_recent_time = mtime
                        most_recent_group = files

            # Update each column with formatted gaze data
            if most_recent_group:
                # Update main model column
                if "main" in most_recent_group:
                    recent_lines = self.gaze_parser.get_recent_data_lines(
                        most_recent_group["main"]
                    )
                    last_line = recent_lines[-1] if recent_lines else ""
                    formatted, gaze_data = self.gaze_parser.format_gaze_data(last_line)
                    self._update_gaze_column_display(
                        self.gaze_main_output,
                        self.gaze_main_arrow,
                        formatted,
                        recent_lines,
                        gaze_data,
                    )

                # Update rotation model column
                if "rot" in most_recent_group:
                    recent_lines = self.gaze_parser.get_recent_data_lines(
                        most_recent_group["rot"]
                    )
                    last_line = recent_lines[-1] if recent_lines else ""
                    formatted, gaze_data = self.gaze_parser.format_gaze_data(last_line)
                    self._update_gaze_column_display(
                        self.gaze_rot_output,
                        self.gaze_rot_arrow,
                        formatted,
                        recent_lines,
                        gaze_data,
                    )

                # Update secondary model column
                if "reg" in most_recent_group:
                    recent_lines = self.gaze_parser.get_recent_data_lines(
                        most_recent_group["reg"]
                    )
                    last_line = recent_lines[-1] if recent_lines else ""
                    formatted, gaze_data = self.gaze_parser.format_gaze_data(last_line)
                    self._update_gaze_column_display(
                        self.gaze_reg_output,
                        self.gaze_reg_arrow,
                        formatted,
                        recent_lines,
                        gaze_data,
                    )
            else:
                # No files found
                self.gaze_main_output.setPlainText("Waiting for data...")
                self.gaze_rot_output.setPlainText("Waiting for data...")
                self.gaze_reg_output.setPlainText("Waiting for data...")

        except Exception as e:
            self.logger.error(f"Error updating gaze columns: {e}")

    def _update_gaze_column_display(
        self,
        text_widget: QTextEdit,
        arrow_widget: GazeArrowWidget,
        formatted_text: str,
        raw_lines: list[str],
        gaze_data: tuple[float, float, bool] | None,
    ) -> None:
        """Update a gaze column widget with arrow display and recent log lines."""
        # Clear and show recent lines (like stderr log)
        text_widget.clear()

        for line in raw_lines:
            text_widget.append(line)

        # Auto-scroll to bottom
        scrollbar = text_widget.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

        # Extract timestamp and status from formatted text for arrow widget caption
        timestamp = ""
        status = ""
        if formatted_text:
            lines = formatted_text.split("\n")
            if len(lines) >= 1 and lines[0].startswith("["):
                # Extract timestamp like "[18:24:01.063]"
                timestamp = lines[0]
            if len(lines) >= 2:
                # Extract status like "🟢 WATCHING TV" or "🔵 LOOKING AWAY"
                status = lines[1]
                if len(lines) >= 3:
                    status += "\n" + lines[2]  # Add angle info if present

        # Update arrow widget with gaze data and captions
        if gaze_data:
            pitch_deg, yaw_deg, watching_tv = gaze_data
            arrow_widget.set_gaze(pitch_deg, yaw_deg, watching_tv, timestamp, status)
        else:
            arrow_widget.set_gaze(0, 0, False, timestamp, status)

    @handle_step_error
    def _services_verified(self, checked: bool = False) -> None:
        """Handle service verification confirmation."""
        try:
            reply = QMessageBox.question(
                self,
                "Confirm Services",
                "Please confirm that:\n\n"
                "✓ FLASH-TV services are running properly\n"
                "✓ No critical errors in the logs\n"
                "✓ Data collection appears to be working\n"
                "✓ Any detected issues are minor/expected\n\n"
                "Are the services running correctly?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("User confirmed services are running properly")

                # Mark as complete but keep services running
                self.state.set_user_input(UserInputKey.SERVICES_VERIFIED, True)
                self.state.set_user_input(UserInputKey.SERVICES_RUNNING, True)

                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)

                QMessageBox.information(
                    self,
                    "Services Verified",
                    "FLASH-TV services verified and running!\n"
                    "Data collection will continue in the background.\n\n"
                    "Note: Services will continue running after this wizard completes.",
                )

        except Exception as e:
            self.logger.error(f"Error during service verification: {e}")
            raise

    @handle_step_error
    def _services_have_issues(self, checked: bool = False) -> None:
        """Handle service issues."""
        try:
            self.logger.warning("User reported service issues")

            QMessageBox.information(
                self,
                "Service Issues",
                "Service issues detected.\n\n"
                "Common troubleshooting steps:\n"
                "Check camera connection\n"
                "Verify face gallery setup\n"
                "Check file permissions\n"
                "Review error messages above\n"
                "Try restarting services\n\n"
                "Fix issues and restart services before continuing.",
            )

            self.update_status(StepStatus.FAILED)

        except Exception as e:
            self.logger.error(f"Error handling service issues: {e}")
            raise

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click."""
        try:
            if self.state.get_user_input(UserInputKey.SERVICES_VERIFIED, False):
                self.logger.info("Service verification step completed successfully")

                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but services not verified")

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the service management step."""
        super().activate_step()
        self.logger.info("Service management step activated")

        # Clear stderr output and reset tailer for fresh state on activation
        self.stderr_output.clear()
        self.stderr_tailer.reset()
        self.gaze_parser.reset_file_state()

        # Check if services already verified
        if self.state.get_user_input(UserInputKey.SERVICES_VERIFIED, False):
            self.service_running = True
            self.state.set_user_input(UserInputKey.SERVICES_RUNNING, True)
            self._update_service_action_buttons()
            self.service_status_label.setText("✅ Services already verified")
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)
        else:
            self.service_running = bool(
                self.state.get_user_input(UserInputKey.SERVICES_RUNNING, False)
            )
            self._update_service_action_buttons()

            # Start log monitoring if services are already running
            self.logger.info("Services already verified - starting log monitoring")
            self._start_log_monitoring()

    def update_ui(self) -> None:
        """Update UI elements periodically."""
        super().update_ui()
        # Services are managed by systemd, no need to monitor processes

    def deactivate_step(self) -> None:
        """Deactivate step when navigating away."""
        self.logger.info("Deactivating service startup step")
        self._stop_log_monitoring()  # Set monitoring flag to false
        super().deactivate_step()  # Base class handles timer cleanup

    def _configure_service_files(
        self, username: str, participant_id: str, device_id: str
    ) -> None:
        try:
            combined_participant_id = build_participant_full_id(participant_id, device_id)
            data_path = str(get_participant_data_dir(username, participant_id, device_id))
            self.logger.info(
                "Validating rendered service artifacts for participant "
                f"{combined_participant_id} on device {device_id}"
            )

            expected_checks = {
                f"/home/{username}/flash-tv-scripts/services/flash-run-on-boot.service": [
                    f"/home/{username}/flash-tv-scripts/services/flash_run_on_boot.sh",
                    f"{data_path}/{combined_participant_id}_flash_logstdout.log",
                    f"{data_path}/{combined_participant_id}_flash_logstderr.log",
                ],
                f"/home/{username}/flash-tv-scripts/services/flash-periodic-restart.service": [
                    f"/home/{username}/flash-tv-scripts/services/flash_periodic_restart.sh",
                    f"{data_path}/{combined_participant_id}_flash_logstdoutp.log",
                    f"{data_path}/{combined_participant_id}_flash_logstderrp.log",
                ],
                f"/home/{username}/flash-tv-scripts/services/flash_run_on_boot.sh": [
                    f"export participant_id={combined_participant_id}",
                    f"export username={username}",
                ],
                f"/home/{username}/flash-tv-scripts/services/flash_periodic_restart.sh": [
                    f"export participant_id={combined_participant_id}",
                    f"export username={username}",
                ],
            }

            unresolved_markers = ("flashsysXXX", "123XXX", "{{", "}}")
            validation_issues: list[str] = []

            for service_file, expected_values in expected_checks.items():
                if not os.path.exists(service_file):
                    validation_issues.append(f"Missing required artifact: {service_file}")
                    continue

                with open(service_file, "r", encoding="utf-8") as service_handle:
                    content = service_handle.read()

                unresolved = [marker for marker in unresolved_markers if marker in content]
                if unresolved:
                    validation_issues.append(
                        f"{service_file} still contains placeholder text ({', '.join(unresolved)})"
                    )
                    continue

                missing_values = [
                    value for value in expected_values if value not in content
                ]
                if missing_values:
                    validation_issues.append(
                        f"{service_file} is not rendered for participant {combined_participant_id}"
                    )

            if validation_issues:
                details = "; ".join(validation_issues[:3])
                if len(validation_issues) > 3:
                    details += "; ..."
                raise FlashTVError(
                    "FLASH-TV service files are not ready for startup yet. "
                    "Please complete the participant rendering/setup step so the "
                    "service templates are rendered for this participant before starting services. "
                    f"Details: {details}",
                    ErrorType.CONFIGURATION_ERROR,
                    recovery_action="Re-run the participant setup/change flow to render service files for this participant",
                )

            self.logger.info("Rendered service artifacts validated successfully")

            # Copy configured service files to /etc/systemd/system/
            self.logger.info("Copying service files to system directory")
            service_files_to_copy = [
                f"/home/{username}/flash-tv-scripts/services/flash-run-on-boot.service",
                f"/home/{username}/flash-tv-scripts/services/flash-periodic-restart.service",
            ]

            for service_file in service_files_to_copy:
                service_name = os.path.basename(service_file)
                result, error = self.process_runner.run_sudo_command(
                    ["cp", service_file, f"/etc/systemd/system/{service_name}"],
                    f"Copy {service_name} to system directory",
                    timeout_ms=10000,
                )

                if error:
                    self.logger.error(f"Failed to copy {service_name}: {error}")
                    raise FlashTVError(
                        f"Failed to copy {service_name} to system directory: {error}",
                        ErrorType.PROCESS_ERROR,
                        recovery_action="Check sudo permissions",
                    )
                else:
                    self.logger.info(
                        f"Successfully copied {service_name} to /etc/systemd/system/"
                    )

            # Reload systemctl daemon
            self.logger.info("Reloading systemctl daemon")
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "daemon-reload"],
                "Reload systemctl daemon",
                timeout_ms=10000,
            )

            if error:
                self.logger.error(f"Failed to reload systemctl daemon: {error}")
                raise FlashTVError(
                    f"Failed to reload systemctl daemon: {error}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check systemctl permissions",
                )
            else:
                self.logger.info("Successfully reloaded systemctl daemon")

        except Exception as e:
            self.logger.error(f"Error configuring service files: {e}")
            raise FlashTVError(
                f"Failed to configure service files: {e}",
                ErrorType.CONFIGURATION_ERROR,
                recovery_action="Check service file paths and permissions",
            )

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Stop log monitoring
            self._stop_log_monitoring()

            # Note: We intentionally do NOT stop the service here
            # The service should continue running after the wizard completes

            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Service management step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
