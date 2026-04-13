"""Device locking step with comprehensive monitoring dashboard."""

from __future__ import annotations

import html
import datetime
import os
import shutil
import subprocess

from config.messages import MESSAGES, get_python_path
from config.participant_contract import (
    build_participant_full_id,
    get_gallery_dir,
    get_participant_data_dir,
    get_tv_power_csv_path,
)
from core import WizardStep
from core.event_store import EventType
from core.exceptions import handle_step_error
from models import StepStatus
from models.state_keys import UserInputKey
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QTextEdit,
    QWidget,
)
from utils.gaze_log_parser import GazeLogParser
from utils.log_tailer import StderrLogTailer
from utils.ui_factory import ButtonStyle


class DeviceLockingStep(WizardStep):
    """Step 11: Device Locking with Live Monitoring Dashboard."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.gaze_parser = GazeLogParser()
        self.stderr_tailer = StderrLogTailer(
            is_error_func=self.gaze_parser.is_known_minor_error,
            max_buffer_lines=500,
        )

        # Monitoring timer - use base class create_timer for automatic cleanup
        self.monitor_timer = self.create_timer(
            5000, self._update_dashboard, start=False
        )

    def create_content_widget(self) -> QWidget:
        """Create the monitoring dashboard UI."""
        content = QWidget()
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Overview
        overview_section = self._create_overview_section()
        main_layout.addWidget(overview_section)

        # Monitoring Dashboard
        dashboard_section = self._create_dashboard_section()
        main_layout.addWidget(dashboard_section, 1)

        # Device Lock Controls
        lock_section = self._create_lock_section()
        main_layout.addWidget(lock_section)

        # Final Instructions
        notes_section = self._create_notes_section()
        main_layout.addWidget(notes_section)

        # Continue button
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        return content

    def _create_overview_section(self) -> QWidget:
        """Create the overview section."""
        overview_group, overview_layout = self.ui_factory.create_group_box(
            "System Status Dashboard & Device Locking"
        )

        overview_text = self.ui_factory.create_label(
            "Verify all components work before locking. Dashboard updates every 5 seconds."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_dashboard_section(self) -> QWidget:
        """Create the comprehensive monitoring dashboard with two-column layout."""
        dashboard_group, dashboard_layout = self.ui_factory.create_group_box(
            "System Status (Updates every 5 seconds)"
        )

        # Two-column layout
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)

        # Left column: Basic system info
        left_column = self._create_basic_info_section()
        columns_layout.addWidget(left_column, stretch=1)

        # Right column: Services and logs
        right_column = self._create_services_and_logs_section()
        columns_layout.addWidget(right_column, stretch=1)

        dashboard_layout.addLayout(columns_layout)

        return dashboard_group

    def _create_basic_info_section(self) -> QWidget:
        """Create basic system information section (left column)."""
        group_box = QGroupBox("System Components")
        layout = self.ui_factory.create_vertical_layout(spacing=10)
        group_box.setLayout(layout)

        # Participant info
        participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
        device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
        full_id = build_participant_full_id(participant_id, device_id)

        participant_label = self.ui_factory.create_label(
            f"<b>Participant:</b> {full_id if full_id else '--'}"
        )
        layout.addWidget(participant_label)

        # Time sync status
        self.time_sync_label = self.ui_factory.create_label("<b>Time Sync:</b> --")
        layout.addWidget(self.time_sync_label)

        # Camera status
        self.camera_label = self.ui_factory.create_label("<b>Camera:</b> --")
        layout.addWidget(self.camera_label)

        # Smart plug status
        self.smart_plug_label = self.ui_factory.create_label("<b>Smart Plug:</b> --")
        layout.addWidget(self.smart_plug_label)

        # RTC times
        self.rtc_times_label = self.ui_factory.create_label(
            "<b>RTC Times:</b> --", word_wrap=True
        )
        layout.addWidget(self.rtc_times_label)

        return group_box

    def _create_services_and_logs_section(self) -> QWidget:
        """Create services and logs section (right column)."""
        group_box = QGroupBox("Services & Logs")
        layout = self.ui_factory.create_vertical_layout(spacing=10)
        group_box.setLayout(layout)

        # Services status
        services_header = self.ui_factory.create_label("<b>FLASH-TV Services:</b>")
        layout.addWidget(services_header)

        self.svc_flash_boot_label = self.ui_factory.create_label(
            "  flash-run-on-boot: --"
        )
        layout.addWidget(self.svc_flash_boot_label)

        self.svc_flash_periodic_label = self.ui_factory.create_label(
            "  flash-periodic: --"
        )
        layout.addWidget(self.svc_flash_periodic_label)

        self.svc_home_assistant_label = self.ui_factory.create_label(
            "  Home Assistant: --"
        )
        layout.addWidget(self.svc_home_assistant_label)

        layout.addSpacing(10)

        self.stderr_log_label = self.ui_factory.create_label(
            "<b>FLASH Error Log:</b><br><span style='color: #2e7d32;'>✅ No errors detected</span>",
            word_wrap=True,
        )
        layout.addWidget(self.stderr_log_label)

        # Last main gaze log line
        self.gaze_log_label = self.ui_factory.create_label(
            "<b>Last Gaze Log:</b> --", word_wrap=True
        )
        layout.addWidget(self.gaze_log_label)

        return group_box

    def _create_lock_section(self) -> QWidget:
        """Create device lock controls."""
        lock_group, lock_layout = self.ui_factory.create_group_box(
            "Turn Off WiFi and Lock Device"
        )

        # ES Gallery Copy button (only visible for ES participants)
        self.es_gallery_copy_button = self.ui_factory.create_action_button(
            "💾 Copy Gallery to External Drive (ES Study)",
            callback=self._copy_gallery_to_drive,
            style=ButtonStyle.PRIMARY,
            height=40,
        )
        self.es_gallery_copy_button.setVisible(False)  # Hidden by default
        lock_layout.addWidget(self.es_gallery_copy_button)

        # Status label for ES copy
        self.es_copy_status = self.ui_factory.create_label("")
        self.es_copy_status.setVisible(False)
        lock_layout.addWidget(self.es_copy_status)

        lock_layout.addSpacing(10)

        # Button to turn off WiFi and lock the device
        self.lock_device_button = self.ui_factory.create_action_button(
            "📡 Turn Off WiFi and Lock Device",
            callback=self._turnoff_wifi_and_lock,
            style=ButtonStyle.SUCCESS,
            height=50,
        )
        lock_layout.addWidget(self.lock_device_button)

        return lock_group

    def _check_es_participant(self) -> bool:
        """Check if this is an ES (exploratory study) participant."""
        participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
        return participant_id.upper().startswith("ES")

    @handle_step_error
    def _copy_gallery_to_drive(self, checked: bool = False) -> None:
        """Copy gallery faces to external hard drive for ES participants."""
        try:
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            username = self.state.get_user_input(UserInputKey.USERNAME, "")

            if not all([participant_id, device_id, username]):
                QMessageBox.warning(
                    self,
                    "Missing Information",
                    "Participant information is incomplete.",
                )
                return

            full_id = build_participant_full_id(participant_id, device_id)
            gallery_path = str(get_gallery_dir(username, participant_id, device_id))

            # Check if gallery exists
            if not os.path.exists(gallery_path):
                QMessageBox.warning(
                    self,
                    "Gallery Not Found",
                    f"Gallery folder not found at:\n{gallery_path}",
                )
                return

            # Let user select the external drive location
            from PySide6.QtWidgets import QFileDialog

            external_drive_path = QFileDialog.getExistingDirectory(
                self,
                "Select External Drive Location",
                f"/media/{username}",
                QFileDialog.Option.ShowDirsOnly,
            )

            if not external_drive_path:
                # User cancelled
                return

            # Create destination folder
            dest_folder = os.path.join(external_drive_path, "ES_galleries", full_id)
            os.makedirs(dest_folder, exist_ok=True)

            # Update status
            self.es_copy_status.setText("Copying gallery files...")
            self.es_copy_status.setStyleSheet("color: #1976d2; font-weight: bold;")
            self.es_copy_status.setVisible(True)
            self.es_gallery_copy_button.setEnabled(False)

            # Force UI update
            from PySide6.QtWidgets import QApplication

            QApplication.processEvents()

            # Copy gallery
            dest_gallery = os.path.join(dest_folder, f"{full_id}_faces")
            if os.path.exists(dest_gallery):
                shutil.rmtree(dest_gallery)
            shutil.copytree(gallery_path, dest_gallery)

            # Log to event store
            self.event_store.log_event(
                EventType.DATA_COPIED,
                step_id=self.step_definition.step_id,
                action="es_gallery_copied",
                details={
                    "participant_id": full_id,
                    "source": gallery_path,
                    "destination": dest_gallery,
                },
            )

            self.es_copy_status.setText(f"✅ Gallery copied to: {dest_gallery}")
            self.es_copy_status.setStyleSheet("color: #2e7d32; font-weight: bold;")
            self.es_gallery_copy_button.setEnabled(True)

            self.logger.info(f"ES gallery copied to {dest_gallery}")

            QMessageBox.information(
                self,
                "Gallery Copied",
                f"Gallery successfully copied to:\n{dest_gallery}",
            )

        except Exception as e:
            self.logger.error(f"Error copying ES gallery: {e}")
            self.es_copy_status.setText(f"❌ Copy failed: {e}")
            self.es_copy_status.setStyleSheet("color: #c62828; font-weight: bold;")
            self.es_gallery_copy_button.setEnabled(True)

            self.event_store.log_error(
                step_id=self.step_definition.step_id,
                action="es_gallery_copy_failed",
                error_message=str(e),
            )

            QMessageBox.critical(
                self,
                "Copy Failed",
                f"Failed to copy gallery:\n{e}",
            )

    def _create_notes_section(self) -> QWidget:
        """Create final instructions section."""
        notes_group, notes_layout = self.ui_factory.create_group_box(
            "Final Instructions for Participant"
        )

        self.instructions_text = QTextEdit()
        self.instructions_text.setMaximumHeight(80)
        self.instructions_text.setPlaceholderText(
            "Add any specific notes for this participant (care instructions, special arrangements, contact info)..."
        )
        notes_layout.addWidget(self.instructions_text)

        return notes_group

    def _create_continue_section(self):
        button_layout = self.ui_factory.create_vertical_layout(spacing=6)
        self.finish_guidance_label = self.ui_factory.create_label(
            "Complete the locking step above. When everything is finished, the 'Complete Setup' button at the top of the window will close the wizard.",
            style="color: #555; padding-top: 4px;",
        )
        button_layout.addWidget(self.finish_guidance_label)

        return button_layout

    def _update_dashboard(self) -> None:
        """Update all dashboard components with live data."""
        try:
            # Update time sync
            time_synced = self.state.get_user_input(UserInputKey.TIME_SYNCED, False)
            self.time_sync_label.setText(
                f"<b>Time Sync:</b> {'✅ Verified' if time_synced else '⚠️ Not verified'}"
            )

            # Update camera
            camera_tested = self.state.get_user_input(UserInputKey.CAMERA_TESTED, False)
            camera_path = self.state.get_user_input(UserInputKey.SELECTED_CAMERA, "")
            if camera_tested:
                self.camera_label.setText(f"<b>Camera:</b> ✅ Tested ({camera_path})")
            else:
                self.camera_label.setText("<b>Camera:</b> ❌ Not tested")

            # Update smart plug with last power reading
            smart_plug_verified = self.state.get_user_input(
                UserInputKey.SMART_PLUG_VERIFIED, False
            )
            last_power = self._get_last_power_reading()

            if smart_plug_verified:
                self.smart_plug_label.setText(
                    f"<b>Smart Plug:</b> ✅ Verified | Last Reading: {last_power}"
                )
            else:
                self.smart_plug_label.setText(
                    f"<b>Smart Plug:</b> ❌ Not verified | Last Reading: {last_power}"
                )

            self.stderr_log_label.setText(self._get_last_flash_error())

            # Update last main gaze log line
            last_gaze_line = self._get_last_gaze_log_line()
            self.gaze_log_label.setText(
                f"<b>Last Main Gaze Log Line:</b> {last_gaze_line}"
            )

            # Update RTC times
            rtc_times = self._get_rtc_times()
            self.rtc_times_label.setText(f"<b>RTC Times:</b> {rtc_times}")

            # Update services
            self._update_services_status()

        except Exception as e:
            self.logger.error(f"Error updating dashboard: {e}")

    def _update_services_status(self) -> None:
        """Update services status."""
        # Check flash-run-on-boot
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "flash-run-on-boot.service"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.stdout.strip() == "active":
                self.svc_flash_boot_label.setText("  flash-run-on-boot: ✅ Running")
            else:
                self.svc_flash_boot_label.setText(
                    f"  flash-run-on-boot: ❌ {result.stdout.strip()}"
                )
        except Exception:
            self.svc_flash_boot_label.setText("  flash-run-on-boot: ⚠️ Unknown")

        # Check flash-periodic-restart
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "flash-periodic-restart.service"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.stdout.strip() == "active":
                self.svc_flash_periodic_label.setText("  flash-periodic: ✅ Running")
            else:
                self.svc_flash_periodic_label.setText(
                    f"  flash-periodic: ❌ {result.stdout.strip()}"
                )
        except Exception:
            self.svc_flash_periodic_label.setText("  flash-periodic: ⚠️ Unknown")

        # Check Home Assistant
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    "name=homeassistant",
                    "--format",
                    "{{.Status}}",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if "Up" in result.stdout:
                self.svc_home_assistant_label.setText("  Home Assistant: ✅ Running")
            else:
                self.svc_home_assistant_label.setText("  Home Assistant: ❌ Stopped")
        except Exception:
            self.svc_home_assistant_label.setText("  Home Assistant: ⚠️ Unknown")

    def _get_last_power_reading(self) -> str:
        """Get the last TV power reading from CSV."""
        try:
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            username = self.state.get_user_input(UserInputKey.USERNAME, "")

            if not all([participant_id, device_id, username]):
                return "No data"

            csv_file = str(get_tv_power_csv_path(username, participant_id, device_id))

            if os.path.exists(csv_file):
                with open(csv_file, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        parts = last_line.split(";")
                        if len(parts) >= 3:
                            power = parts[0]
                            time_str = parts[2]
                            return f"{power}W at {time_str}"
            return "No data yet"
        except Exception as e:
            self.logger.debug(f"Error reading power data: {e}")
            return "Error"

    def _get_last_flash_error(self) -> str:
        try:
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            username = self.state.get_user_input(UserInputKey.USERNAME, "")

            if not all([participant_id, device_id, username]):
                return self._format_flash_error_log([])

            full_id = build_participant_full_id(participant_id, device_id)
            data_path = str(get_participant_data_dir(username, participant_id, device_id))
            stderr_log = f"{data_path}/{full_id}_flash_logstderr.log"

            if not os.path.exists(stderr_log):
                return self._format_missing_flash_error_log()

            stderr_lines, actual_errors = (
                self.stderr_tailer.get_all_content_with_errors(stderr_log)
            )
            if not stderr_lines:
                return self._format_flash_error_log([])

            return self._format_flash_error_log(actual_errors)
        except Exception as e:
            self.logger.debug(f"Error reading stderr log: {e}")
            return self._format_flash_error_log([])

    def _format_missing_flash_error_log(self) -> str:
        return "<b>FLASH Error Log:</b><br><span>No log file found</span>"

    def _format_flash_error_log(self, error_lines: list[str]) -> str:
        if not error_lines:
            return (
                "<b>FLASH Error Log:</b><br>"
                "<span style='color: #2e7d32;'>✅ No errors detected</span>"
            )

        recent_errors = error_lines[-20:]
        escaped_lines = [html.escape(line) for line in recent_errors]
        joined_lines = "<br>".join(escaped_lines)
        return (
            "<b>FLASH Error Log:</b><br>"
            f"<span style='color: #c62828;'>{joined_lines}</span>"
        )

    def _get_last_gaze_log_line(self) -> str:
        """Get the last line from the main gaze log file."""
        try:
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            username = self.state.get_user_input(UserInputKey.USERNAME, "")

            if not all([participant_id, device_id, username]):
                return "No log yet"

            full_id = build_participant_full_id(participant_id, device_id)
            data_path = str(get_participant_data_dir(username, participant_id, device_id))

            # Find the most recent main gaze log file
            # Pattern: {full_id}_flash_log_YYYY-MM-DD_HH-MM-SS.txt (not _rot or _reg)
            import glob

            log_pattern = os.path.join(data_path, f"{full_id}_flash_log_*.txt")
            log_files = glob.glob(log_pattern)

            # Filter out _rot.txt and _reg.txt files
            main_logs = [
                f
                for f in log_files
                if not (f.endswith("_rot.txt") or f.endswith("_reg.txt"))
            ]

            if main_logs:
                latest_log = self._select_latest_main_flash_log(main_logs, full_id)

                with open(latest_log, "r", errors="ignore") as f:
                    lines = f.readlines()
                    if lines:
                        # Get last non-empty line
                        for line in reversed(lines):
                            line = line.strip()
                            if line:
                                # Truncate if too long
                                return line[:150] + "..." if len(line) > 150 else line

            return "No log entries yet"
        except Exception as e:
            self.logger.debug(f"Error reading gaze log: {e}")
            return "Error reading log"

    def _select_latest_main_flash_log(
        self, main_logs: list[str], full_id: str
    ) -> str:
        parsed_logs: list[tuple[datetime.datetime, str]] = []

        for log_path in main_logs:
            timestamp = self._parse_main_flash_log_timestamp(log_path, full_id)
            if timestamp is not None:
                parsed_logs.append((timestamp, log_path))

        if parsed_logs:
            return max(parsed_logs, key=lambda item: (item[0], item[1]))[1]

        return max(main_logs, key=os.path.getmtime)

    def _parse_main_flash_log_timestamp(
        self, log_path: str, full_id: str
    ) -> datetime.datetime | None:
        filename = os.path.basename(log_path)
        prefix = f"{full_id}_flash_log_"

        if not (filename.startswith(prefix) and filename.endswith(".txt")):
            return None

        timestamp_str = filename.removeprefix(prefix).removesuffix(".txt")

        try:
            return datetime.datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
        except ValueError:
            return None

    def _get_rtc_times(self) -> str:
        """Get RTC times from both RTCs and system time using the existing Python script."""
        try:
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            username = self.state.get_user_input(UserInputKey.USERNAME, "")

            if not all([participant_id, device_id, username]):
                return "No data"

            full_id = build_participant_full_id(participant_id, device_id)

            # Path to the RTC check script
            script_path = f"/home/{username}/flash-tv-scripts/python_scripts/update_or_check_system_time_from_RTCs.py"
            data_path = str(get_participant_data_dir(username, participant_id, device_id))
            start_date_file = f"{data_path}/{full_id}_start_date.txt"
            python_path = get_python_path(username)

            # Run the RTC check script
            result = subprocess.run(
                [python_path, script_path, "check", start_date_file],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                # Parse the output to extract key times
                lines = output.split("\n")

                system_time = "N/A"
                rtc0_time = "N/A"
                rtc1_time = "N/A"
                external_rtc_time = "N/A"

                import re

                for line in lines:
                    if "Local time:" in line:
                        # Extract system time from timedatectl output
                        # Format: "Local time: Wed 2025-01-15 14:30:45 EST"
                        parts = line.split("Local time:", 1)
                        if len(parts) > 1:
                            time_str = parts[1].strip()
                            # Try to extract date and time using regex
                            # Pattern: skip weekday, extract date and time
                            match = re.search(
                                r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", time_str
                            )
                            if match:
                                system_time = match.group(0)
                            else:
                                # Fallback: split and take date + time parts
                                time_parts = time_str.split()
                                if len(time_parts) >= 3:
                                    system_time = " ".join(time_parts[1:3])
                    elif "Time from internal RTC rtc0" in line:
                        # Format: "Time from internal RTC rtc0 (PSEQ_RTC, being used) is: 2025-01-15 14:30:45.123456..."
                        parts = line.split("is:", 1)
                        if len(parts) > 1:
                            rtc0_time = parts[1].strip()
                            # Extract just the datetime if present
                            match = re.search(
                                r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", rtc0_time
                            )
                            if match:
                                rtc0_time = match.group(0)
                            elif (
                                not rtc0_time
                                or "None" in rtc0_time
                                or "Unable" in rtc0_time
                            ):
                                rtc0_time = "Not available"
                    elif "Time from external RTC" in line:
                        # Format: "Time from external RTC (DS3231) is: 2025-01-15 14:30:45" or error message
                        parts = line.split("is:", 1)
                        if len(parts) > 1:
                            external_rtc_time = parts[1].strip()
                            # Check if it's an error message
                            if "was incomparable or incorrect" in external_rtc_time:
                                # Extract datetime from error message
                                match = re.search(
                                    r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})",
                                    external_rtc_time,
                                )
                                if match:
                                    external_rtc_time = (
                                        f"{match.group(1)} (⚠️ validation failed)"
                                    )
                                else:
                                    external_rtc_time = "Validation failed"
                            else:
                                # Extract just the datetime
                                match = re.search(
                                    r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}",
                                    external_rtc_time,
                                )
                                if match:
                                    external_rtc_time = match.group(0)
                                elif (
                                    not external_rtc_time or "None" in external_rtc_time
                                ):
                                    external_rtc_time = "Not available"
                    elif "Time from internal RTC rtc1" in line:
                        # Format: "Time from internal RTC rtc1 (tegra-RTC, not being used) is: 2025-01-15 14:30:45..."
                        parts = line.split("is:", 1)
                        if len(parts) > 1:
                            rtc1_time = parts[1].strip()
                            # Extract just the datetime if present
                            match = re.search(
                                r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", rtc1_time
                            )
                            if match:
                                rtc1_time = match.group(0)
                            elif (
                                not rtc1_time
                                or "None" in rtc1_time
                                or "Unable" in rtc1_time
                            ):
                                rtc1_time = "Not available"

                # Format the display - Note: External RTC (DS3231) may be exposed as /dev/rtc1 on some systems
                return f"System: {system_time} | RTC0: {rtc0_time} | External RTC: {external_rtc_time} | RTC1: {rtc1_time}"
            else:
                self.logger.debug(f"RTC script error: {result.stderr}")
                return "Error running RTC script"

        except Exception as e:
            self.logger.debug(f"Error reading RTC times: {e}")
            return "Error"

    @handle_step_error
    def _turnoff_wifi_and_lock(self, checked: bool = False) -> None:
        """Turn off WiFi and lock the device screen."""
        try:
            self.logger.info("Attempting to turn off WiFi and lock device")

            # Step 1: Turn off WiFi
            wifi_disabled = False
            wifi_commands = [
                ["nmcli", "radio", "wifi", "off"],  # NetworkManager
                ["rfkill", "block", "wifi"],  # rfkill
            ]

            for cmd in wifi_commands:
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        self.logger.info(
                            f"WiFi disabled successfully using: {' '.join(cmd)}"
                        )
                        wifi_disabled = True
                        break
                except FileNotFoundError:
                    self.logger.debug(f"WiFi command not found: {' '.join(cmd)}")
                    continue
                except Exception as e:
                    self.logger.debug(
                        f"Failed to disable WiFi with {' '.join(cmd)}: {e}"
                    )
                    continue

            if not wifi_disabled:
                self.logger.warning("Could not disable WiFi automatically")
                QMessageBox.warning(
                    self,
                    "WiFi Turnoff Failed",
                    "WiFi could not be turned off automatically.\n\n"
                    "What to try next:\n"
                    "• Turn off WiFi manually from the network icon\n"
                    "• Then click the lock button again\n\n"
                    "When to ask for help:\n"
                    "• If WiFi will not turn off manually, ask technical support.",
                )
                return

            # Step 2: Lock the device
            lock_commands = [
                ["loginctl", "lock-session"],  # Modern systemd method
                ["gnome-screensaver-command", "-l"],  # GNOME screensaver
                ["xdg-screensaver", "lock"],  # Generic XDG method
            ]

            locked = False
            for cmd in lock_commands:
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        self.logger.info(
                            f"Device locked successfully using: {' '.join(cmd)}"
                        )
                        locked = True
                        break
                except FileNotFoundError:
                    self.logger.debug(f"Lock command not found: {' '.join(cmd)}")
                    continue
                except Exception as e:
                    self.logger.debug(f"Failed to lock with {' '.join(cmd)}: {e}")
                    continue

            if locked:
                self._mark_setup_complete()
                # No dialog box - screen is locked now
            else:
                self.logger.error("All lock methods failed")
                QMessageBox.warning(
                    self,
                    "Lock Failed",
                    "WiFi was turned off, but the device did not lock automatically.\n\n"
                    "What to try next:\n"
                    "• Lock the device manually from the power menu\n"
                    "• Or press the Super key, type 'lock', and press Enter\n\n"
                    "When to ask for help:\n"
                    "• If the device still will not lock, ask technical support.",
                )

        except Exception as e:
            self.logger.error(f"Error attempting to turn off WiFi and lock device: {e}")
            QMessageBox.critical(
                self,
                "Error",
                "The final lock step could not finish because of an unexpected problem.\n\n"
                "What to try next:\n"
                "• Try the lock step once more\n"
                "• If needed, turn off WiFi and lock the device manually\n\n"
                "When to ask for help:\n"
                "• If the device still will not lock safely, ask technical support.",
            )

    @handle_step_error
    def _mark_setup_complete(self) -> None:
        """Mark the entire setup as complete."""
        instructions = self.instructions_text.toPlainText().strip()
        if instructions:
            self.state.set_user_input(UserInputKey.FINAL_INSTRUCTIONS, instructions)
            self._save_notes_to_file("Device Locking", instructions)

        self.state.set_user_input(UserInputKey.DEVICE_LOCKED, True)
        self.state.set_user_input(UserInputKey.SETUP_COMPLETE, True)

        if self.state_manager:
            self.state_manager.save_state(self.state)

        self.update_status(StepStatus.COMPLETED)
        self.finish_guidance_label.setText(
            "✅ Device locking is complete. Click 'Complete Setup' at the top of the window to finish and close the wizard."
        )
        self.finish_guidance_label.setStyleSheet(
            "color: #2e7d32; font-weight: bold; padding-top: 4px;"
        )

        self.logger.info("Device locking step completed")

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the device locking step."""
        super().activate_step()

        self.logger.info("Device locking step activated")

        # Start dashboard monitoring
        self.monitor_timer.start(5000)  # Update every 5 seconds

        self.stderr_tailer.reset()

        # Show ES gallery copy button if this is an ES participant
        if self._check_es_participant():
            self.es_gallery_copy_button.setVisible(True)
            self.logger.info("ES participant detected - showing gallery copy button")

        # Load any saved instructions
        saved_instructions = self.state.get_user_input(
            UserInputKey.FINAL_INSTRUCTIONS, ""
        )
        if saved_instructions:
            self.instructions_text.setText(saved_instructions)

        # Check if already completed
        if self.state.get_user_input(UserInputKey.DEVICE_LOCKED, False):
            self.update_status(StepStatus.COMPLETED)
            self.finish_guidance_label.setText(
                "✅ Device locking is already complete. Click 'Complete Setup' at the top of the window to finish and close the wizard."
            )
            self.finish_guidance_label.setStyleSheet(
                "color: #2e7d32; font-weight: bold; padding-top: 4px;"
            )
            self.logger.info("Restored device locking completion state")

        # Do initial dashboard update
        self._update_dashboard()

    def deactivate_step(self) -> None:
        """Deactivate step when navigating away."""
        self.logger.info("Deactivating device locking step")
        super().deactivate_step()  # Base class handles timer cleanup

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Device locking step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
