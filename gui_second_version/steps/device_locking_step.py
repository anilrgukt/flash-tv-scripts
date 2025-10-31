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
        participant_label.setFont(QFont("Arial", 11))
        layout.addWidget(participant_label)

        # Time sync status
        self.time_sync_label = QLabel("<b>Time Sync:</b> --")
        self.time_sync_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.time_sync_label)

        # Network status
        self.network_label = QLabel("<b>Network:</b> --")
        self.network_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.network_label)

        # Camera status
        self.camera_label = QLabel("<b>Camera:</b> --")
        self.camera_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.camera_label)

        # Smart plug status
        self.smart_plug_label = QLabel("<b>Smart Plug:</b> --")
        self.smart_plug_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.smart_plug_label)

        # Last stderr log entry
        self.stderr_log_label = QLabel("<b>Last FLASH Log Line:</b> --")
        self.stderr_log_label.setFont(QFont("Arial", 11))
        self.stderr_log_label.setWordWrap(True)
        layout.addWidget(self.stderr_log_label)

        # RTC times
        self.rtc_times_label = QLabel("<b>RTC Times:</b> --")
        self.rtc_times_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.rtc_times_label)

        return box

    def _create_services_status_section(self) -> QWidget:
        """Create services status section."""
        box = QWidget()
        layout = self.ui_factory.create_vertical_layout(spacing=8)
        box.setLayout(layout)

        services_header = QLabel("<b>FLASH-TV Services:</b>")
        services_header.setFont(QFont("Arial", 11))
        layout.addWidget(services_header)

        self.svc_flash_boot_label = QLabel("  flash-run-on-boot: --")
        self.svc_flash_boot_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.svc_flash_boot_label)

        self.svc_flash_periodic_label = QLabel("  flash-periodic: --")
        self.svc_flash_periodic_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.svc_flash_periodic_label)

        self.svc_home_assistant_label = QLabel("  Home Assistant: --")
        self.svc_home_assistant_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.svc_home_assistant_label)

        return box

    def _create_lock_section(self) -> QWidget:
        """Create device lock controls."""
        lock_group, lock_layout = self.ui_factory.create_group_box("Lock Device")

        lock_info = self.ui_factory.create_label("After verifying all systems are working properly above, lock the device to complete setup.")
        lock_info.setFont(QFont("Arial", 11))
        lock_layout.addWidget(lock_info)

        lock_layout.addSpacing(15)

        # Button to actually lock the device
        self.lock_device_button = self.ui_factory.create_action_button(
            "🔒 Lock the Device Now",
            callback=self._lock_device,
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

            # Update network
            wifi_ssid = self.state.get_user_input("wifi_ssid", "")
            if wifi_ssid and wifi_ssid != "SKIPPED":
                self.network_label.setText(f"<b>Network:</b> ✅ Connected to {wifi_ssid}")
            else:
                self.network_label.setText(f"<b>Network:</b> ⚠️ Not configured")

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

            # Update last stderr log entry
            last_stderr = self._get_last_stderr_entry()
            self.stderr_log_label.setText(f"<b>Last FLASH Log Line:</b> {last_stderr}")

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

    def _get_last_stderr_entry(self) -> str:
        """Get the last stderr log entry."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not all([participant_id, device_id, username]):
                return "No log yet"

            full_id = f"{participant_id}{device_id}"
            stderr_log = f"/home/{username}/data/{full_id}_data/{full_id}_flash_logstderr.log"

            if os.path.exists(stderr_log):
                with open(stderr_log, "r", errors="ignore") as f:
                    lines = f.readlines()
                    if lines:
                        # Get last non-empty line
                        for line in reversed(lines):
                            line = line.strip()
                            if line:
                                # Truncate if too long
                                return line[:100] + "..." if len(line) > 100 else line
            return "No entries yet"
        except Exception as e:
            self.logger.debug(f"Error reading stderr log: {e}")
            return "Error"

    def _get_rtc_times(self) -> str:
        """Get RTC times from both RTCs and system time."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not all([participant_id, device_id, username]):
                return "No data"

            full_id = f"{participant_id}{device_id}"

            # Get system time
            system_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Try to read RTC times
            rtc0_time = "N/A"
            rtc1_time = "N/A"

            try:
                result = subprocess.run(["hwclock", "-r", "-f", "/dev/rtc0"], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    rtc0_time = result.stdout.strip()
            except Exception:
                pass

            try:
                result = subprocess.run(["hwclock", "-r", "-f", "/dev/rtc1"], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    rtc1_time = result.stdout.strip()
            except Exception:
                pass

            return f"System: {system_time} | RTC0: {rtc0_time} | RTC1: {rtc1_time}"
        except Exception as e:
            self.logger.debug(f"Error reading RTC times: {e}")
            return "Error"

    @handle_step_error
    def _lock_device(self, checked: bool = False) -> None:
        """Lock the device screen."""
        try:
            self.logger.info("Attempting to lock device screen")

            # Try multiple lock methods in order of preference
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
                QMessageBox.information(
                    self,
                    "Device Locked",
                    "The device has been locked successfully.\n\nSetup is complete!",
                )
            else:
                self.logger.error("All lock methods failed")
                QMessageBox.warning(
                    self,
                    "Lock Failed",
                    "Could not lock the device automatically.\n\n"
                    "Please lock the device manually:\n"
                    "• Click the power button (top right) → Lock\n"
                    "• Or press Super key → Type 'lock' → Enter",
                )

        except Exception as e:
            self.logger.error(f"Error attempting to lock device: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while trying to lock the device:\n{e}",
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
