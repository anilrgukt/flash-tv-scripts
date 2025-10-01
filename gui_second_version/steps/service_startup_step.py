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


class ServiceStartupStep(WizardStep):
    """Step 10: Starting and Verifying Long Term FLASH-TV Services."""

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
            "• flash-run-on-boot.service (systemd)\n"
            "• flash-periodic-restart.service (systemd)\n"
            "• Home Assistant Docker container\n\n"
            "These manage FLASH-TV data collection and restarts."
        )
        service_layout.addWidget(service_info)

        return service_group

    def _create_log_section(self) -> QWidget:
        """Create the 4-column log monitoring section."""
        log_group, log_layout = self.ui_factory.create_group_box("Service Monitoring")

        # Create horizontal layout for 4 columns
        columns_layout = self.ui_factory.create_horizontal_layout()

        # Column 1: Full stderr log (scrollable, copy-pastable, errors highlighted in red)
        stderr_column_layout = self.ui_factory.create_vertical_layout()
        stderr_label = self.ui_factory.create_label("stderr Log:")
        stderr_label.setStyleSheet("font-weight: bold;")
        stderr_column_layout.addWidget(stderr_label)

        self.stderr_output = QTextEdit()
        self.stderr_output.setReadOnly(True)
        self.stderr_output.setPlaceholderText("stderr log will appear here...")
        self.stderr_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        stderr_column_layout.addWidget(self.stderr_output)

        columns_layout.addLayout(stderr_column_layout)

        # Column 2: Main model gaze output
        main_column_layout = self.ui_factory.create_vertical_layout()
        main_label = self.ui_factory.create_label("Main Model:")
        main_label.setStyleSheet("font-weight: bold;")
        main_column_layout.addWidget(main_label)

        self.gaze_main_output = QTextEdit()
        self.gaze_main_output.setReadOnly(True)
        self.gaze_main_output.setPlaceholderText("Waiting for data...")
        main_column_layout.addWidget(self.gaze_main_output)

        columns_layout.addLayout(main_column_layout)

        # Column 3: Rotation model gaze output
        rot_column_layout = self.ui_factory.create_vertical_layout()
        rot_label = self.ui_factory.create_label("Rotation Model:")
        rot_label.setStyleSheet("font-weight: bold;")
        rot_column_layout.addWidget(rot_label)

        self.gaze_rot_output = QTextEdit()
        self.gaze_rot_output.setReadOnly(True)
        self.gaze_rot_output.setPlaceholderText("Waiting for data...")
        rot_column_layout.addWidget(self.gaze_rot_output)

        columns_layout.addLayout(rot_column_layout)

        # Column 4: Secondary model gaze output
        reg_column_layout = self.ui_factory.create_vertical_layout()
        reg_label = self.ui_factory.create_label("Secondary Model:")
        reg_label.setStyleSheet("font-weight: bold;")
        reg_column_layout.addWidget(reg_label)

        self.gaze_reg_output = QTextEdit()
        self.gaze_reg_output.setReadOnly(True)
        self.gaze_reg_output.setPlaceholderText("Waiting for data...")
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
            callback=self._on_continue_clicked, text="Services Verified - Continue"
        )
        return button_layout

    @handle_step_error
    def _start_services(self, checked: bool = False) -> None:
        """Start FLASH-TV services using the actual service scripts."""
        try:
            # Get all required values from state
            username = self.state.get_user_input("username", "")
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")

            if not username:
                raise FlashTVError(
                    "Missing username",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first"
                )

            if not participant_id:
                raise FlashTVError(
                    "Missing participant ID",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first"
                )

            if not device_id:
                raise FlashTVError(
                    "Missing device ID",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first"
                )

            self.logger.info("Starting FLASH-TV systemd services")

            # Set sudo password from state for service operations
            if not self.process_runner.set_sudo_password_from_state():
                raise FlashTVError(
                    "Sudo password required for service operations",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Ensure sudo password is entered in participant setup"
                )

            self.start_services_button.setEnabled(False)
            self.service_status_label.setText("Starting services...")
            self.update_status(StepStatus.AUTOMATION_RUNNING)

            # Use the actual start_services.sh script
            script_path = f"/home/{username}/flash-tv-scripts/services/start_services.sh"

            # First configure the service files with participant details
            self._configure_service_files(username, participant_id, device_id)

            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting FLASH-TV services...")

            # Run each service command individually using sudo support
            all_success = True

            # Enable flash-periodic-restart.service
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Enabling flash-periodic-restart.service...")
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "enable", "flash-periodic-restart.service"],
                "Enable flash-periodic-restart service",
                timeout_ms=15000
            )
            if not (result and result.returncode == 0):
                all_success = False
                self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to enable flash-periodic-restart.service: {error}")

            # Enable flash-run-on-boot.service
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Enabling flash-run-on-boot.service...")
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "enable", "flash-run-on-boot.service"],
                "Enable flash-run-on-boot service",
                timeout_ms=15000
            )
            if not (result and result.returncode == 0):
                all_success = False
                self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to enable flash-run-on-boot.service: {error}")

            # Start flash-periodic-restart.service
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting flash-periodic-restart.service...")
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "start", "flash-periodic-restart.service"],
                "Start flash-periodic-restart service",
                timeout_ms=15000
            )
            if not (result and result.returncode == 0):
                all_success = False
                self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to start flash-periodic-restart.service: {error}")

            # Start flash-run-on-boot.service
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting flash-run-on-boot.service...")
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "start", "flash-run-on-boot.service"],
                "Start flash-run-on-boot service",
                timeout_ms=15000
            )
            if not (result and result.returncode == 0):
                all_success = False
                self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to start flash-run-on-boot.service: {error}")

            # Start Home Assistant Docker container
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Home Assistant Docker container...")
            result = self.process_runner.run_command(
                ["docker", "compose", "up", "-d"],
                working_dir=f"/home/{username}/homeassistant-compose",
                timeout_ms=30000
            )
            if not (result and result.returncode == 0):
                all_success = False
                self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to start Home Assistant container")

            # Check service status
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Checking service status...")
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "status", "--no-pager", "flash-periodic-restart.service", "flash-run-on-boot.service"],
                "Check service status",
                timeout_ms=10000
            )
            if result and result.stdout:
                self.log_output.append(f"Service Status:\n{result.stdout}")

            if all_success:
                self.service_running = True
                self.service_status_label.setText("FLASH-TV services running")
                self.stop_services_button.setEnabled(True)
                self.restart_services_button.setEnabled(True)

                # Start log monitoring
                self._start_log_monitoring()

                self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Services started successfully")
                self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Systemd services and Docker containers are now running")

                # Show script output if available
                if result.stdout:
                    self.log_output.append(f"Script output: {result.stdout}")

                # Enable verification immediately since services are now started
                self.services_working_button.setEnabled(True)
                self.services_issue_button.setEnabled(True)

                self.logger.info("FLASH-TV services started successfully")
            else:
                error_msg = result.stderr if result else "Script execution failed"
                self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Service start failed: {error_msg}")
                raise FlashTVError(
                    f"Failed to start FLASH-TV services: {error_msg}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check service script permissions and systemd status"
                )

        except Exception as e:
            self.logger.error(f"Error starting services: {e}")
            self.start_services_button.setEnabled(True)
            self.service_status_label.setText("Failed to start services")
            self.update_status(StepStatus.FAILED)
            raise

    @handle_step_error
    def _stop_services(self, checked: bool = False) -> None:
        """Stop FLASH-TV services using the actual service scripts."""
        try:
            username = self.state.get_user_input("username", "")
            self.logger.info("Stopping FLASH-TV systemd services")

            # Set sudo password from state for service operations
            if not self.process_runner.set_sudo_password_from_state():
                self.logger.error("Sudo password required for stopping services")
                return

            # Stop log monitoring
            self._stop_log_monitoring()

            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Stopping FLASH-TV services...")

            # Stop flash-periodic-restart.service
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "stop", "flash-periodic-restart.service"],
                "Stop flash-periodic-restart service",
                timeout_ms=15000
            )

            # Stop flash-run-on-boot.service
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "stop", "flash-run-on-boot.service"],
                "Stop flash-run-on-boot service",
                timeout_ms=15000
            )

            # Disable flash-periodic-restart.service
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "disable", "flash-periodic-restart.service"],
                "Disable flash-periodic-restart service",
                timeout_ms=15000
            )

            # Disable flash-run-on-boot.service
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "disable", "flash-run-on-boot.service"],
                "Disable flash-run-on-boot service",
                timeout_ms=15000
            )

            # Stop Home Assistant Docker container
            result = self.process_runner.run_command(
                ["docker", "compose", "down"],
                working_dir=f"/home/{username}/homeassistant-compose",
                timeout_ms=30000
            )

            self.service_running = False
            self.service_status_label.setText("Services stopped")
            self.start_services_button.setEnabled(True)
            self.stop_services_button.setEnabled(False)
            self.restart_services_button.setEnabled(False)

            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Stop services script executed")
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Stopping systemd services and Docker containers")
            self.logger.info("FLASH-TV service stop script executed")

        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")
            raise FlashTVError(
                f"Failed to stop services: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try manual systemctl commands"
            )

    @handle_step_error
    def _restart_services(self, checked: bool = False) -> None:
        """Restart FLASH-TV services using the actual service scripts."""
        try:
            username = self.state.get_user_input("username", "")
            self.logger.info("Restarting FLASH-TV systemd services")

            # Set sudo password from state for service operations
            if not self.process_runner.set_sudo_password_from_state():
                self.logger.error("Sudo password required for restarting services")
                return

            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Restarting FLASH-TV services...")

            # Restart flash-periodic-restart.service
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "restart", "flash-periodic-restart.service"],
                "Restart flash-periodic-restart service",
                timeout_ms=15000
            )

            # Restart flash-run-on-boot.service
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "restart", "flash-run-on-boot.service"],
                "Restart flash-run-on-boot service",
                timeout_ms=15000
            )

            # Restart Home Assistant Docker container
            result = self.process_runner.run_command(
                ["docker", "compose", "restart"],
                working_dir=f"/home/{username}/homeassistant-compose",
                timeout_ms=30000
            )

            # Check service status
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "status", "--no-pager", "flash-periodic-restart.service", "flash-run-on-boot.service"],
                "Check service status",
                timeout_ms=10000
            )
            if result and result.stdout:
                self.log_output.append(f"Service Status:\n{result.stdout}")

            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Restart services script executed")
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Restarting systemd services and Docker containers")
            self.logger.info("FLASH-TV service restart script executed")

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

            # Look for stderr log files specifically
            current_time = datetime.now()

            # Check stderr log file and display full content with red highlighting
            stderr_log_file = os.path.join(data_path, f"{full_participant_id}_flash_logstderr.log")
            if os.path.exists(stderr_log_file):
                self._display_stderr_log(stderr_log_file)

            # Check gaze output files and update the 3 gaze columns
            self._update_gaze_columns(data_path, full_participant_id)

            # Update last check time
            self.last_log_check = current_time

        except Exception as e:
            self.logger.error(f"Error checking logs: {e}")

    def _display_stderr_log(self, log_path: str) -> None:
        """Display the full stderr log with errors highlighted in red."""
        try:
            with open(log_path, 'r', errors='ignore') as f:
                content = f.read()

            # Clear current content
            self.stderr_output.clear()

            # Process each line and highlight errors
            for line in content.splitlines():
                # Check if line contains error patterns
                is_error = any(pattern in line for pattern in [
                    'Traceback (most recent call last)',
                    'Exception:',
                    'Error:',
                    'CRITICAL:',
                    'ERROR:',
                    'Failed to',
                    'Could not',
                    'Unable to',
                    'No such file',
                    'Permission denied',
                    'Connection refused',
                    'Segmentation fault',
                    'RuntimeError',
                    'ValueError',
                    'KeyError',
                    'IndexError',
                    'AttributeError',
                    'OSError',
                    'IOError'
                ])

                # Skip known minor errors
                if is_error and not self._is_known_minor_error(line):
                    # Highlight error lines in red
                    self.stderr_output.setTextColor(self.stderr_output.palette().color(self.stderr_output.foregroundRole()))
                    self.stderr_output.append(f'<span style="color: red;">{line}</span>')
                else:
                    # Normal lines in default color
                    self.stderr_output.setTextColor(self.stderr_output.palette().color(self.stderr_output.foregroundRole()))
                    self.stderr_output.append(line)

            # Auto-scroll to bottom
            self.stderr_output.verticalScrollBar().setValue(
                self.stderr_output.verticalScrollBar().maximum()
            )

        except Exception as e:
            self.logger.error(f"Error displaying stderr log {log_path}: {e}")

    def _update_gaze_columns(self, data_path: str, full_participant_id: str) -> None:
        """Update the 3 gaze output columns with latest data."""
        try:
            import glob

            # Find the most recent gaze log files
            base_pattern = os.path.join(data_path, f"{full_participant_id}_flash_log_*.txt")
            all_gaze_files = glob.glob(base_pattern)

            # Group files by timestamp
            file_groups = {}
            for filepath in all_gaze_files:
                filename = os.path.basename(filepath)
                if "_flash_log_" in filename:
                    parts = filename.split("_flash_log_")
                    if len(parts) == 2:
                        timestamp_part = parts[1].replace(".txt", "").replace("_rot", "").replace("_reg", "")
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
                    last_line = self._get_last_data_line(most_recent_group["main"])
                    formatted = self._format_gaze_data(last_line, "main")
                    self._update_gaze_column_display(self.gaze_main_output, formatted, last_line)

                # Update rotation model column
                if "rot" in most_recent_group:
                    last_line = self._get_last_data_line(most_recent_group["rot"])
                    formatted = self._format_gaze_data(last_line, "rot")
                    self._update_gaze_column_display(self.gaze_rot_output, formatted, last_line)

                # Update secondary model column
                if "reg" in most_recent_group:
                    last_line = self._get_last_data_line(most_recent_group["reg"])
                    formatted = self._format_gaze_data(last_line, "reg")
                    self._update_gaze_column_display(self.gaze_reg_output, formatted, last_line)
            else:
                # No files found
                self.gaze_main_output.setPlainText("Waiting for data...")
                self.gaze_rot_output.setPlainText("Waiting for data...")
                self.gaze_reg_output.setPlainText("Waiting for data...")

        except Exception as e:
            self.logger.error(f"Error updating gaze columns: {e}")

    def _update_gaze_column_display(self, widget: QTextEdit, formatted_text: str, raw_line: str) -> None:
        """Update a gaze column widget with color coding."""
        widget.setPlainText(formatted_text)

        # Color code based on status
        if "TC gaze detected" in formatted_text or "Gaze-det" in raw_line:
            widget.setStyleSheet("background-color: #90EE90; padding: 5px;")  # Green
        elif "TC present but no gaze" in formatted_text or "Gaze-no-det" in raw_line:
            widget.setStyleSheet("background-color: #FFFFE0; padding: 5px;")  # Yellow
        elif "No faces detected" in formatted_text or "No-face-detected" in raw_line:
            widget.setStyleSheet("background-color: #FFB6C1; padding: 5px;")  # Light red
        else:
            widget.setStyleSheet("background-color: #f0f0f0; padding: 5px;")  # Gray

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

    def _scan_log_file_complete(self, log_path: str) -> List[str]:
        """Scan entire stderr log file for error patterns."""
        errors = []

        try:
            with open(log_path, 'r', errors='ignore') as f:
                content = f.read()

            # Parse the entire file looking for error patterns
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue

                # Look for actual FLASH-TV errors and Python exceptions
                # Be more selective since stderr will have lots of warnings
                if any(pattern in line for pattern in [
                    'Traceback (most recent call last)',  # Python traceback start
                    'Exception:',  # Python exceptions
                    'Error:',  # General errors
                    'CRITICAL:',  # Critical log messages
                    'ERROR:',  # Error log messages
                    'Failed to detect',  # FLASH-TV specific failures
                    'Failed to load',
                    'Failed to initialize',
                    'Could not find',
                    'Could not open',
                    'Unable to access',
                    'No such file or directory',
                    'Permission denied',
                    'Connection refused',
                    'Camera not found',
                    'Device not found',
                    'Segmentation fault',
                    'Assertion failed',
                    'CUDA out of memory',
                    'RuntimeError',
                    'ValueError',
                    'KeyError',
                    'IndexError',
                    'AttributeError',
                    'OSError',
                    'IOError',
                    'ImportError',
                    'ModuleNotFoundError'
                ]):
                    # Store the error line
                    errors.append(line)

        except Exception as e:
            self.logger.error(f"Error scanning stderr log file {log_path}: {e}")

        return errors

    def _check_gaze_output_files(self, data_path: str, full_participant_id: str) -> None:
        """Check gaze output files and display the last line of each."""
        try:
            import glob
            from datetime import datetime, timedelta

            # Find the most recent gaze log files (within last 24 hours)
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=24)

            # Pattern for gaze log files: {participant_id}_flash_log_YYYY-MM-DD_HH-MM-SS*.txt
            base_pattern = os.path.join(data_path, f"{full_participant_id}_flash_log_*.txt")
            all_gaze_files = glob.glob(base_pattern)

            # Group files by timestamp
            file_groups = {}
            for filepath in all_gaze_files:
                # Extract timestamp from filename
                filename = os.path.basename(filepath)
                # Pattern: P1-3999028_flash_log_2025-09-29_14-32-43.txt or _rot.txt or _reg.txt
                if "_flash_log_" in filename:
                    # Extract the base filename without suffix
                    parts = filename.split("_flash_log_")
                    if len(parts) == 2:
                        timestamp_part = parts[1].replace(".txt", "").replace("_rot", "").replace("_reg", "")
                        base_name = f"{full_participant_id}_flash_log_{timestamp_part}"

                        if base_name not in file_groups:
                            file_groups[base_name] = {}

                        # Determine file type
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
                # Check if we have all three files
                if "main" in files and "rot" in files and "reg" in files:
                    # Get modification time of main file
                    mtime = os.path.getmtime(files["main"])
                    if most_recent_time is None or mtime > most_recent_time:
                        most_recent_time = mtime
                        most_recent_group = files

            # If we found a recent set, display the last lines
            if most_recent_group:
                for file_type, filepath in most_recent_group.items():
                    last_line = self._get_last_data_line(filepath)
                    if last_line:
                        # Parse and format the gaze data
                        formatted_data = self._format_gaze_data(last_line, file_type)

                        # Update the appropriate label
                        if file_type in self.gaze_status_labels:
                            label_prefix = {"main": "Main Model:", "rot": "Rotation Model:", "reg": "Secondary Model:"}[file_type]
                            self.gaze_status_labels[file_type].setText(f"{label_prefix} {formatted_data}")

                            # Color code based on gaze status
                            if "TC gaze detected" in formatted_data or "Gaze-det" in formatted_data:
                                # Target child detected with gaze - green
                                self.gaze_status_labels[file_type].setStyleSheet(
                                    "font-family: monospace; padding: 5px; background-color: #90EE90; margin: 2px;"
                                )
                            elif "TC present but no gaze" in formatted_data or "Gaze-no-det" in formatted_data:
                                # Target child present but no gaze detected - yellow
                                self.gaze_status_labels[file_type].setStyleSheet(
                                    "font-family: monospace; padding: 5px; background-color: #FFFFE0; margin: 2px;"
                                )
                            elif "No faces detected" in formatted_data or "No-face-detected" in formatted_data:
                                # No faces detected - light red/pink
                                self.gaze_status_labels[file_type].setStyleSheet(
                                    "font-family: monospace; padding: 5px; background-color: #FFB6C1; margin: 2px;"
                                )
                            else:
                                # Unknown status - default gray
                                self.gaze_status_labels[file_type].setStyleSheet(
                                    "font-family: monospace; padding: 5px; background-color: #f0f0f0; margin: 2px;"
                                )
            else:
                # No recent files found
                for file_type in ["main", "rot", "reg"]:
                    if file_type in self.gaze_status_labels:
                        label_prefix = {"main": "Main Model:", "rot": "Rotation Model:", "reg": "Secondary Model:"}[file_type]
                        self.gaze_status_labels[file_type].setText(f"{label_prefix} Waiting for data...")
                        self.gaze_status_labels[file_type].setStyleSheet(
                            "font-family: monospace; padding: 5px; background-color: #f0f0f0; margin: 2px;"
                        )

        except Exception as e:
            self.logger.error(f"Error checking gaze output files: {e}")

    def _get_last_data_line(self, filepath: str) -> str:
        """Get the last non-empty line from a gaze log file."""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
                # Find the last non-empty line
                for line in reversed(lines):
                    line = line.strip()
                    if line and not line.startswith("#"):  # Skip comments
                        return line
        except Exception as e:
            self.logger.debug(f"Could not read last line from {filepath}: {e}")
        return ""

    def _format_gaze_data(self, line: str, file_type: str) -> str:
        """Format gaze data line for display."""
        try:
            # Format: timestamp frame_num num_faces tc_present pitch yaw roll tc_angle x1 y1 x2 y2 label
            # All space-separated
            parts = line.split()

            if len(parts) >= 13:
                # Extract key fields
                timestamp = parts[0].split('_')[-1] if '_' in parts[0] else parts[0]  # Get time part only
                frame_num = parts[1]
                num_faces = parts[2]
                tc_present = parts[3]  # 0 or 1

                # Gaze data (pitch, yaw, roll) - parts[4:7]
                pitch = parts[4] if parts[4] != "None" else "N/A"
                yaw = parts[5] if parts[5] != "None" else "N/A"

                # Label - last element
                label = parts[-1] if len(parts) > 12 else "unknown"

                # Format based on detection status
                if label == "Gaze-det":
                    # Target child detected with gaze
                    if pitch != "N/A" and yaw != "N/A":
                        return f"[{timestamp}] TC gaze detected - Pitch: {pitch[:6]}, Yaw: {yaw[:6]}"
                    else:
                        return f"[{timestamp}] TC detected with gaze"
                elif label == "Gaze-no-det":
                    # Target child present but no gaze detection
                    return f"[{timestamp}] TC present but no gaze (faces: {num_faces})"
                elif label == "No-face-detected":
                    # No faces detected at all
                    return f"[{timestamp}] No faces detected"
                else:
                    # Unknown label
                    return f"[{timestamp}] Status: {label} (faces: {num_faces}, TC: {tc_present})"
            else:
                return f"Invalid format (only {len(parts)} fields)"
        except Exception as e:
            self.logger.debug(f"Error formatting gaze data: {e}")
            return "Parse error"

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
        # Services are managed by systemd, no need to monitor processes

    def _configure_service_files(self, username: str, participant_id: str, device_id: str) -> None:
        """Configure service files by replacing placeholder values with participant details."""
        try:
            self.logger.info(f"Configuring service files for participant {participant_id} on device {device_id}")

            # Define the service files that need configuration
            service_files = [
                f"/home/{username}/flash-tv-scripts/services/flash-run-on-boot.service",
                f"/home/{username}/flash-tv-scripts/services/flash-periodic-restart.service",
                f"/home/{username}/flash-tv-scripts/services/flash_run_on_boot.sh",
                f"/home/{username}/flash-tv-scripts/services/flash_periodic_restart.sh"
            ]

            # Define the replacements - IMPORTANT: Use combined participant_id + device_id
            combined_participant_id = f"{participant_id}{device_id}"
            replacements = {
                "flashsysXXX": username,
                "123XXX": combined_participant_id
            }

            self.logger.info(f"Using combined participant ID: {combined_participant_id}")

            for service_file in service_files:
                if os.path.exists(service_file):
                    self.logger.info(f"Configuring {service_file}")

                    # Read the current content
                    with open(service_file, 'r') as f:
                        content = f.read()

                    # Apply replacements
                    for placeholder, value in replacements.items():
                        content = content.replace(placeholder, value)

                    # Write back the configured content
                    with open(service_file, 'w') as f:
                        f.write(content)

                    self.logger.info(f"Successfully configured {service_file}")
                else:
                    self.logger.warning(f"Service file not found: {service_file}")

            self.logger.info("Service file configuration completed")

            # Copy configured service files to /etc/systemd/system/
            self.logger.info("Copying service files to system directory")
            service_files_to_copy = [
                f"/home/{username}/flash-tv-scripts/services/flash-run-on-boot.service",
                f"/home/{username}/flash-tv-scripts/services/flash-periodic-restart.service"
            ]

            for service_file in service_files_to_copy:
                service_name = os.path.basename(service_file)
                result, error = self.process_runner.run_sudo_command(
                    ["cp", service_file, f"/etc/systemd/system/{service_name}"],
                    f"Copy {service_name} to system directory",
                    timeout_ms=10000
                )

                if error:
                    self.logger.error(f"Failed to copy {service_name}: {error}")
                    raise FlashTVError(
                        f"Failed to copy {service_name} to system directory: {error}",
                        ErrorType.PROCESS_ERROR,
                        recovery_action="Check sudo permissions"
                    )
                else:
                    self.logger.info(f"Successfully copied {service_name} to /etc/systemd/system/")

            # Reload systemctl daemon
            self.logger.info("Reloading systemctl daemon")
            result, error = self.process_runner.run_sudo_command(
                ["systemctl", "daemon-reload"],
                "Reload systemctl daemon",
                timeout_ms=10000
            )

            if error:
                self.logger.error(f"Failed to reload systemctl daemon: {error}")
                raise FlashTVError(
                    f"Failed to reload systemctl daemon: {error}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check systemctl permissions"
                )
            else:
                self.logger.info("Successfully reloaded systemctl daemon")

        except Exception as e:
            self.logger.error(f"Error configuring service files: {e}")
            raise FlashTVError(
                f"Failed to configure service files: {e}",
                ErrorType.CONFIGURATION_ERROR,
                recovery_action="Check service file paths and permissions"
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