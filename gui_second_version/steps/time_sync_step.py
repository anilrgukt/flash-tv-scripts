"""Time synchronization step implementation using new framework patterns."""

from __future__ import annotations

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
from models import StepStatus
from constants import Messages, Services
from utils.ui_factory import ButtonStyle


class TimeSyncStep(WizardStep):
    """Step 3: Synchronize System Time using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the time synchronization UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections using UI factory
        display_section = self._create_time_display_section()
        details_section = self._create_details_section()
        actions_section = self._create_actions_section()

        main_layout.addWidget(display_section)
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
            Messages.CURRENT_SYSTEM_TIME, status_type="info"
        )
        display_layout.addWidget(self.time_label)

        self.sync_status_label = self.ui_factory.create_status_label(
            Messages.TIME_SYNCHRONIZATION_CHECKING, status_type="info"
        )
        display_layout.addWidget(self.sync_status_label)

        return display_group

    def _create_details_section(self) -> QWidget:
        """Create the time configuration details section using UI factory."""
        details_group, details_layout = self.ui_factory.create_group_box(
            "Time Configuration Details"
        )

        self.details_text = self.ui_factory.create_text_area(
            placeholder="Time synchronization details will appear here...",
            max_height=120,
            read_only=True,
        )
        details_layout.addWidget(self.details_text)

        return details_group

    def _create_actions_section(self) -> QWidget:
        """Create the time synchronization actions section using UI factory."""
        actions_group, actions_layout = self.ui_factory.create_group_box(
            "Time Synchronization Actions"
        )

        # Synchronize time button
        self.sync_button = self.ui_factory.create_action_button(
            "🔄 Synchronize System Time",
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

        # Time is correct button
        self.time_correct_button = self.ui_factory.create_action_button(
            "Time is Correct - Continue",
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
                    Messages.ERROR_CHECKING_TIME_STATUS.format(error=error_msg)
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
                self.sync_status_label.setText(Messages.TIME_SYNCHRONIZED)
                self.sync_status_label.setStyleSheet(
                    f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
                )
                self.time_correct_button.setEnabled(True)
                self.logger.info("System time is synchronized")
            else:
                self.sync_status_label.setText(Messages.TIME_NOT_SYNCHRONIZED)
                self.sync_status_label.setStyleSheet(
                    f"color: {self.config.error_color}; font-weight: bold; padding: 5px;"
                )
                self.logger.warning("System time is not synchronized")

            # Check NTP service
            if "ntp service: active" in status_output.lower():
                self.details_text.append(Messages.NTP_SERVICE_ACTIVE)
                self.logger.debug("NTP service is active")
            else:
                self.details_text.append(Messages.NTP_SERVICE_INACTIVE)
                self.logger.debug("NTP service is inactive")

        except Exception as e:
            self.logger.error(f"Error parsing time status: {e}")

    @handle_step_error
    def _synchronize_time(self, checked: bool = False) -> None:
        """Synchronize system time using NTP with comprehensive error handling."""
        try:
            # Confirm with user
            reply = QMessageBox.question(
                self,
                Messages.SYNCHRONIZE_TIME,
                Messages.ENABLE_NTP_CONFIRMATION,
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
                    self, "Error", Messages.FAILED_TO_ENABLE_NTP.format(error=error1)
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
                    Messages.FAILED_TO_RESTART_SERVICE.format(error=error2),
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
                self.logger.info("Time synchronization completed successfully")
                QMessageBox.information(self, "Success", Messages.TIME_SYNC_SUCCESSFUL)
            else:
                self.update_status(StepStatus.USER_ACTION_REQUIRED)
                self.logger.warning("Time synchronization enabled but still pending")
                QMessageBox.warning(
                    self,
                    Messages.SYNC_PENDING,
                    Messages.NTP_ENABLED_PENDING,
                )

        except Exception as e:
            self.logger.error(f"Error during time synchronization: {e}")
            QMessageBox.critical(
                self, "Error", Messages.TIME_SYNC_FAILED.format(error=str(e))
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
            dialog.setWindowTitle(Messages.SET_SYSTEM_TIME_MANUALLY)
            dialog.resize(400, 200)

            # Use UI factory for dialog layout
            layout = self.ui_factory.create_vertical_layout()
            dialog.setLayout(layout)

            layout.addWidget(
                self.ui_factory.create_label(Messages.SET_CORRECT_DATE_TIME)
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
                        self, "Error", Messages.FAILED_TO_SET_TIME.format(error=error)
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
                    self.time_correct_button.setEnabled(True)

                    # Persist state
                    if self.state_manager:
                        self.state_manager.save_state(self.state)

                    self.update_status(StepStatus.COMPLETED)
                    self.logger.info("Manual time setting completed successfully")
                    QMessageBox.information(
                        self, "Success", Messages.TIME_SET_SUCCESSFULLY
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

        # Check current time status
        self._check_time_status()

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
