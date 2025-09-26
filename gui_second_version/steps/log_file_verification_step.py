"""Service startup and log monitoring step implementation."""

from __future__ import annotations

import os
import re
import time
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Set

from PyQt6.QtWidgets import QWidget, QMessageBox, QListWidget, QListWidgetItem, QTextEdit
from PyQt6.QtCore import QTimer

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from utils.ui_factory import ButtonStyle


class LogFileVerificationStep(WizardStep):
    """Step 10: Service Startup and Log Monitoring."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Service monitoring state
        self.service_running = False
        self.log_monitoring_active = False
        self.last_log_check = None

        # Known warnings/errors to ignore
        self.known_warnings = {
            "Corrupt JPEG data",
            "DeprecationWarning",
            "UserWarning",
            "Deprecated in NumPy 1.20",
            "Failed to load image Python extension",
            "Overload resolution failed:",
            "M is not a numpy array, neither a scalar",
            "Expected Ptr<cv::UMat> for argument",
            "Traceback",
            "warpAffine",
            "nimg = face_align.norm_crop(face_img_bgr, pts5)",
            "facen = model.get_input(face, facelmarks.astype(np.int).reshape(1,5,2), face=True)",
            "face = io.imread(os.path.join(path, fname))",
            "detFacesLog, bboxFaces, idxFaces = pipe_frames_data_to_faces",
            "test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py",
            "insightface/deploy/face_model.py",
            "insightface/utils/face_align.py",
            "RTNETLINK answers: File exists"
        }

        # Normal messages to ignore
        self.normal_messages = {
            "Loading symbol saved by previous version",
            "Symbol successfully upgraded!",
            "Running performance tests",
            "Resource temporarily unavailable",
        }

        # Log monitoring timer
        self.log_monitor_timer = QTimer()
        self.log_monitor_timer.timeout.connect(self._check_logs)

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

    def _create_overview_section(self) -> QWidget:
        """Create the overview section."""
        overview_group, overview_layout = self.ui_factory.create_group_box(
            "FLASH-TV Service Management and Log Monitoring"
        )

        overview_text = self.ui_factory.create_label(
            "This step starts the FLASH-TV data collection services and monitors the logs for any issues. "
            "The services will run continuously and data collection will begin. "
            "Logs are monitored in real-time to detect any unexpected errors."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_service_section(self) -> QWidget:
        """Create the service control section."""
        service_group, service_layout = self.ui_factory.create_group_box("Service Control")

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
            "• FLASH-TV data collection service\n"
            "• Log monitoring and error detection\n"
            "• Periodic restart service (if configured)\n\n"
            "Data collection will begin immediately after service startup."
        )
        service_layout.addWidget(service_info)

        return service_group

    def _create_log_section(self) -> QWidget:
        """Create the log monitoring section."""
        log_group, log_layout = self.ui_factory.create_group_box("Log Monitoring")

        # Log monitoring status
        self.log_status_label = self.ui_factory.create_status_label(
            "Log monitoring not active", status_type="info"
        )
        log_layout.addWidget(self.log_status_label)

        # Log output area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(200)
        self.log_output.setPlaceholderText("Service logs and error messages will appear here...")
        log_layout.addWidget(self.log_output)

        # Error summary list
        error_list_label = self.ui_factory.create_label("Detected Issues:")
        log_layout.addWidget(error_list_label)

        self.error_list = QListWidget()
        self.error_list.setMaximumHeight(100)
        log_layout.addWidget(self.error_list)

        # Verification buttons
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
            callback=self._on_continue_clicked, text="Services Verified - Continue"
        )
        return button_layout

    @handle_step_error
    def _start_services(self, checked: bool = False) -> None:
        """Start FLASH-TV services."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not participant_id or not username:
                raise FlashTVError(
                    "Missing participant ID or username",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first"
                )

            full_participant_id = f"{participant_id}{device_id}" if device_id else participant_id

            self.logger.info(f"Starting FLASH-TV services for participant: {full_participant_id}")

            self.start_services_button.setEnabled(False)
            self.service_status_label.setText("🚀 Starting services...")
            self.update_status(StepStatus.AUTOMATION_RUNNING)

            # Start the main data collection service using the same script as data collection
            script_path = f"/home/{username}/flash-tv-scripts/python_scripts/run_flash_data_collection.py"

            command = [
                f"/home/{username}/py38/bin/python",
                script_path,
                full_participant_id,
                f"/home/{username}/data/{full_participant_id}_data",
                "save-image",
                username,
            ]

            # Launch the service process
            process_info = self.process_runner.run_script(
                command=command,
                description=f"FLASH-TV service for {full_participant_id}",
                working_dir=f"/home/{username}/flash-tv-scripts/python_scripts",
                process_name="flash_service",
            )

            if process_info:
                self.service_running = True
                self.service_status_label.setText("✅ FLASH-TV services running")
                self.stop_services_button.setEnabled(True)
                self.restart_services_button.setEnabled(True)

                # Start log monitoring
                self._start_log_monitoring()

                self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Services started successfully")
                self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Data collection active for {full_participant_id}")

                # Enable verification after a brief startup period
                QTimer.singleShot(5000, lambda: self.services_working_button.setEnabled(True))
                QTimer.singleShot(5000, lambda: self.services_issue_button.setEnabled(True))

                self.logger.info("FLASH-TV services started successfully")
            else:
                raise FlashTVError(
                    "Failed to start FLASH-TV services",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check permissions and script path"
                )

        except Exception as e:
            self.logger.error(f"Error starting services: {e}")
            self.start_services_button.setEnabled(True)
            self.service_status_label.setText("❌ Failed to start services")
            self.update_status(StepStatus.FAILED)
            raise

    @handle_step_error
    def _stop_services(self, checked: bool = False) -> None:
        """Stop FLASH-TV services."""
        try:
            self.logger.info("Stopping FLASH-TV services")

            # Stop log monitoring
            self._stop_log_monitoring()

            # Stop the service process
            process_info = self.state.get_process("flash_service")
            if process_info and process_info.is_running():
                self.process_runner.terminate_process("flash_service")

            self.service_running = False
            self.service_status_label.setText("🛑 Services stopped")
            self.start_services_button.setEnabled(True)
            self.stop_services_button.setEnabled(False)
            self.restart_services_button.setEnabled(False)

            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Services stopped")
            self.logger.info("FLASH-TV services stopped")

        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")
            raise FlashTVError(
                f"Failed to stop services: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try using system service commands"
            )

    @handle_step_error
    def _restart_services(self, checked: bool = False) -> None:
        """Restart FLASH-TV services."""
        try:
            self.logger.info("Restarting FLASH-TV services")
            self._stop_services()
            QTimer.singleShot(2000, self._start_services)  # Wait 2 seconds before restart

        except Exception as e:
            self.logger.error(f"Error restarting services: {e}")
            raise

    def _start_log_monitoring(self) -> None:
        """Start monitoring logs for errors."""
        try:
            self.log_monitoring_active = True
            self.log_status_label.setText("🔍 Monitoring logs for errors...")
            self.log_monitor_timer.start(5000)  # Check every 5 seconds
            self.last_log_check = datetime.now()

            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Log monitoring started")
            self.logger.info("Log monitoring started")

        except Exception as e:
            self.logger.error(f"Error starting log monitoring: {e}")

    def _stop_log_monitoring(self) -> None:
        """Stop monitoring logs."""
        try:
            self.log_monitoring_active = False
            self.log_monitor_timer.stop()
            self.log_status_label.setText("🛑 Log monitoring stopped")

            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Log monitoring stopped")
            self.logger.info("Log monitoring stopped")

        except Exception as e:
            self.logger.error(f"Error stopping log monitoring: {e}")

    def _check_logs(self) -> None:
        """Check logs for new errors (excluding known minor errors)."""
        try:
            if not self.log_monitoring_active:
                return

            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not participant_id or not username:
                return

            full_participant_id = f"{participant_id}{device_id}" if device_id else participant_id
            data_path = f"/home/{username}/data/{full_participant_id}_data"

            if not os.path.exists(data_path):
                return

            # Look for log files
            current_time = datetime.now()
            new_errors = []

            for file in os.listdir(data_path):
                if file.startswith(f"{full_participant_id}_flash_log") and file.endswith(".txt"):
                    log_path = os.path.join(data_path, file)

                    # Check if file was modified since last check
                    if self.last_log_check and os.path.getmtime(log_path) > self.last_log_check.timestamp():
                        new_errors.extend(self._scan_log_file(log_path))

            # Update last check time
            self.last_log_check = current_time

            # Display new errors (filtering out known minor ones)
            for error in new_errors:
                if not self._is_known_minor_error(error):
                    self.error_list.addItem(QListWidgetItem(f"[{current_time.strftime('%H:%M:%S')}] {error}"))
                    self.log_output.append(f"[{current_time.strftime('%H:%M:%S')}] ERROR: {error}")

            # Update status
            error_count = self.error_list.count()
            if error_count == 0:
                self.log_status_label.setText("✅ No issues detected")
            else:
                self.log_status_label.setText(f"⚠️ {error_count} issue(s) detected")

        except Exception as e:
            self.logger.error(f"Error checking logs: {e}")

    def _scan_log_file(self, log_path: str) -> List[str]:
        """Scan a log file for error patterns."""
        errors = []
        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                # Look for common error patterns
                if any(pattern in line.lower() for pattern in ['error', 'exception', 'failed', 'critical']):
                    errors.append(line)

        except Exception as e:
            self.logger.error(f"Error scanning log file {log_path}: {e}")

        return errors

    def _is_known_minor_error(self, error_message: str) -> bool:
        """Check if an error is a known warning or normal message that should be ignored."""
        # Check if it's a known warning
        for pattern in self.known_warnings:
            if pattern in error_message or pattern.lower() in error_message.lower():
                return True

        # Check if it's a normal message
        for pattern in self.normal_messages:
            if pattern in error_message or pattern.lower() in error_message.lower():
                return True

        return False

    @handle_step_error
    def _services_verified(self) -> None:
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
                self.state.set_user_input("services_verified", True)
                self.state.set_user_input("services_running", True)

                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)

                QMessageBox.information(
                    self,
                    "Services Verified",
                    "FLASH-TV services verified and running!\n"
                    "Data collection will continue in the background.\n\n"
                    "Note: Services will continue running after this wizard completes."
                )

        except Exception as e:
            self.logger.error(f"Error during service verification: {e}")
            raise

    @handle_step_error
    def _services_have_issues(self) -> None:
        """Handle service issues."""
        try:
            self.logger.warning("User reported service issues")

            QMessageBox.information(
                self,
                "Service Issues",
                "Service issues detected.\n\n"
                "Common troubleshooting steps:\n"
                "• Check camera connection\n"
                "• Verify face gallery setup\n"
                "• Check file permissions\n"
                "• Review error messages above\n"
                "• Try restarting services\n\n"
                "Fix issues and restart services before continuing."
            )

            self.update_status(StepStatus.FAILED)

        except Exception as e:
            self.logger.error(f"Error handling service issues: {e}")
            raise

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click."""
        try:
            if self.state.get_user_input("services_verified", False):
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

        # Check if services already verified
        if self.state.get_user_input("services_verified", False):
            self.service_status_label.setText("✅ Services already verified")
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)

    def update_ui(self) -> None:
        """Update UI elements periodically."""
        super().update_ui()

        # Check service process status
        process_info = self.state.get_process("flash_service")
        if process_info and not process_info.is_running() and self.service_running:
            self.service_running = False
            self.service_status_label.setText("❌ Service stopped unexpectedly")
            self.start_services_button.setEnabled(True)
            self.stop_services_button.setEnabled(False)
            self.restart_services_button.setEnabled(False)

            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Service stopped unexpectedly")
            self.error_list.addItem(QListWidgetItem("Service stopped unexpectedly"))

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