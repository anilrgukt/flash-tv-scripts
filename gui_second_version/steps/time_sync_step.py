"""Time synchronization step implementation using new framework patterns with RTC integration."""

from __future__ import annotations

import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QMessageBox,
    QDialog,
    QDateTimeEdit,
    QDialogButtonBox,
)
from PyQt6.QtCore import QTimer, QDateTime

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus, ProcessStatus
from constants import Messages, Services
from utils.ui_factory import ButtonStyle


class TimeSyncStep(WizardStep):
    """Step 3: Synchronize System Time with RTC integration using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the time synchronization UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections using UI factory
        display_section = self._create_time_display_section()
        rtc_section = self._create_rtc_section()
        details_section = self._create_details_section()
        actions_section = self._create_actions_section()

        main_layout.addWidget(display_section)
        main_layout.addWidget(rtc_section)
        main_layout.addWidget(details_section)
        main_layout.addWidget(actions_section)

        # Continue button using UI factory
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        # Setup timer for time display updates
        self.time_update_timer = QTimer()
        self.time_update_timer.timeout.connect(self._safe_update_time_display)
        self.time_update_timer.start(1000)  # Update every second

        return content

    def _create_time_display_section(self) -> QWidget:
        """Create the system time display section using UI factory."""
        display_group, display_layout = self.ui_factory.create_group_box(
            "System Time Information"
        )

        self.time_label = self.ui_factory.create_status_label(
            Messages.CURRENT_SYSTEM_TIME, status_type="info"
        )
        display_layout.addWidget(self.time_label)

        self.sync_status_label = self.ui_factory.create_status_label(
            "🔍 Checking time synchronization status...", status_type="info"
        )
        display_layout.addWidget(self.sync_status_label)

        return display_group

    def _create_rtc_section(self) -> QWidget:
        """Create the RTC information and control section using UI factory."""
        rtc_group, rtc_layout = self.ui_factory.create_group_box(
            "Real-Time Clock (RTC) Information"
        )

        # Add instructions for proper workflow
        instructions_label = self.ui_factory.create_label(
            "⚠️ IMPORTANT: Follow these steps in order:\n"
            "1. First, click 'Set External RTC to System Time' to initialize the RTC\n"
            "2. Then click 'Check All RTC Status' to verify\n"
            "3. Finally, sync time from External RTC if needed"
        )
        instructions_label.setStyleSheet("color: #d32f2f; font-weight: bold; padding: 10px; background-color: #ffebee; border-radius: 4px;")
        rtc_layout.addWidget(instructions_label)
        
        # External RTC (DS3231) status
        self.external_rtc_label = self.ui_factory.create_status_label(
            "📡 External RTC (DS3231): Not checked yet", status_type="info"
        )
        rtc_layout.addWidget(self.external_rtc_label)

        # Internal RTC status
        self.internal_rtc_label = self.ui_factory.create_status_label(
            "💻 Internal RTC: Not checked yet", status_type="info"
        )
        rtc_layout.addWidget(self.internal_rtc_label)

        # RTC buttons - ordered by workflow
        rtc_button_layout = self.ui_factory.create_horizontal_layout()

        # Set RTC button first (step 1)
        self.set_external_rtc_button = self.ui_factory.create_action_button(
            "1️⃣ Set External RTC to System Time",
            callback=self._set_external_rtc,
            style=ButtonStyle.PRIMARY,
            height=35,
        )
        rtc_button_layout.addWidget(self.set_external_rtc_button)

        # Check RTC status button (step 2)
        self.check_rtc_button = self.ui_factory.create_action_button(
            "2️⃣ Check All RTC Status",
            callback=self._check_rtc_status,
            style=ButtonStyle.SECONDARY,
            height=35,
        )
        rtc_button_layout.addWidget(self.check_rtc_button)

        # Sync from RTC button (step 3)
        self.sync_from_external_rtc_button = self.ui_factory.create_action_button(
            "3️⃣ Sync from External RTC",
            callback=self._sync_from_external_rtc,
            style=ButtonStyle.SUCCESS,
            height=35,
            enabled=False,
        )
        rtc_button_layout.addWidget(self.sync_from_external_rtc_button)

        rtc_layout.addLayout(rtc_button_layout)

        return rtc_group

    def _create_details_section(self) -> QWidget:
        """Create the time configuration details section using UI factory."""
        details_group, details_layout = self.ui_factory.create_group_box(
            "Time Configuration Details"
        )

        self.details_text = self.ui_factory.create_text_area(
            placeholder="Time synchronization details will appear here...",
            max_height=150,
            read_only=True,
        )
        details_layout.addWidget(self.details_text)

        return details_group

    def _create_actions_section(self) -> QWidget:
        """Create the time synchronization actions section using UI factory."""
        actions_group, actions_layout = self.ui_factory.create_group_box(
            "Time Synchronization Actions"
        )

        # Synchronize time button (NTP)
        self.sync_button = self.ui_factory.create_action_button(
            "🌐 Synchronize with Network Time (NTP)",
            callback=self._synchronize_time,
            style=ButtonStyle.PRIMARY,
            height=35,
        )
        actions_layout.addWidget(self.sync_button)

        # Manual time setting button
        self.manual_time_button = self.ui_factory.create_action_button(
            "📅 Manually Set Time",
            callback=self._set_time_manually,
            style=ButtonStyle.SECONDARY,
            height=35,
        )
        actions_layout.addWidget(self.manual_time_button)

        return actions_group

    def _create_continue_section(self):
        """Create the continue button section using UI factory."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text="Continue to Gallery Setup"
        )

        return button_layout

    def _safe_update_time_display(self) -> None:
        """Safely update the current time display with error handling."""
        try:
            self._update_time_display()
        except Exception as e:
            self.logger.error(f"Error updating time display: {e}")

    def _update_time_display(self) -> None:
        """Update the current time display."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
        self.time_label.setText(f"Current System Time: {current_time}")

    @handle_step_error
    def _check_rtc_status(self, checked: bool = False) -> None:
        """Check both external and internal RTC status with error handling."""
        try:
            self.logger.info("Checking RTC status")
            username = self.state.get_user_input("username", "")
            
            if not username:
                self.logger.error("Username not available for RTC check")
                self.details_text.append("❌ Username not available for RTC operations")
                return
            
            # Check external RTC using the Python script
            self.details_text.append("📡 Checking External RTC (DS3231) status...")
            
            python_path = f"/home/{username}/py38/bin/python"
            # Get the script path relative to user's home directory
            rtc_check_script = os.path.expanduser("~/flash-tv-scripts/python_scripts/update_or_check_system_time_from_RTCs.py")
            
            # Get the data path for start_date.txt
            data_path = self.state.get_user_input("data_path", "")
            if not data_path:
                # If no data path, use a temporary placeholder
                start_date_file = "/tmp/start_date.txt"
            else:
                start_date_file = os.path.join(data_path, "start_date.txt")
            
            result = self.process_runner.run_command(
                ["sudo", python_path, rtc_check_script, "check", start_date_file], timeout_ms=15000
            )
            
            if result and result.returncode == 0:
                self.external_rtc_label.setText("📡 External RTC (DS3231): ✅ Available")
                self.external_rtc_label.setStyleSheet(f"color: {self.config.success_color}; font-weight: bold; padding: 5px;")
                self.sync_from_external_rtc_button.setEnabled(True)
                
                # Parse output for time information
                if result.stdout:
                    self.details_text.append(f"External RTC Status:\n{result.stdout}")
                    
                self.logger.info("External RTC is available")
            else:
                error_msg = result.stderr if result else "RTC check failed"
                self.external_rtc_label.setText("📡 External RTC (DS3231): ❌ Not Available")
                self.external_rtc_label.setStyleSheet(f"color: {self.config.error_color}; font-weight: bold; padding: 5px;")
                self.details_text.append(f"External RTC Error: {error_msg}")
                self.logger.warning(f"External RTC not available: {error_msg}")
            
            # Check internal RTC
            self.details_text.append("💻 Checking Internal RTC status...")
            hwclock_result = self.process_runner.run_command(
                ["hwclock", "--show"], timeout_ms=5000
            )
            
            if hwclock_result and hwclock_result.returncode == 0:
                self.internal_rtc_label.setText("💻 Internal RTC: ✅ Available")
                self.internal_rtc_label.setStyleSheet(f"color: {self.config.success_color}; font-weight: bold; padding: 5px;")
                if hwclock_result.stdout:
                    self.details_text.append(f"Internal RTC Time: {hwclock_result.stdout.strip()}")
                self.logger.info("Internal RTC is available")
            else:
                error_msg = hwclock_result.stderr if hwclock_result else "hwclock failed"
                self.internal_rtc_label.setText("💻 Internal RTC: ❌ Not Available")
                self.internal_rtc_label.setStyleSheet(f"color: {self.config.error_color}; font-weight: bold; padding: 5px;")
                self.details_text.append(f"Internal RTC Error: {error_msg}")
                self.logger.warning(f"Internal RTC not available: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"Error checking RTC status: {e}")
            self.details_text.append(f"Error checking RTC status: {str(e)}")
            raise FlashTVError(
                f"Failed to check RTC status: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Check RTC hardware connections",
            )

    @handle_step_error
    def _sync_from_external_rtc(self, checked: bool = False) -> None:
        """Sync system time from external RTC with comprehensive error handling."""
        try:
            username = self.state.get_user_input("username", "")
            if not username:
                raise FlashTVError("Username not available", ErrorType.STATE_ERROR)
            
            reply = QMessageBox.question(
                self,
                "Sync from External RTC",
                "This will set the system time from the External RTC (DS3231). Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                self.logger.info("User cancelled RTC sync")
                return
            
            self.logger.info("Syncing system time from external RTC")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.sync_from_external_rtc_button.setEnabled(False)
            
            # Run the RTC sync script
            python_path = f"/home/{username}/py38/bin/python"
            # Get the script path relative to user's home directory
            rtc_sync_script = os.path.expanduser("~/flash-tv-scripts/python_scripts/update_or_check_system_time_from_RTCs.py")
            
            # Get the data path for start_date.txt
            data_path = self.state.get_user_input("data_path", "")
            if not data_path:
                self.logger.error("Data path not available for RTC sync")
                self.update_status(StepStatus.FAILED)
                raise FlashTVError(
                    "Data path not available for RTC sync",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first",
                )
            
            start_date_file = os.path.join(data_path, "start_date.txt")
            
            # Use run_sudo_command for immediate execution
            result, error = self.process_runner.run_sudo_command(
                [python_path, rtc_sync_script, "update", start_date_file],
                "sync system time from external RTC"
            )
            
            if error:
                self.logger.error(f"Failed to sync from RTC: {error}")
                self.details_text.append(f"❌ Failed to sync from RTC: {error}")
                self.update_status(StepStatus.FAILED)
                raise FlashTVError(
                    f"Failed to sync from external RTC: {error}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check script permissions and RTC hardware",
                )
            else:
                self.details_text.append("✅ System time synced from external RTC!")
                self.logger.info("RTC sync completed successfully")
                
                # Check time status and show verification
                self._check_time_status()
                self._verify_time_manually()
                self.update_status(StepStatus.USER_ACTION_REQUIRED)
                
        except Exception as e:
            self.logger.error(f"Error during RTC sync: {e}")
            self.update_status(StepStatus.FAILED)
            raise
        finally:
            self.sync_from_external_rtc_button.setEnabled(True)

    @handle_step_error
    def _set_external_rtc(self, checked: bool = False) -> None:
        """Set external RTC to current system time with comprehensive error handling."""
        try:
            username = self.state.get_user_input("username", "")
            if not username:
                raise FlashTVError("Username not available", ErrorType.STATE_ERROR)
            
            reply = QMessageBox.question(
                self,
                "Set External RTC",
                "This will set the External RTC (DS3231) to the current system time. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                self.logger.info("User cancelled RTC setting")
                return
            
            self.logger.info("Setting external RTC to system time")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.set_external_rtc_button.setEnabled(False)
            
            # Run the RTC set script with start_date.txt path
            python_path = f"/home/{username}/py38/bin/python"
            # Get the script path relative to user's home directory
            rtc_set_script = os.path.expanduser("~/flash-tv-scripts/python_scripts/set_external_RTC_and_save_start_date.py")
            
            # Get the data path for start_date.txt
            data_path = self.state.get_user_input("data_path", "")
            if not data_path:
                self.logger.error("Data path not available")
                raise FlashTVError(
                    "Data path not available for RTC setup",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first",
                )
            
            start_date_file = os.path.join(data_path, "start_date.txt")
            
            # Use run_sudo_command for immediate execution instead of run_script
            # This avoids the process being terminated prematurely
            result, error = self.process_runner.run_sudo_command(
                [python_path, rtc_set_script, start_date_file],
                "set external RTC to system time"
            )
            
            if error:
                self.logger.error(f"Failed to set RTC: {error}")
                self.details_text.append(f"❌ Failed to set external RTC: {error}")
                self.update_status(StepStatus.FAILED)
                raise FlashTVError(
                    f"Failed to set external RTC: {error}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check script permissions and RTC hardware",
                )
            else:
                self.details_text.append("✅ External RTC has been set to system time!")
                self.logger.info("RTC set script completed successfully")
                
                # Disable NTP after setting RTC
                self.details_text.append("📡 Disabling NTP to preserve RTC time...")
                ntp_result, ntp_error = self.process_runner.run_sudo_command(
                    ["timedatectl", "set-ntp", "0"], "disable NTP for RTC usage"
                )
                if ntp_error:
                    self.logger.warning(f"Failed to disable NTP: {ntp_error}")
                    self.details_text.append(f"⚠️ Warning: Could not disable NTP: {ntp_error}")
                else:
                    self.details_text.append("✅ NTP disabled - system will use RTC time")
                
                # Now check RTC status to verify it was set
                self._check_rtc_status()
                self.update_status(StepStatus.USER_ACTION_REQUIRED)
                
        except Exception as e:
            self.logger.error(f"Error during RTC set: {e}")
            self.update_status(StepStatus.FAILED)
            raise
        finally:
            self.set_external_rtc_button.setEnabled(True)

    @handle_step_error
    def _check_time_status(self) -> None:
        """Check system time synchronization status with error handling."""
        try:
            self.logger.info("Checking system time synchronization status")

            result = self.process_runner.run_command(
                ["timedatectl", "status"], timeout_ms=10000
            )

            if result and result.returncode == 0:
                self.details_text.append("System Time Status:")
                self.details_text.append(result.stdout)
                self._parse_time_status(result.stdout)
            else:
                error_msg = result.stderr if result else "Command failed"
                self.details_text.append(f"Error checking time status: {error_msg}")
                self.logger.error(f"Time status check failed: {error_msg}")

        except Exception as e:
            self.logger.error(f"Error checking time status: {e}")
            self.details_text.append(f"Error: {str(e)}")
            raise FlashTVError(
                f"Failed to check time status: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try checking time status manually",
            )

    def _verify_time_manually(self) -> None:
        """Show dialog for manual time verification."""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            reply = QMessageBox.information(
                self,
                "Verify Time",
                f"System time has been synced from RTC.\n\n"
                f"Current system time: {current_time}\n\n"
                f"Please verify this matches the actual time.\n"
                f"If incorrect, use 'Manually Set Time' to correct it.",
                QMessageBox.StandardButton.Ok
            )
            
            self.details_text.append(f"\n✅ Time verification completed at {current_time}")
            self._enable_continue()
            
        except Exception as e:
            self.logger.error(f"Error during time verification: {e}")
    
    def _parse_time_status(self, status_output: str) -> None:
        """Parse timedatectl status output and update UI."""
        try:
            # Parse for sync status
            if "synchronized: yes" in status_output.lower():
                self.sync_status_label.setText("✅ System time is synchronized")
                self.sync_status_label.setStyleSheet(
                    f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
                )
                self._enable_continue()
                self.logger.info("System time is synchronized")
            else:
                self.sync_status_label.setText("⚠️ System time is not synchronized")
                self.sync_status_label.setStyleSheet(
                    f"color: {self.config.error_color}; font-weight: bold; padding: 5px;"
                )
                self.logger.warning("System time is not synchronized")

            # Check NTP service
            if "ntp service: active" in status_output.lower():
                self.details_text.append("✅ NTP service is active")
                self.logger.debug("NTP service is active")
            else:
                self.details_text.append("⚠️ NTP service is inactive")
                self.logger.debug("NTP service is inactive")

        except Exception as e:
            self.logger.error(f"Error parsing time status: {e}")

    def _enable_continue(self) -> None:
        """Enable continue button and mark step as completed."""
        self.continue_button.setEnabled(True)
        self.update_status(StepStatus.COMPLETED)
        # Save time sync completion
        self.state.set_user_input("time_synced", True)
        if self.state_manager:
            self.state_manager.save_state(self.state)

    @handle_step_error
    def _synchronize_time(self, checked: bool = False) -> None:
        """Synchronize system time using NTP with comprehensive error handling."""
        try:
            # Confirm with user
            reply = QMessageBox.question(
                self,
                "Synchronize Time",
                "This will enable automatic time synchronization using NTP. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                self.logger.info("User cancelled time synchronization")
                return

            self.logger.info("Starting time synchronization process")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.sync_button.setEnabled(False)

            # Enable NTP
            result1, error1 = self.process_runner.run_sudo_command(
                ["timedatectl", "set-ntp", "1"], "enable time synchronization"
            )

            if error1:
                self.logger.error(f"Failed to enable NTP: {error1}")
                QMessageBox.critical(
                    self, "Error", f"Failed to enable NTP synchronization: {error1}"
                )
                self.update_status(StepStatus.FAILED)
                return

            # Restart time sync service
            result2, error2 = self.process_runner.run_sudo_command(
                ["systemctl", "restart", Services.SYSTEMD_TIMESYNCD],
                "restart time sync service",
            )

            if error2:
                self.logger.warning(f"Failed to restart time sync service: {error2}")

            # Wait for synchronization
            import time
            time.sleep(3)

            # Recheck status
            self._check_time_status()

            # Persist state
            if self.state_manager:
                self.state_manager.save_state(self.state)

            if self.continue_button.isEnabled():
                self.logger.info("Time synchronization completed successfully")
                QMessageBox.information(self, "Success", "Time synchronization completed successfully!")
            else:
                self.update_status(StepStatus.USER_ACTION_REQUIRED)
                self.logger.warning("Time synchronization enabled but still pending")
                QMessageBox.warning(
                    self,
                    "Synchronization Pending",
                    "NTP synchronization has been enabled but may take a few moments to complete.",
                )

        except Exception as e:
            self.logger.error(f"Error during time synchronization: {e}")
            QMessageBox.critical(
                self, "Error", f"Time synchronization failed: {str(e)}"
            )
            self.update_status(StepStatus.FAILED)
            raise FlashTVError(
                f"Time synchronization failed: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try manually setting the time or check NTP service",
            )
        finally:
            self.sync_button.setEnabled(True)

    @handle_step_error
    def _set_time_manually(self, checked: bool = False) -> None:
        """Manually set the system time with comprehensive error handling."""
        try:
            self.logger.info("Opening manual time setting dialog")

            dialog = QDialog(self)
            dialog.setWindowTitle("Set System Time Manually")
            dialog.resize(400, 200)

            # Use UI factory for dialog layout
            layout = self.ui_factory.create_vertical_layout()
            dialog.setLayout(layout)

            layout.addWidget(
                self.ui_factory.create_label("Set the correct date and time:")
            )

            datetime_edit = QDateTimeEdit()
            datetime_edit.setDateTime(QDateTime.currentDateTime())
            datetime_edit.setCalendarPopup(True)
            datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            layout.addWidget(datetime_edit)

            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_datetime = datetime_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
                self.logger.info(f"User selected time: {new_datetime}")

                # Set the time
                result, error = self.process_runner.run_sudo_command(
                    ["date", "-s", new_datetime], "set system time manually"
                )

                if error:
                    self.logger.error(f"Failed to set time manually: {error}")
                    QMessageBox.critical(
                        self, "Error", f"Failed to set system time: {error}"
                    )
                    raise FlashTVError(
                        f"Failed to set time manually: {error}",
                        ErrorType.PROCESS_ERROR,
                        recovery_action="Check system permissions or try NTP sync",
                    )
                else:
                    # Disable NTP if it was enabled
                    self.process_runner.run_sudo_command(
                        ["timedatectl", "set-ntp", "0"], "disable automatic time sync"
                    )

                    # Update status and UI
                    self._check_time_status()
                    self._enable_continue()

                    self.logger.info("Manual time setting completed successfully")
                    QMessageBox.information(
                        self, "Success", "System time has been set successfully!"
                    )
            else:
                self.logger.info("User cancelled manual time setting")

        except Exception as e:
            self.logger.error(f"Error during manual time setting: {e}")
            raise FlashTVError(
                f"Manual time setting failed: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try using NTP synchronization instead",
            )

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            if self.is_completed() and self.continue_button.isEnabled():
                self.logger.info("Time synchronization step completed, proceeding to gallery setup")

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but time not synchronized")
                QMessageBox.warning(
                    self,
                    "Time Not Synchronized",
                    "Please synchronize the system time before continuing.",
                )

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete time synchronization step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Check time synchronization and try again",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the time sync step with enhanced logic."""
        super().activate_step()

        self.logger.info("Time synchronization step activated")

        # Check if already completed
        if self.state.get_user_input("time_synced", False):
            self.logger.info("Time synchronization already completed")
            self.sync_status_label.setText("✅ Time synchronization already completed")
            self.sync_status_label.setStyleSheet(f"color: {self.config.success_color}; font-weight: bold; padding: 5px;")
            self._enable_continue()
            return

        # Only check current time status, do NOT automatically check RTC
        self._check_time_status()
        
        # Show instruction to user
        self.details_text.append("\n📌 Please follow the RTC setup workflow:")
        self.details_text.append("1. Click 'Set External RTC to System Time' first")
        self.details_text.append("2. Click 'Check All RTC Status' to verify")
        self.details_text.append("3. Click 'Sync from External RTC' if needed")

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()
        # No longer monitoring RTC processes since we use synchronous run_sudo_command

    def cleanup(self) -> None:
        """Clean up resources when step is destroyed."""
        try:
            self.logger.info("Cleaning up time synchronization step")

            # Stop time update timer
            if hasattr(self, "time_update_timer") and self.time_update_timer.isActive():
                self.time_update_timer.stop()

            # Call parent cleanup
            super().cleanup()

        except Exception as e:
            self.logger.error(f"Error during time sync step cleanup: {e}")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Time synchronization step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")