"""Time synchronization step implementation with proper RTC integration."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

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
from models import StepStatus
from constants import Messages, Services
from utils.ui_factory import ButtonStyle


class TimeSyncStepCorrected(WizardStep):
    """Step 3: Synchronize System Time with proper RTC integration."""

    def create_content_widget(self) -> QWidget:
        """Create the time synchronization UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections using UI factory
        display_section = self._create_time_display_section()
        rtc_section = self._create_rtc_status_section()
        details_section = self._create_details_section()
        actions_section = self._create_actions_section()

        main_layout.addWidget(display_section)
        main_layout.addWidget(rtc_section)
        main_layout.addWidget(details_section)
        main_layout.addWidget(actions_section)

        # Add stretch to push content up
        main_layout.addStretch()

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
            "Current System Time: Loading...", status_type="info"
        )
        display_layout.addWidget(self.time_label)

        self.sync_status_label = self.ui_factory.create_status_label(
            "Time Synchronization: Checking...", status_type="info"
        )
        display_layout.addWidget(self.sync_status_label)

        return display_group

    def _create_rtc_status_section(self) -> QWidget:
        """Create the RTC status display section using UI factory."""
        rtc_group, rtc_layout = self.ui_factory.create_group_box(
            "Real-Time Clock (RTC) Status"
        )

        self.external_rtc_label = self.ui_factory.create_status_label(
            "External RTC (DS3231): Checking...", status_type="info"
        )
        rtc_layout.addWidget(self.external_rtc_label)

        self.internal_rtc0_label = self.ui_factory.create_status_label(
            "Internal RTC rtc0 (PSEQ_RTC): Checking...", status_type="info"
        )
        rtc_layout.addWidget(self.internal_rtc0_label)

        self.internal_rtc1_label = self.ui_factory.create_status_label(
            "Internal RTC rtc1 (tegra-RTC): Checking...", status_type="info"
        )
        rtc_layout.addWidget(self.internal_rtc1_label)

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

        # Check all RTCs button
        self.check_rtcs_button = self.ui_factory.create_action_button(
            "🔍 Check All RTC Status",
            callback=self._check_all_rtcs,
            style=ButtonStyle.SECONDARY,
            height=35,
        )
        actions_layout.addWidget(self.check_rtcs_button)

        # Sync from external RTC button
        self.sync_external_rtc_button = self.ui_factory.create_action_button(
            "🕐 Sync Time from External RTC",
            callback=self._sync_from_external_rtc,
            style=ButtonStyle.PRIMARY,
            height=35,
        )
        actions_layout.addWidget(self.sync_external_rtc_button)

        # Set external RTC button
        self.set_external_rtc_button = self.ui_factory.create_action_button(
            "💾 Set External RTC from System Time",
            callback=self._set_external_rtc,
            style=ButtonStyle.SECONDARY,
            height=35,
        )
        actions_layout.addWidget(self.set_external_rtc_button)

        # Synchronize NTP time button
        self.sync_ntp_button = self.ui_factory.create_action_button(
            "🌐 Synchronize via NTP (Internet)",
            callback=self._synchronize_ntp_time,
            style=ButtonStyle.PRIMARY,
            height=35,
        )
        actions_layout.addWidget(self.sync_ntp_button)

        # Manual time setting button
        self.manual_time_button = self.ui_factory.create_action_button(
            "📅 Manually Set Time",
            callback=self._set_time_manually,
            style=ButtonStyle.SECONDARY,
            height=35,
        )
        actions_layout.addWidget(self.manual_time_button)

        # Time is correct button
        self.time_correct_button = self.ui_factory.create_action_button(
            "✅ Time is Correct - Continue",
            callback=self._mark_time_correct,
            style=ButtonStyle.SUCCESS,
            height=35,
            enabled=False,
        )
        actions_layout.addWidget(self.time_correct_button)

        return actions_group

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
    def _check_all_rtcs(self, checked: bool = False) -> None:
        """Check all RTC status using the Python script."""
        try:
            self.logger.info("Checking all RTC status")
            self.check_rtcs_button.setEnabled(False)
            self.details_text.clear()
            self.details_text.append("Checking RTC status...\n")

            # Create temporary file for start date (required by the script)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                temp_start_date_path = temp_file.name

            try:
                # Get the python environment path
                if hasattr(self.state, 'username') and self.state.username:
                    python_path = f"/home/{self.state.username}/py38/bin/python"
                else:
                    python_path = "python"

                # Get the script path
                scripts_dir = Path(__file__).parent.parent.parent / "python_scripts"
                rtc_script = scripts_dir / "update_or_check_system_time_from_RTCs.py"

                # Run the RTC check script
                result = self.process_runner.run_command([
                    python_path,
                    str(rtc_script),
                    "check",
                    temp_start_date_path
                ], timeout_ms=30000)

                if result and result.returncode == 0:
                    # Parse and display the output
                    output = result.stdout
                    self.details_text.append("RTC Status Check Results:\n")
                    self.details_text.append(output)
                    
                    # Parse the output to update individual RTC status labels
                    self._parse_rtc_status(output)
                    
                    self.logger.info("RTC status check completed successfully")
                else:
                    error_msg = result.stderr if result else "Command failed"
                    self.details_text.append(f"Error checking RTC status:\n{error_msg}")
                    self.logger.error(f"RTC status check failed: {error_msg}")

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_start_date_path)
                except OSError:
                    pass

        except Exception as e:
            self.logger.error(f"Error checking RTC status: {e}")
            self.details_text.append(f"Error: {str(e)}")
            raise FlashTVError(
                f"Failed to check RTC status: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try checking RTC status manually",
            )
        finally:
            self.check_rtcs_button.setEnabled(True)

    def _parse_rtc_status(self, output: str) -> None:
        """Parse RTC status output and update individual labels."""
        try:
            lines = output.split('\n')
            
            # Look for specific RTC information in the output
            external_rtc_time = None
            internal_rtc0_time = None
            internal_rtc1_time = None
            
            for line in lines:
                line = line.strip()
                if "Time from external RTC (DS3231) is:" in line:
                    external_rtc_time = line.split(":", 1)[1].strip()
                elif "Time from internal RTC rtc0 (PSEQ_RTC, being used) is:" in line:
                    internal_rtc0_time = line.split(":", 1)[1].strip()
                elif "Time from internal RTC rtc1 (tegra-RTC, not being used) is:" in line:
                    internal_rtc1_time = line.split(":", 1)[1].strip()

            # Update labels with status
            if external_rtc_time:
                if "incorrect" in external_rtc_time.lower() or "error" in external_rtc_time.lower():
                    self.external_rtc_label.setText(f"External RTC (DS3231): ❌ {external_rtc_time}")
                    self.external_rtc_label.setStyleSheet(f"color: {self.config.error_color}; padding: 5px;")
                else:
                    self.external_rtc_label.setText(f"External RTC (DS3231): ✅ {external_rtc_time}")
                    self.external_rtc_label.setStyleSheet(f"color: {self.config.success_color}; padding: 5px;")

            if internal_rtc0_time:
                if "none" in internal_rtc0_time.lower() or "error" in internal_rtc0_time.lower():
                    self.internal_rtc0_label.setText(f"Internal RTC rtc0 (PSEQ_RTC): ❌ {internal_rtc0_time}")
                    self.internal_rtc0_label.setStyleSheet(f"color: {self.config.error_color}; padding: 5px;")
                else:
                    self.internal_rtc0_label.setText(f"Internal RTC rtc0 (PSEQ_RTC): ✅ {internal_rtc0_time}")
                    self.internal_rtc0_label.setStyleSheet(f"color: {self.config.success_color}; padding: 5px;")

            if internal_rtc1_time:
                if "none" in internal_rtc1_time.lower() or "error" in internal_rtc1_time.lower():
                    self.internal_rtc1_label.setText(f"Internal RTC rtc1 (tegra-RTC): ❌ {internal_rtc1_time}")
                    self.internal_rtc1_label.setStyleSheet(f"color: {self.config.warning_color}; padding: 5px;")
                else:
                    self.internal_rtc1_label.setText(f"Internal RTC rtc1 (tegra-RTC): ℹ️ {internal_rtc1_time}")
                    self.internal_rtc1_label.setStyleSheet(f"color: {self.config.info_color}; padding: 5px;")

            # Check if we should enable the time correct button
            self._check_time_accuracy()

        except Exception as e:
            self.logger.error(f"Error parsing RTC status: {e}")

    def _check_time_accuracy(self) -> None:
        """Check if system time appears accurate and enable continue button if so."""
        try:
            # Simple check: if any of the RTCs show valid time, enable continue
            external_ok = "✅" in self.external_rtc_label.text()
            internal_rtc0_ok = "✅" in self.internal_rtc0_label.text()
            
            if external_ok or internal_rtc0_ok:
                self.time_correct_button.setEnabled(True)
                self.sync_status_label.setText("Time Status: ✅ RTC time available")
                self.sync_status_label.setStyleSheet(f"color: {self.config.success_color}; font-weight: bold; padding: 5px;")
            else:
                self.time_correct_button.setEnabled(False)
                self.sync_status_label.setText("Time Status: ⚠️ RTC synchronization recommended")
                self.sync_status_label.setStyleSheet(f"color: {self.config.warning_color}; font-weight: bold; padding: 5px;")

        except Exception as e:
            self.logger.error(f"Error checking time accuracy: {e}")

    @handle_step_error
    def _sync_from_external_rtc(self, checked: bool = False) -> None:
        """Sync system time from external RTC."""
        try:
            # Confirm with user
            reply = QMessageBox.question(
                self,
                "Sync from External RTC",
                "This will set the system time from the external RTC (DS3231).\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                self.logger.info("User cancelled external RTC sync")
                return

            self.logger.info("Starting external RTC sync")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.sync_external_rtc_button.setEnabled(False)
            
            # Create temporary file for start date
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                temp_start_date_path = temp_file.name

            try:
                # Get the python environment path
                if hasattr(self.state, 'username') and self.state.username:
                    python_path = f"/home/{self.state.username}/py38/bin/python"
                else:
                    python_path = "python"

                # Get the script path
                scripts_dir = Path(__file__).parent.parent.parent / "python_scripts"
                rtc_script = scripts_dir / "update_or_check_system_time_from_RTCs.py"

                # Run the RTC update script
                result = self.process_runner.run_command([
                    python_path,
                    str(rtc_script),
                    "update",
                    temp_start_date_path
                ], timeout_ms=60000)

                if result and result.returncode == 0:
                    output = result.stdout
                    self.details_text.clear()
                    self.details_text.append("External RTC Sync Results:\n")
                    self.details_text.append(output)
                    
                    # Check if sync was successful
                    if "The system time was set from the external RTC" in output:
                        QMessageBox.information(self, "Success", "System time synchronized from external RTC!")
                        self.update_status(StepStatus.COMPLETED)
                        self._check_all_rtcs()  # Refresh RTC status
                    else:
                        QMessageBox.warning(self, "Warning", "External RTC sync completed but may have fallen back to internal RTC.")
                        self.update_status(StepStatus.USER_ACTION_REQUIRED)
                else:
                    error_msg = result.stderr if result else "Command failed"
                    self.details_text.clear()
                    self.details_text.append(f"External RTC sync failed:\n{error_msg}")
                    QMessageBox.critical(self, "Error", f"Failed to sync from external RTC:\n{error_msg}")
                    self.update_status(StepStatus.FAILED)

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_start_date_path)
                except OSError:
                    pass

        except Exception as e:
            self.logger.error(f"Error during external RTC sync: {e}")
            QMessageBox.critical(self, "Error", f"External RTC sync failed: {str(e)}")
            self.update_status(StepStatus.FAILED)
            raise FlashTVError(
                f"External RTC sync failed: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try checking RTC status or use NTP sync",
            )
        finally:
            self.sync_external_rtc_button.setEnabled(True)

    @handle_step_error
    def _set_external_rtc(self, checked: bool = False) -> None:
        """Set external RTC from current system time."""
        try:
            # Confirm with user
            reply = QMessageBox.question(
                self,
                "Set External RTC",
                "This will set the external RTC (DS3231) to the current system time.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                self.logger.info("User cancelled external RTC setting")
                return

            self.logger.info("Setting external RTC from system time")
            self.set_external_rtc_button.setEnabled(False)
            
            # Create temporary file for start date
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                temp_start_date_path = temp_file.name

            try:
                # Get the python environment path
                if hasattr(self.state, 'username') and self.state.username:
                    python_path = f"/home/{self.state.username}/py38/bin/python"
                else:
                    python_path = "python"

                # Get the script path
                scripts_dir = Path(__file__).parent.parent.parent / "python_scripts"
                rtc_script = scripts_dir / "set_external_RTC_and_save_start_date.py"

                # Run the RTC set script
                result = self.process_runner.run_command([
                    python_path,
                    str(rtc_script),
                    temp_start_date_path
                ], timeout_ms=30000)

                if result and result.returncode == 0:
                    output = result.stdout
                    self.details_text.clear()
                    self.details_text.append("External RTC Set Results:\n")
                    self.details_text.append(output)
                    
                    QMessageBox.information(self, "Success", "External RTC has been set to current system time!")
                    self._check_all_rtcs()  # Refresh RTC status
                else:
                    error_msg = result.stderr if result else "Command failed"
                    self.details_text.clear()
                    self.details_text.append(f"Failed to set external RTC:\n{error_msg}")
                    QMessageBox.critical(self, "Error", f"Failed to set external RTC:\n{error_msg}")

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_start_date_path)
                except OSError:
                    pass

        except Exception as e:
            self.logger.error(f"Error setting external RTC: {e}")
            QMessageBox.critical(self, "Error", f"Setting external RTC failed: {str(e)}")
            raise FlashTVError(
                f"Setting external RTC failed: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Check I2C connection and try again",
            )
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
                self.details_text.setText(result.stdout)
                self._parse_time_status(result.stdout)
            else:
                error_msg = result.stderr if result else "Command failed"
                self.details_text.setText(
                    f"Error checking time status:\n{error_msg}"
                )
                self.logger.error(f"Time status check failed: {error_msg}")

        except Exception as e:
            self.logger.error(f"Error checking time status: {e}")
            self.details_text.setText(f"Error: {str(e)}")
            raise FlashTVError(
                f"Failed to check time status: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try checking time status manually",
            )

    def _parse_time_status(self, status_output: str) -> None:
        """Parse timedatectl status output and update UI."""
        try:
            # Parse for sync status
            if "synchronized: yes" in status_output.lower():
                self.sync_status_label.setText("Time Synchronization: ✅ Synchronized")
                self.sync_status_label.setStyleSheet(
                    f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
                )
                self.time_correct_button.setEnabled(True)
                self.logger.info("System time is synchronized")
            else:
                self.sync_status_label.setText("Time Synchronization: ❌ Not Synchronized")
                self.sync_status_label.setStyleSheet(
                    f"color: {self.config.error_color}; font-weight: bold; padding: 5px;"
                )
                self.logger.warning("System time is not synchronized")

            # Check NTP service
            if "ntp service: active" in status_output.lower():
                self.details_text.append("\n✅ NTP service is active")
                self.logger.debug("NTP service is active")
            else:
                self.details_text.append("\n⚠️ NTP service is not active")
                self.logger.debug("NTP service is inactive")

        except Exception as e:
            self.logger.error(f"Error parsing time status: {e}")

    @handle_step_error
    def _synchronize_ntp_time(self, checked: bool = False) -> None:
        """Synchronize system time using NTP with comprehensive error handling."""
        try:
            # Confirm with user
            reply = QMessageBox.question(
                self,
                "Synchronize Time",
                "This will enable NTP time synchronization (requires internet connection).\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                self.logger.info("User cancelled NTP time synchronization")
                return

            self.logger.info("Starting NTP time synchronization process")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.sync_ntp_button.setEnabled(False)

            # Enable NTP
            result1, error1 = self.process_runner.run_sudo_command(
                ["timedatectl", "set-ntp", "1"], "enable time synchronization"
            )

            if error1:
                self.logger.error(f"Failed to enable NTP: {error1}")
                QMessageBox.critical(
                    self, "Error", f"Failed to enable NTP: {error1}"
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
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to restart service: {error2}",
                )

            # Wait for synchronization
            import time
            time.sleep(2)

            # Recheck status
            self._check_time_status()

            # Persist state
            if self.state_manager:
                self.state_manager.save_state(self.state)

            if self.time_correct_button.isEnabled():
                self.update_status(StepStatus.COMPLETED)
                self.logger.info("NTP time synchronization completed successfully")
                QMessageBox.information(self, "Success", "Time synchronization successful!")
            else:
                self.update_status(StepStatus.USER_ACTION_REQUIRED)
                self.logger.warning("NTP time synchronization enabled but still pending")
                QMessageBox.warning(
                    self,
                    "Sync Pending",
                    "NTP is enabled but synchronization may take a moment.\nPlease check status again in a few seconds.",
                )

        except Exception as e:
            self.logger.error(f"Error during NTP time synchronization: {e}")
            QMessageBox.critical(
                self, "Error", f"Time sync failed: {str(e)}"
            )
            self.update_status(StepStatus.FAILED)
            raise FlashTVError(
                f"NTP time synchronization failed: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try manually setting the time or check network connection",
            )
        finally:
            self.sync_ntp_button.setEnabled(True)

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
                        self, "Error", f"Failed to set time: {error}"
                    )
                    raise FlashTVError(
                        f"Failed to set time manually: {error}",
                        ErrorType.PROCESS_ERROR,
                        recovery_action="Check system permissions or try RTC sync",
                    )
                else:
                    # Disable NTP if it was enabled
                    self.process_runner.run_sudo_command(
                        ["timedatectl", "set-ntp", "0"], "disable automatic time sync"
                    )

                    # Update status and UI
                    self._check_time_status()
                    self.time_correct_button.setEnabled(True)

                    # Persist state
                    if self.state_manager:
                        self.state_manager.save_state(self.state)

                    self.update_status(StepStatus.COMPLETED)
                    self.logger.info("Manual time setting completed successfully")
                    QMessageBox.information(
                        self, "Success", "Time set successfully!"
                    )
            else:
                self.logger.info("User cancelled manual time setting")

        except Exception as e:
            self.logger.error(f"Error during manual time setting: {e}")
            raise FlashTVError(
                f"Manual time setting failed: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try using NTP synchronization or RTC sync instead",
            )

    @handle_step_error
    def _mark_time_correct(self, checked: bool = False) -> None:
        """Mark time as correct and continue with validation."""
        try:
            if self.is_completed() or self.time_correct_button.isEnabled():
                self.logger.info("User confirmed time is correct")

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.update_status(StepStatus.COMPLETED)
                self.request_next_step.emit()
            else:
                self.logger.warning("Time correct button clicked but not enabled")
                QMessageBox.warning(
                    self,
                    "Time Not Synchronized",
                    "Please synchronize the system time before continuing.",
                )

        except Exception as e:
            self.logger.error(f"Error marking time as correct: {e}")
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

        # Check current time status and RTC status
        self._check_time_status()
        self._check_all_rtcs()

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