"""Device locking step with comprehensive monitoring dashboard."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGridLayout,
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

from core import WizardStep
from core.exceptions import handle_step_error
from models import StepStatus
from utils.ui_factory import ButtonStyle


class DeviceLockingStep(WizardStep):
    """Step 11: Device Locking with Live Monitoring Dashboard."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._update_dashboard)

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
        overview_group, overview_layout = self.ui_factory.create_group_box("System Status Dashboard & Device Locking")

        overview_text = self.ui_factory.create_label(
            "Monitor all system components in real-time before locking the device. "
            "This dashboard updates every 5 seconds to show current system status. "
            "Verify all components are working properly before locking."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_dashboard_section(self) -> QWidget:
        """Create the comprehensive monitoring dashboard."""
        dashboard_group, dashboard_layout = self.ui_factory.create_group_box("System Status (Updates every 5 seconds)")

        # Simple vertical layout with clear sections
        content_layout = self.ui_factory.create_vertical_layout(spacing=15)

        # Basic info section
        basic_info = self._create_basic_info_section()
        content_layout.addWidget(basic_info)

        # Services status
        services_status = self._create_services_status_section()
        content_layout.addWidget(services_status)

        dashboard_layout.addLayout(content_layout)

        return dashboard_group

    def _create_basic_info_section(self) -> QWidget:
        """Create basic system information section with clean layout."""
        box = QWidget()
        layout = self.ui_factory.create_vertical_layout(spacing=8)
        box.setLayout(layout)

        # Participant info
        participant_id = self.state.get_user_input("participant_id", "")
        device_id = self.state.get_user_input("device_id", "")
        full_id = f"{participant_id}{device_id}" if device_id else participant_id

        participant_label = QLabel(f"<b>Participant:</b> {full_id if full_id else '--'}")
        participant_label.setFont(QFont("Arial", 22))
        layout.addWidget(participant_label)

        # Time sync status
        self.time_sync_label = QLabel("<b>Time Sync:</b> --")
        self.time_sync_label.setFont(QFont("Arial", 22))
        layout.addWidget(self.time_sync_label)

        # Camera status
        self.camera_label = QLabel("<b>Camera:</b> --")
        self.camera_label.setFont(QFont("Arial", 22))
        layout.addWidget(self.camera_label)

        # Smart plug status
        self.smart_plug_label = QLabel("<b>Smart Plug:</b> --")
        self.smart_plug_label.setFont(QFont("Arial", 22))
        layout.addWidget(self.smart_plug_label)

        # Last FLASH error from stderr
        self.stderr_log_label = QLabel("<b>Last FLASH Error:</b> --")
        self.stderr_log_label.setFont(QFont("Arial", 22))
        self.stderr_log_label.setWordWrap(True)
        layout.addWidget(self.stderr_log_label)

        # Last main gaze log line
        self.gaze_log_label = QLabel("<b>Last Main Gaze Log Line:</b> --")
        self.gaze_log_label.setFont(QFont("Arial", 22))
        self.gaze_log_label.setWordWrap(True)
        layout.addWidget(self.gaze_log_label)

        # RTC times
        self.rtc_times_label = QLabel("<b>RTC Times:</b> --")
        self.rtc_times_label.setFont(QFont("Arial", 22))
        layout.addWidget(self.rtc_times_label)

        return box

    def _create_services_status_section(self) -> QWidget:
        """Create services status section."""
        box = QWidget()
        layout = self.ui_factory.create_vertical_layout(spacing=8)
        box.setLayout(layout)

        services_header = QLabel("<b>FLASH-TV Services:</b>")
        services_header.setFont(QFont("Arial", 22))
        layout.addWidget(services_header)

        self.svc_flash_boot_label = QLabel("  flash-run-on-boot: --")
        self.svc_flash_boot_label.setFont(QFont("Arial", 22))
        layout.addWidget(self.svc_flash_boot_label)

        self.svc_flash_periodic_label = QLabel("  flash-periodic: --")
        self.svc_flash_periodic_label.setFont(QFont("Arial", 22))
        layout.addWidget(self.svc_flash_periodic_label)

        self.svc_home_assistant_label = QLabel("  Home Assistant: --")
        self.svc_home_assistant_label.setFont(QFont("Arial", 22))
        layout.addWidget(self.svc_home_assistant_label)

        return box

    def _create_lock_section(self) -> QWidget:
        """Create device lock controls."""
        lock_group, lock_layout = self.ui_factory.create_group_box("Turn Off WiFi and Lock Device")

        lock_info = self.ui_factory.create_label("After verifying all systems are working properly above, turn off WiFi and lock the device to complete setup.")
        lock_info.setFont(QFont("Arial", 22))
        lock_layout.addWidget(lock_info)

        lock_layout.addSpacing(15)

        # Button to turn off WiFi and lock the device
        self.lock_device_button = self.ui_factory.create_action_button(
            "📡 Turn Off WiFi and Lock Device",
            callback=self._turnoff_wifi_and_lock,
            style=ButtonStyle.SUCCESS,
            height=50,
        )
        lock_layout.addWidget(self.lock_device_button)

        return lock_group

    def _create_notes_section(self) -> QWidget:
        """Create final instructions section."""
        notes_group, notes_layout = self.ui_factory.create_group_box("Final Instructions for Participant")

        instructions_label = self.ui_factory.create_label("Additional Notes for Participant:")
        notes_layout.addWidget(instructions_label)

        self.instructions_text = QTextEdit()
        self.instructions_text.setMaximumHeight(80)
        self.instructions_text.setPlaceholderText("Add any specific notes for this participant...")
        notes_layout.addWidget(self.instructions_text)

        return notes_group

    def _create_continue_section(self):
        """Create continue button section."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text="Setup Complete - Device Locked"
        )
        self.continue_button.setEnabled(False)

        return button_layout

    def _update_dashboard(self) -> None:
        """Update all dashboard components with live data."""
        try:
            # Update time sync
            time_synced = self.state.get_user_input("time_synced", False)
            self.time_sync_label.setText(f"<b>Time Sync:</b> {'✅ Verified' if time_synced else '⚠️ Not verified'}")

            # Update camera
            camera_tested = self.state.get_user_input("camera_tested", False)
            camera_path = self.state.get_user_input("selected_camera", "")
            if camera_tested:
                self.camera_label.setText(f"<b>Camera:</b> ✅ Tested ({camera_path})")
            else:
                self.camera_label.setText(f"<b>Camera:</b> ❌ Not tested")

            # Update smart plug with last power reading
            smart_plug_verified = self.state.get_user_input("smart_plug_verified", False)
            last_power = self._get_last_power_reading()

            if smart_plug_verified:
                self.smart_plug_label.setText(f"<b>Smart Plug:</b> ✅ Verified | Last Reading: {last_power}")
            else:
                self.smart_plug_label.setText(f"<b>Smart Plug:</b> ❌ Not verified | Last Reading: {last_power}")

            # Update last FLASH error from stderr
            last_error = self._get_last_flash_error()
            self.stderr_log_label.setText(f"<b>Last FLASH Error:</b> {last_error}")

            # Update last main gaze log line
            last_gaze_line = self._get_last_gaze_log_line()
            self.gaze_log_label.setText(f"<b>Last Main Gaze Log Line:</b> {last_gaze_line}")

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
            result = subprocess.run(["systemctl", "is-active", "flash-run-on-boot.service"], capture_output=True, text=True, timeout=2)
            if result.stdout.strip() == "active":
                self.svc_flash_boot_label.setText("  flash-run-on-boot: ✅ Running")
            else:
                self.svc_flash_boot_label.setText(f"  flash-run-on-boot: ❌ {result.stdout.strip()}")
        except Exception:
            self.svc_flash_boot_label.setText("  flash-run-on-boot: ⚠️ Unknown")

        # Check flash-periodic-restart
        try:
            result = subprocess.run(["systemctl", "is-active", "flash-periodic-restart.service"], capture_output=True, text=True, timeout=2)
            if result.stdout.strip() == "active":
                self.svc_flash_periodic_label.setText("  flash-periodic: ✅ Running")
            else:
                self.svc_flash_periodic_label.setText(f"  flash-periodic: ❌ {result.stdout.strip()}")
        except Exception:
            self.svc_flash_periodic_label.setText("  flash-periodic: ⚠️ Unknown")

        # Check Home Assistant
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=homeassistant", "--format", "{{.Status}}"], capture_output=True, text=True, timeout=2
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
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not all([participant_id, device_id, username]):
                return "No data"

            full_id = f"{participant_id}{device_id}"
            csv_file = f"/home/{username}/data/{full_id}_data/{full_id}_tv_power_5s.csv"

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
        """Get the last FLASH error from stderr log."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not all([participant_id, device_id, username]):
                return "No errors yet"

            full_id = f"{participant_id}{device_id}"
            stderr_log = f"/home/{username}/data/{full_id}_data/{full_id}_flash_logstderr.log"

            if os.path.exists(stderr_log):
                with open(stderr_log, "r", errors="ignore") as f:
                    lines = f.readlines()
                    if lines:
                        # Get last non-empty line that looks like an error
                        # Errors typically contain keywords like "error", "Error", "failed", "Failed", "exception", "Exception"
                        for line in reversed(lines):
                            line = line.strip()
                            if line:
                                # Check if it's an error line
                                lower_line = line.lower()
                                if any(keyword in lower_line for keyword in ["error", "failed", "exception", "traceback", "warning"]):
                                    # Truncate if too long
                                    return line[:100] + "..." if len(line) > 100 else line
                        # If no error keywords found, return the last line anyway
                        last_line = lines[-1].strip()
                        if last_line:
                            return last_line[:100] + "..." if len(last_line) > 100 else last_line
            return "No errors yet"
        except Exception as e:
            self.logger.debug(f"Error reading stderr log: {e}")
            return "Error reading log"

    def _get_last_gaze_log_line(self) -> str:
        """Get the last line from the main gaze log file."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not all([participant_id, device_id, username]):
                return "No log yet"

            full_id = f"{participant_id}{device_id}"
            data_path = f"/home/{username}/data/{full_id}_data"

            # Find the most recent main gaze log file
            # Pattern: {full_id}_flash_log_YYYY-MM-DD_HH-MM-SS.txt (not _rot or _reg)
            import glob
            log_pattern = os.path.join(data_path, f"{full_id}_flash_log_*.txt")
            log_files = glob.glob(log_pattern)

            # Filter out _rot.txt and _reg.txt files
            main_logs = [f for f in log_files if not (f.endswith("_rot.txt") or f.endswith("_reg.txt"))]

            if main_logs:
                # Get the most recent log file
                latest_log = max(main_logs, key=os.path.getmtime)

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

    def _get_rtc_times(self) -> str:
        """Get RTC times from both RTCs and system time using the existing Python script."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not all([participant_id, device_id, username]):
                return "No data"

            full_id = f"{participant_id}{device_id}"

            # Path to the RTC check script
            script_path = f"/home/{username}/flash-tv-scripts/python_scripts/update_or_check_system_time_from_RTCs.py"
            start_datetime_file = f"/home/{username}/data/{full_id}_data/{full_id}_start_datetime.txt"
            python_path = f"/home/{username}/py38/bin/python"

            # Run the RTC check script
            result = subprocess.run(
                [python_path, script_path, "check", start_datetime_file],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                # Parse the output to extract key times
                lines = output.split('\n')

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
                            match = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', time_str)
                            if match:
                                system_time = match.group(0)
                            else:
                                # Fallback: split and take date + time parts
                                time_parts = time_str.split()
                                if len(time_parts) >= 3:
                                    system_time = ' '.join(time_parts[1:3])
                    elif "Time from internal RTC rtc0" in line:
                        # Format: "Time from internal RTC rtc0 (PSEQ_RTC, being used) is: 2025-01-15 14:30:45.123456..."
                        parts = line.split("is:", 1)
                        if len(parts) > 1:
                            rtc0_time = parts[1].strip()
                            # Extract just the datetime if present
                            match = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', rtc0_time)
                            if match:
                                rtc0_time = match.group(0)
                            elif not rtc0_time or "None" in rtc0_time or "Unable" in rtc0_time:
                                rtc0_time = "Not available"
                    elif "Time from external RTC" in line:
                        # Format: "Time from external RTC (DS3231) is: 2025-01-15 14:30:45" or error message
                        parts = line.split("is:", 1)
                        if len(parts) > 1:
                            external_rtc_time = parts[1].strip()
                            # Check if it's an error message
                            if "was incomparable or incorrect" in external_rtc_time:
                                # Extract datetime from error message
                                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', external_rtc_time)
                                if match:
                                    external_rtc_time = f"{match.group(1)} (⚠️ validation failed)"
                                else:
                                    external_rtc_time = "Validation failed"
                            else:
                                # Extract just the datetime
                                match = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', external_rtc_time)
                                if match:
                                    external_rtc_time = match.group(0)
                                elif not external_rtc_time or "None" in external_rtc_time:
                                    external_rtc_time = "Not available"
                    elif "Time from internal RTC rtc1" in line:
                        # Format: "Time from internal RTC rtc1 (tegra-RTC, not being used) is: 2025-01-15 14:30:45..."
                        parts = line.split("is:", 1)
                        if len(parts) > 1:
                            rtc1_time = parts[1].strip()
                            # Extract just the datetime if present
                            match = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', rtc1_time)
                            if match:
                                rtc1_time = match.group(0)
                            elif not rtc1_time or "None" in rtc1_time or "Unable" in rtc1_time:
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
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.logger.info(f"WiFi disabled successfully using: {' '.join(cmd)}")
                        wifi_disabled = True
                        break
                except FileNotFoundError:
                    self.logger.debug(f"WiFi command not found: {' '.join(cmd)}")
                    continue
                except Exception as e:
                    self.logger.debug(f"Failed to disable WiFi with {' '.join(cmd)}: {e}")
                    continue

            if not wifi_disabled:
                self.logger.warning("Could not disable WiFi automatically")
                QMessageBox.warning(
                    self,
                    "WiFi Turnoff Failed",
                    "Could not turn off WiFi automatically.\n\n"
                    "Please turn off WiFi manually:\n"
                    "Click network icon → Turn off WiFi\n\n"
                    "Then click the button again to lock the device.",
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
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.logger.info(f"Device locked successfully using: {' '.join(cmd)}")
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
                    "WiFi has been turned off, but could not lock the device automatically.\n\n"
                    "Please lock the device manually:\n"
                    "Click the power button (top right) → Lock\n"
                    "Or press Super key → Type 'lock' → Enter",
                )

        except Exception as e:
            self.logger.error(f"Error attempting to turn off WiFi and lock device: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred:\n{e}",
            )

    @handle_step_error
    def _mark_setup_complete(self) -> None:
        """Mark the entire setup as complete."""
        instructions = self.instructions_text.toPlainText().strip()
        if instructions:
            self.state.set_user_input("final_instructions", instructions)
            self._save_notes_to_file("Device Locking", instructions)

        self.state.set_user_input("device_locked", True)
        self.state.set_user_input("setup_complete", True)

        if self.state_manager:
            self.state_manager.save_state(self.state)

        self.continue_button.setEnabled(True)
        self.update_status(StepStatus.COMPLETED)

        self.logger.info("Device locking step completed")

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click."""
        if self.state.get_user_input("device_locked", False):
            QMessageBox.information(
                self,
                "Setup Complete!",
                "FLASH-TV setup is now complete!\n\nThe system is ready for data collection.\nParticipant can resume normal TV viewing.",
            )
            self.request_next_step.emit()

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the device locking step."""
        super().activate_step()

        self.logger.info("Device locking step activated")

        # Start dashboard monitoring
        self.monitor_timer.start(5000)  # Update every 5 seconds

        # Load any saved instructions
        saved_instructions = self.state.get_user_input("final_instructions", "")
        if saved_instructions:
            self.instructions_text.setText(saved_instructions)

        # Check if already completed
        if self.state.get_user_input("device_locked", False):
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)
            self.logger.info("Restored device locking completion state")

        # Do initial dashboard update
        self._update_dashboard()

    def deactivate_step(self) -> None:
        """Deactivate step when navigating away - stop timers."""
        try:
            self.logger.info("Deactivating device locking step")

            # Stop monitor timer to prevent resource leaks
            if hasattr(self, "monitor_timer") and self.monitor_timer.isActive():
                self.monitor_timer.stop()
                self.logger.info("Stopped monitor timer on deactivation")

        except Exception as e:
            self.logger.error(f"Error during step deactivation: {e}")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Stop monitoring timer
            self.monitor_timer.stop()

            # Final state save
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Device locking step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
