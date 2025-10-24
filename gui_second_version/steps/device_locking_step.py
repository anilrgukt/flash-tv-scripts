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
        overview_group, overview_layout = self.ui_factory.create_group_box(
            "System Status Dashboard & Device Locking"
        )

        overview_text = self.ui_factory.create_label(
            "Monitor all system components in real-time before locking the device. "
            "This dashboard updates every 5 seconds to show current system status. "
            "Verify all components are working properly before locking."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_dashboard_section(self) -> QWidget:
        """Create the comprehensive monitoring dashboard."""
        dashboard_group, dashboard_layout = self.ui_factory.create_group_box(
            "🔍 Live System Monitoring (Updates every 5 seconds)"
        )

        # Create grid for organized status display
        grid_layout = QGridLayout()
        grid_layout.setSpacing(12)

        # Row 0: System Information & Network & Time
        sys_info_box = self._create_system_info_box()
        grid_layout.addWidget(sys_info_box, 0, 0)

        network_box = self._create_network_box()
        grid_layout.addWidget(network_box, 0, 1)

        time_box = self._create_time_box()
        grid_layout.addWidget(time_box, 0, 2)

        # Set equal column stretch for top row
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)

        # Row 1: Smart Plug Status (full width)
        smart_plug_box = self._create_smart_plug_box()
        grid_layout.addWidget(smart_plug_box, 1, 0, 1, 3)

        # Row 2: Camera Status and Services Status
        camera_box = self._create_camera_box()
        grid_layout.addWidget(camera_box, 2, 0, 1, 1)

        services_box = self._create_services_box()
        grid_layout.addWidget(services_box, 2, 1, 1, 2)

        # Row 3: Recent Errors
        errors_box = self._create_errors_box()
        grid_layout.addWidget(errors_box, 3, 0, 1, 3)

        dashboard_layout.addLayout(grid_layout)

        return dashboard_group

    def _create_system_info_box(self) -> QWidget:
        """Create system information status box."""
        box, layout = self.ui_factory.create_group_box("System Information")
        box.setMinimumHeight(150)

        self.sys_participant_id = self.ui_factory.create_label("Participant: --")
        self.sys_username = self.ui_factory.create_label("Username: --")
        self.sys_data_path = self.ui_factory.create_label("Data Path: --")
        self.sys_timestamp = self.ui_factory.create_label("Time: --")
        self.sys_last_updated = self.ui_factory.create_label("Last Updated: --")

        for label in [self.sys_participant_id, self.sys_username, self.sys_data_path, self.sys_timestamp]:
            label.setFont(QFont("Monospace", 10))
            layout.addWidget(label)
            layout.addSpacing(3)

        self.sys_last_updated.setFont(QFont("Monospace", 9))
        self.sys_last_updated.setStyleSheet("color: #666;")
        layout.addWidget(self.sys_last_updated)

        layout.addStretch()

        return box

    def _create_network_box(self) -> QWidget:
        """Create network status box."""
        box, layout = self.ui_factory.create_group_box("Network Status")
        box.setMinimumHeight(150)

        self.net_wifi_status = self.ui_factory.create_label("WiFi: --")
        self.net_ssid = self.ui_factory.create_label("Network: --")
        self.net_ip = self.ui_factory.create_label("IP: --")
        self.net_last_updated = self.ui_factory.create_label("Last Updated: --")

        for label in [self.net_wifi_status, self.net_ssid, self.net_ip]:
            label.setFont(QFont("Monospace", 10))
            layout.addWidget(label)
            layout.addSpacing(3)

        self.net_last_updated.setFont(QFont("Monospace", 9))
        self.net_last_updated.setStyleSheet("color: #666;")
        layout.addWidget(self.net_last_updated)

        layout.addStretch()

        return box

    def _create_time_box(self) -> QWidget:
        """Create time sync status box."""
        box, layout = self.ui_factory.create_group_box("Time Synchronization")
        box.setMinimumHeight(150)

        self.time_sync_status = self.ui_factory.create_label("Sync: --")
        self.time_current = self.ui_factory.create_label("System: --")
        self.time_last_updated = self.ui_factory.create_label("Last Updated: --")

        for label in [self.time_sync_status, self.time_current]:
            label.setFont(QFont("Monospace", 10))
            layout.addWidget(label)
            layout.addSpacing(3)

        self.time_last_updated.setFont(QFont("Monospace", 9))
        self.time_last_updated.setStyleSheet("color: #666;")
        layout.addWidget(self.time_last_updated)

        layout.addStretch()

        return box

    def _create_smart_plug_box(self) -> QWidget:
        """Create smart plug monitoring box."""
        box, layout = self.ui_factory.create_group_box("Smart Plug & Home Assistant")

        content_layout = self.ui_factory.create_horizontal_layout()

        # Left: Connection status
        status_layout = self.ui_factory.create_vertical_layout()
        self.sp_ha_status = self.ui_factory.create_label("HA Connection: --")
        self.sp_verified = self.ui_factory.create_label("Verified: --")
        self.sp_last_updated = self.ui_factory.create_label("Last Updated: --")

        for label in [self.sp_ha_status, self.sp_verified]:
            label.setFont(QFont("Monospace", 9))
            status_layout.addWidget(label)

        self.sp_last_updated.setFont(QFont("Monospace", 8))
        self.sp_last_updated.setStyleSheet("color: #666;")
        status_layout.addWidget(self.sp_last_updated)

        status_layout.addStretch()
        content_layout.addLayout(status_layout, 1)

        # Right: Latest power readings
        power_layout = self.ui_factory.create_vertical_layout()
        power_label = QLabel("<b>Latest TV Power Readings:</b>")
        power_layout.addWidget(power_label)

        self.sp_power_data = QTextEdit()
        self.sp_power_data.setReadOnly(True)
        self.sp_power_data.setMaximumHeight(80)
        self.sp_power_data.setFont(QFont("Monospace", 8))
        self.sp_power_data.setPlaceholderText("No data yet...")
        power_layout.addWidget(self.sp_power_data)

        content_layout.addLayout(power_layout, 2)

        layout.addLayout(content_layout)

        return box

    def _create_camera_box(self) -> QWidget:
        """Create camera status box."""
        box, layout = self.ui_factory.create_group_box("Camera Status")
        box.setMinimumHeight(120)

        self.cam_device = self.ui_factory.create_label("Device: --")
        self.cam_tested = self.ui_factory.create_label("Tested: --")
        self.cam_last_updated = self.ui_factory.create_label("Last Updated: --")

        for label in [self.cam_device, self.cam_tested]:
            label.setFont(QFont("Monospace", 10))
            layout.addWidget(label)
            layout.addSpacing(3)

        self.cam_last_updated.setFont(QFont("Monospace", 9))
        self.cam_last_updated.setStyleSheet("color: #666;")
        layout.addWidget(self.cam_last_updated)

        layout.addStretch()

        return box

    def _create_services_box(self) -> QWidget:
        """Create services monitoring box with status only (no gaze circles)."""
        box, layout = self.ui_factory.create_group_box("FLASH-TV Services Status")
        box.setMinimumHeight(120)

        self.svc_flash_boot = self.ui_factory.create_label("flash-run-on-boot: --")
        self.svc_flash_periodic = self.ui_factory.create_label("flash-periodic: --")
        self.svc_home_assistant = self.ui_factory.create_label("Home Assistant: --")

        for label in [self.svc_flash_boot, self.svc_flash_periodic, self.svc_home_assistant]:
            label.setFont(QFont("Monospace", 10))
            layout.addWidget(label)
            layout.addSpacing(3)

        layout.addStretch()

        return box

    def _create_errors_box(self) -> QWidget:
        """Create recent errors display box."""
        box, layout = self.ui_factory.create_group_box("Recent Unexpected Errors")

        # Header with timestamp
        header_layout = self.ui_factory.create_horizontal_layout()
        self.errors_last_updated = self.ui_factory.create_label("Last Updated: --")
        self.errors_last_updated.setFont(QFont("Monospace", 8))
        self.errors_last_updated.setStyleSheet("color: #666;")
        header_layout.addWidget(self.errors_last_updated)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.errors_output = QTextEdit()
        self.errors_output.setReadOnly(True)
        self.errors_output.setMaximumHeight(80)
        self.errors_output.setFont(QFont("Monospace", 8))
        self.errors_output.setPlaceholderText("No unexpected errors detected")
        layout.addWidget(self.errors_output)

        return box

    def _create_lock_section(self) -> QWidget:
        """Create device lock controls."""
        lock_group, lock_layout = self.ui_factory.create_group_box("Device Locking Instructions")

        lock_info = self.ui_factory.create_label(
            "<b>After verifying all systems are working properly above, manually lock the device:</b>"
        )
        lock_layout.addWidget(lock_info)

        lock_layout.addSpacing(10)

        # Manual lock instructions
        instructions_text = (
            "<b>Manual Device Lock Instructions:</b><br><br>"
            "1. Click the top right power button on screen → Select <b>Lock</b><br><br>"
            "<b>OR</b><br><br>"
            "2. Press <b>Super key</b> → Type \"lock\" → Press <b>Enter</b><br><br>"
            "<b>Important:</b> Lock the device before leaving the participant's location to prevent accidental changes."
        )
        instructions_label = self.ui_factory.create_label(instructions_text)
        instructions_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        lock_layout.addWidget(instructions_label)

        lock_layout.addSpacing(10)

        # Single button to mark as locked
        self.mark_locked_button = self.ui_factory.create_action_button(
            "✅ I Have Locked the Device",
            callback=self._mark_device_locked,
            style=ButtonStyle.SUCCESS,
            height=45,
        )
        lock_layout.addWidget(self.mark_locked_button)

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
            callback=self._on_continue_clicked,
            text="Setup Complete - Device Locked"
        )
        self.continue_button.setEnabled(False)

        return button_layout

    def _update_dashboard(self) -> None:
        """Update all dashboard components with live data."""
        try:
            self._update_system_info()
            self._update_network_status()
            self._update_time_status()
            self._update_smart_plug_status()
            self._update_camera_status()
            self._update_services_status()
            self._update_errors_status()

        except Exception as e:
            self.logger.error(f"Error updating dashboard: {e}")

    def _update_system_info(self) -> None:
        """Update system information display."""
        participant_id = self.state.get_user_input("participant_id", "")
        device_id = self.state.get_user_input("device_id", "")
        username = self.state.get_user_input("username", "")
        data_path = self.state.get_user_input("data_path", "")

        full_id = f"{participant_id}{device_id}" if device_id else participant_id

        self.sys_participant_id.setText(f"Participant: {full_id if full_id else '--'}")
        self.sys_username.setText(f"Username: {username if username else '--'}")
        self.sys_data_path.setText(f"Data: {data_path if data_path else '--'}")
        self.sys_timestamp.setText(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.sys_last_updated.setText(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")

    def _update_network_status(self) -> None:
        """Update network status display."""
        wifi_ssid = self.state.get_user_input("wifi_ssid", "")

        if wifi_ssid and wifi_ssid != "SKIPPED":
            self.net_wifi_status.setText("WiFi: ✅ Connected")
            self.net_ssid.setText(f"Network: {wifi_ssid}")

            # Try to get IP address
            try:
                result = subprocess.run(
                    ["hostname", "-I"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    ip = result.stdout.strip().split()[0]
                    self.net_ip.setText(f"IP: {ip}")
                else:
                    self.net_ip.setText("IP: --")
            except Exception:
                self.net_ip.setText("IP: --")
        else:
            self.net_wifi_status.setText("WiFi: ⚠️ Skipped/Unknown")
            self.net_ssid.setText("Network: --")
            self.net_ip.setText("IP: --")

        self.net_last_updated.setText(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")

    def _update_time_status(self) -> None:
        """Update time sync status display."""
        time_synced = self.state.get_user_input("time_synced", False)

        if time_synced:
            self.time_sync_status.setText("Sync: ✅ Verified")
        else:
            self.time_sync_status.setText("Sync: ⚠️ Not verified")

        self.time_current.setText(f"System: {datetime.now().strftime('%H:%M:%S')}")
        self.time_last_updated.setText(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")

    def _update_smart_plug_status(self) -> None:
        """Update smart plug and Home Assistant status."""
        smart_plug_verified = self.state.get_user_input("smart_plug_verified", False)

        if smart_plug_verified:
            self.sp_verified.setText("Verified: ✅ Yes")
        else:
            self.sp_verified.setText("Verified: ❌ No")

        # Check Home Assistant connection
        try:
            import urllib.request
            response = urllib.request.urlopen("http://localhost:8123", timeout=2)
            if response.getcode() == 200:
                self.sp_ha_status.setText("HA Connection: ✅ Connected")
            else:
                self.sp_ha_status.setText("HA Connection: ⚠️ Unexpected response")
        except Exception:
            self.sp_ha_status.setText("HA Connection: ❌ Not reachable")

        # Get latest power readings from CSV
        participant_id = self.state.get_user_input("participant_id", "")
        device_id = self.state.get_user_input("device_id", "")
        username = self.state.get_user_input("username", "")

        if participant_id and device_id and username:
            full_id = f"{participant_id}{device_id}"
            csv_file = f"/home/{username}/data/{full_id}_data/{full_id}_tv_power_5s.csv"

            if os.path.exists(csv_file):
                try:
                    with open(csv_file, 'r') as f:
                        lines = f.readlines()
                        last_5 = lines[-5:] if len(lines) >= 5 else lines

                    self.sp_power_data.clear()
                    for line in last_5:
                        parts = line.strip().split(';')
                        if len(parts) >= 3:
                            power = parts[0]
                            date = parts[1]
                            time = parts[2]
                            self.sp_power_data.append(f"{date} {time} | {power}W")
                except Exception as e:
                    self.sp_power_data.setPlainText(f"Error reading CSV: {e}")
            else:
                self.sp_power_data.setPlainText("Waiting for power data file...")

        self.sp_last_updated.setText(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")

    def _update_camera_status(self) -> None:
        """Update camera status display."""
        camera_path = self.state.get_user_input("selected_camera", "")
        camera_name = self.state.get_user_input("selected_camera_name", "")
        camera_tested = self.state.get_user_input("camera_tested", False)

        if camera_path:
            self.cam_device.setText(f"Device: {camera_path}")
        else:
            self.cam_device.setText("Device: --")

        self.cam_tested.setText(f"Tested: {'✅ Yes' if camera_tested else '❌ No'}")
        self.cam_last_updated.setText(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")

    def _update_services_status(self) -> None:
        """Update services and gaze monitoring status."""
        # Check systemd services
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "flash-run-on-boot.service"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.stdout.strip() == "active":
                self.svc_flash_boot.setText("flash-run-on-boot: ✅ Running")
            else:
                self.svc_flash_boot.setText("flash-run-on-boot: ❌ Stopped")
        except Exception:
            self.svc_flash_boot.setText("flash-run-on-boot: ⚠️ Unknown")

        try:
            result = subprocess.run(
                ["systemctl", "is-active", "flash-periodic-restart.service"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.stdout.strip() == "active":
                self.svc_flash_periodic.setText("flash-periodic: ✅ Running")
            else:
                self.svc_flash_periodic.setText("flash-periodic: ❌ Stopped")
        except Exception:
            self.svc_flash_periodic.setText("flash-periodic: ⚠️ Unknown")

        # Check Home Assistant Docker
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=homeassistant", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if "Up" in result.stdout:
                self.svc_home_assistant.setText("Home Assistant: ✅ Running")
            else:
                self.svc_home_assistant.setText("Home Assistant: ❌ Stopped")
        except Exception:
            self.svc_home_assistant.setText("Home Assistant: ⚠️ Unknown")


    def _update_errors_status(self) -> None:
        """Update recent errors display."""
        participant_id = self.state.get_user_input("participant_id", "")
        device_id = self.state.get_user_input("device_id", "")
        username = self.state.get_user_input("username", "")

        if not all([participant_id, device_id, username]):
            return

        full_id = f"{participant_id}{device_id}"
        data_path = f"/home/{username}/data/{full_id}_data"
        stderr_log = os.path.join(data_path, f"{full_id}_flash_logstderr.log")

        if os.path.exists(stderr_log):
            try:
                with open(stderr_log, 'r', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last 100 lines and filter for actual errors
                    last_lines = lines[-100:] if len(lines) > 100 else lines

                    errors = []
                    for line in last_lines:
                        line = line.strip()
                        if any(keyword in line for keyword in [
                            "Exception:", "Error:", "CRITICAL:", "ERROR:",
                            "Traceback", "Failed to", "Could not", "Unable to",
                            "Permission denied", "No such file"
                        ]):
                            # Check if it's a known safe error
                            if not self._is_known_safe_error(line):
                                errors.append(line)

                    if errors:
                        self.errors_output.clear()
                        # Show last 5 actual errors
                        for error in errors[-5:]:
                            self.errors_output.append(f'<span style="color: red;">{error}</span>')
                    else:
                        self.errors_output.setPlainText("No unexpected errors detected")

            except Exception as e:
                self.errors_output.setPlainText(f"Error reading log: {e}")
        else:
            self.errors_output.setPlainText("No error log file yet")

        self.errors_last_updated.setText(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")

    def _is_known_safe_error(self, line: str) -> bool:
        """Check if error is a known safe/expected error."""
        known_safe = [
            "Corrupt JPEG data", "DeprecationWarning", "UserWarning",
            "Deprecated in NumPy", "Failed to load image Python extension",
            "Overload resolution failed", "warpAffine", "RTNETLINK answers"
        ]

        for pattern in known_safe:
            if pattern in line:
                return True
        return False

    @handle_step_error
    def _mark_device_locked(self, checked: bool = False) -> None:
        """Mark that the device has been locked."""
        self.logger.info("User confirmed device has been locked")
        self._mark_setup_complete()

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
                "FLASH-TV setup is now complete!\n\n"
                "The system is ready for data collection.\n"
                "Participant can resume normal TV viewing.\n\n"
                "Remember to lock the screen if not already done.",
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
