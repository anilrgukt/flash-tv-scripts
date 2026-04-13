"""Time synchronization step implementation using new framework patterns with RTC integration."""

from __future__ import annotations

import os
from datetime import datetime

from config.messages import MESSAGES, get_python_path
from config.participant_contract import build_participant_full_id
from core import WizardStep
from core.exceptions import ErrorType, FlashTVError, handle_step_error
from models import StepStatus
from models.state_keys import UserInputKey
from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QDateTimeEdit, QDialog, QDialogButtonBox, QWidget
from utils.ui_factory import ButtonStyle


class TimeSyncStep(WizardStep):
    """Step 3: Synchronize System Time with RTC integration using new framework patterns."""

    NTP_POLL_INTERVAL_MS = 2000
    NTP_POLL_MAX_ATTEMPTS = 15

    def create_content_widget(self) -> QWidget:
        """Create the time synchronization UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections using UI factory
        display_section = self._create_time_display_section()
        actions_section = self._create_actions_section()  # ALL buttons in correct order
        details_section = self._create_details_section()

        main_layout.addWidget(display_section)
        main_layout.addWidget(actions_section)
        main_layout.addWidget(details_section)

        # Continue button using UI factory
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        # Setup timer for time display updates - use base class create_timer for automatic cleanup
        self.time_update_timer = self.create_timer(1000, self._safe_update_time_display)
        self.ntp_poll_timer = self.create_timer(
            self.NTP_POLL_INTERVAL_MS, self._poll_ntp_status, start=False
        )
        self.workflow_delay_timer = self.create_timer(
            1000, self._run_scheduled_workflow_callback, start=False
        )
        self._current_time_source = "unknown"
        self._ntp_poll_attempts = 0
        self._scheduled_workflow_callback = None
        self._rtc_persistence_verified = False

        return content

    def _create_time_display_section(self) -> QWidget:
        """Create the system time display section using UI factory."""
        display_group, display_layout = self.ui_factory.create_group_box(
            "System Time Information"
        )

        self.time_label = self.ui_factory.create_status_label(
            MESSAGES.Time.CURRENT_SYSTEM_TIME, status_type="info"
        )
        display_layout.addWidget(self.time_label)

        self.sync_status_label = self.ui_factory.create_status_label(
            "🔍 Checking time synchronization status...", status_type="info"
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
            min_height=200,
            read_only=True,
        )
        details_layout.addWidget(self.details_text)

        return details_group

    def _create_actions_section(self) -> QWidget:
        actions_container = QWidget()
        actions_container_layout = self.ui_factory.create_vertical_layout()
        actions_container.setLayout(actions_container_layout)

        # Add RTC status labels at the top (always visible)
        rtc_status_group, rtc_status_layout = self.ui_factory.create_group_box(
            "RTC Hardware Status"
        )

        self.external_rtc_label = self.ui_factory.create_status_label(
            "📡 External RTC (DS3231): Not checked yet", status_type="info"
        )
        rtc_status_layout.addWidget(self.external_rtc_label)

        self.internal_rtc_label = self.ui_factory.create_status_label(
            "💻 Internal RTC: Not checked yet", status_type="info"
        )
        rtc_status_layout.addWidget(self.internal_rtc_label)

        actions_container_layout.addWidget(rtc_status_group)

        workflow_group, workflow_layout = self.ui_factory.create_group_box(
            "Time Sync Workflow Status"
        )
        self.workflow_status_label = self.ui_factory.create_status_label(
            "Ready to configure time", status_type="info"
        )
        workflow_layout.addWidget(self.workflow_status_label)

        self.workflow_steps_label = self.ui_factory.create_label(
            "Automatic sync will start if WiFi is available."
        )
        workflow_layout.addWidget(self.workflow_steps_label)

        self.workflow_hint_label = self.ui_factory.create_label(
            "If internet time is unavailable, set the time manually and the RTC will be configured automatically."
        )
        workflow_layout.addWidget(self.workflow_hint_label)
        actions_container_layout.addWidget(workflow_group)

        manual_group, manual_group_layout = self.ui_factory.create_group_box(
            "Time Synchronization Controls"
        )

        # Row 1: Manual time and NTP buttons
        time_buttons_layout = self.ui_factory.create_horizontal_layout(spacing=10)

        # 1a. Manual time setting button (PRIMARY - RECOMMENDED)
        self.manual_time_button = self.ui_factory.create_action_button(
            "📅 Manually Set Time",
            callback=self._set_time_manually,
            style=ButtonStyle.PRIMARY,
            height=45,
        )
        time_buttons_layout.addWidget(self.manual_time_button)

        # 1b. NTP Synchronize time button (SECONDARY - ALTERNATIVE)
        self.sync_button = self.ui_factory.create_action_button(
            "🌐 Sync with Network Time (NTP)",
            callback=self._synchronize_time,
            style=ButtonStyle.SECONDARY,
            height=35,
        )
        time_buttons_layout.addWidget(self.sync_button)

        manual_group_layout.addLayout(time_buttons_layout)

        # Add spacing for RTC operations
        manual_group_layout.addSpacing(15)

        # RTC operations label
        rtc_label = self.ui_factory.create_label(
            "RTC Operations (after setting system time):"
        )
        rtc_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        manual_group_layout.addWidget(rtc_label)

        # Row 2: RTC operation buttons
        rtc_buttons_layout = self.ui_factory.create_horizontal_layout(spacing=10)

        # Set RTC button
        self.set_external_rtc_button = self.ui_factory.create_action_button(
            "Set External RTC",
            callback=self._set_external_rtc,
            style=ButtonStyle.SECONDARY,
            height=35,
        )
        rtc_buttons_layout.addWidget(self.set_external_rtc_button)

        # Check RTC status button
        self.check_rtc_button = self.ui_factory.create_action_button(
            "Check RTC Status",
            callback=self._check_rtc_status,
            style=ButtonStyle.SECONDARY,
            height=35,
        )
        rtc_buttons_layout.addWidget(self.check_rtc_button)

        # Sync from RTC button
        self.sync_from_external_rtc_button = self.ui_factory.create_action_button(
            "Sync from External RTC",
            callback=self._sync_from_external_rtc,
            style=ButtonStyle.SECONDARY,
            height=35,
            enabled=False,
        )
        rtc_buttons_layout.addWidget(self.sync_from_external_rtc_button)

        manual_group_layout.addLayout(rtc_buttons_layout)
        actions_container_layout.addWidget(manual_group)

        return actions_container

    def _show_auto_workflow_view(self) -> None:
        self.workflow_status_label.setText("⏳ Automatic time sync in progress...")
        self.workflow_status_label.setStyleSheet(
            f"color: {self.config.info_color}; font-weight: bold; padding: 5px;"
        )
        self._set_manual_controls_enabled(False)

    def _show_manual_controls_view(self) -> None:
        self._set_manual_controls_enabled(True)

    def _set_manual_controls_enabled(self, enabled: bool) -> None:
        for button in (
            self.manual_time_button,
            self.sync_button,
            self.set_external_rtc_button,
            self.check_rtc_button,
            self.sync_from_external_rtc_button,
        ):
            if button is self.sync_from_external_rtc_button and not enabled:
                button.setEnabled(False)
            elif button is self.sync_from_external_rtc_button and enabled:
                continue
            else:
                button.setEnabled(enabled)

    def _update_workflow_step(self, step: int, total: int, message: str) -> None:
        """Update the workflow progress display."""
        self.workflow_steps_label.setText(f"Step {step}/{total}: {message}")
        self.workflow_hint_label.setText(message)

    def _schedule_workflow_callback(self, delay_ms: int, callback) -> None:
        self._scheduled_workflow_callback = callback
        self.workflow_delay_timer.stop()
        self.workflow_delay_timer.setInterval(delay_ms)
        self.workflow_delay_timer.start()

    def _run_scheduled_workflow_callback(self) -> None:
        self.workflow_delay_timer.stop()
        callback = self._scheduled_workflow_callback
        self._scheduled_workflow_callback = None
        if callback is not None:
            callback()

    def _command_succeeded(self, result, error) -> bool:
        return bool(result) and result.returncode == 0 and not error

    def _create_continue_section(self):
        """Create the continue button section using UI factory."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text=MESSAGES.UI.CONTINUE
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
    def _check_rtc_status(self, checked: bool = False) -> bool:
        """Check both external and internal RTC status with error handling."""
        try:
            self.logger.info("Checking RTC status")
            username = self.state.get_user_input(UserInputKey.USERNAME, "")
            external_rtc_available = False

            if not username:
                self.logger.error("Username not available for RTC check")
                self.details_text.append(
                    "❌ The setup account is missing, so the RTC cannot be checked."
                )
                self.details_text.append(
                    "📌 Go back to Participant Setup, confirm the device account details, then try again."
                )
                self.details_text.append(
                    "📌 If the account details already look correct, ask the study technician for help."
                )
                return False

            # Set sudo password from state for RTC operations
            if not self.process_runner.set_sudo_password_from_state():
                self.logger.error("Sudo password not available for RTC operations")
                self.details_text.append(
                    "❌ The sudo password is missing, so the RTC cannot be checked."
                )
                self.details_text.append(
                    "📌 Go back to Participant Setup, re-enter the password, and try again."
                )
                self.details_text.append(
                    "📌 If the password is not accepted there either, ask the study technician for help."
                )
                return False

            # Check external RTC using the Python script
            self.details_text.append("📡 Checking External RTC (DS3231) status...")

            python_path = get_python_path(username)
            # Get the script path using username from state
            rtc_check_script = f"/home/{username}/flash-tv-scripts/python_scripts/update_or_check_system_time_from_RTCs.py"

            # Get the data path for start_date.txt
            data_path = self.state.get_user_input(UserInputKey.DATA_PATH, "")
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            combined_id = build_participant_full_id(participant_id, device_id)

            if not data_path:
                # If no data path, use a temporary placeholder
                start_date_file = f"/tmp/{combined_id}_start_date.txt"
            else:
                start_date_file = os.path.join(
                    data_path, f"{combined_id}_start_date.txt"
                )

            result, error = self.process_runner.run_sudo_command(
                [python_path, rtc_check_script, "check", start_date_file],
                "Check external RTC status",
                timeout_ms=15000,
            )

            if result and result.returncode == 0:
                external_rtc_available = True
                self.external_rtc_label.setText(
                    "📡 External RTC (DS3231): ✅ Available"
                )
                self.external_rtc_label.setStyleSheet(
                    f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
                )
                self.sync_from_external_rtc_button.setEnabled(True)

                # Parse output for time information
                if result.stdout:
                    self.details_text.append(f"External RTC Status:\n{result.stdout}")

                self.logger.info("External RTC is available")
            else:
                error_msg = result.stderr if result else "RTC check failed"
                self.external_rtc_label.setText(
                    "📡 External RTC (DS3231): ❌ Not Available"
                )
                self.external_rtc_label.setStyleSheet(
                    f"color: {self.config.error_color}; font-weight: bold; padding: 5px;"
                )
                self.details_text.append(f"External RTC Error: {error_msg}")
                self.details_text.append(
                    "📌 Try the RTC action again after checking the cable or RTC hardware connection."
                )
                self.details_text.append(
                    "📌 If the RTC still is not detected, stop here and ask technical support for help."
                )
                self.sync_from_external_rtc_button.setEnabled(False)
                self.logger.warning(f"External RTC not available: {error_msg}")

            # Check internal RTC (needs sudo)
            self.details_text.append("💻 Checking Internal RTC status...")
            hwclock_result, error = self.process_runner.run_sudo_command(
                ["hwclock", "--show"], "Check internal RTC status", timeout_ms=5000
            )

            if hwclock_result and hwclock_result.returncode == 0:
                self.internal_rtc_label.setText("💻 Internal RTC: ✅ Available")
                self.internal_rtc_label.setStyleSheet(
                    f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
                )
                if hwclock_result.stdout:
                    self.details_text.append(
                        f"Internal RTC Time: {hwclock_result.stdout.strip()}"
                    )
                self.logger.info("Internal RTC is available")
            else:
                error_msg = (
                    hwclock_result.stderr if hwclock_result else "hwclock failed"
                )
                self.internal_rtc_label.setText("💻 Internal RTC: ❌ Not Available")
                self.internal_rtc_label.setStyleSheet(
                    f"color: {self.config.error_color}; font-weight: bold; padding: 5px;"
                )
                self.details_text.append(f"Internal RTC Error: {error_msg}")
                self.logger.warning(f"Internal RTC not available: {error_msg}")

            return external_rtc_available

        except Exception as e:
            self.logger.error(f"Error checking RTC status: {e}")
            self.details_text.append(
                "❌ The RTC could not be checked because of an unexpected problem."
            )
            self.details_text.append(
                "📌 Try the RTC action again once. If it still fails, ask technical support for help."
            )
            raise FlashTVError(
                f"Failed to check RTC status: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try the RTC action again after checking the RTC connection. If it still fails, ask technical support for help.",
            )

    def _set_ready_to_continue_state(
        self, system_message: str, rtc_message: str
    ) -> None:
        self._rtc_persistence_verified = True
        self.sync_status_label.setText(system_message)
        self.sync_status_label.setStyleSheet(
            f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
        )
        self.workflow_status_label.setText(f"✅ {rtc_message}")
        self.workflow_status_label.setStyleSheet(
            f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
        )
        self.workflow_steps_label.setText("Ready to continue")
        self.workflow_hint_label.setText(
            "System time is valid, the external RTC check succeeded, and you can continue."
        )
        self.details_text.append(f"✅ {system_message}")
        self.details_text.append(f"✅ {rtc_message}")
        self.details_text.append("✅ Ready to continue to the next step.")
        self._enable_continue()

    def _block_until_rtc_is_fixed(self, error_message: str) -> None:
        self._rtc_persistence_verified = False
        self.continue_button.setEnabled(False)
        self.state.set_user_input(UserInputKey.TIME_SYNCED, False)
        self.sync_status_label.setText(
            "⚠️ System time is set, but RTC persistence is not confirmed"
        )
        self.sync_status_label.setStyleSheet(
            f"color: {self.config.warning_color}; font-weight: bold; padding: 5px;"
        )
        self.workflow_status_label.setText(
            "❌ External RTC save/check is still required"
        )
        self.workflow_status_label.setStyleSheet(
            f"color: {self.config.error_color}; font-weight: bold; padding: 5px;"
        )
        self.workflow_steps_label.setText(
            "Do not continue until the RTC issue is resolved"
        )
        self.workflow_hint_label.setText(
            "Retry the RTC action. If it still fails after checking the RTC connection, ask technical support for help."
        )
        self.details_text.append(f"❌ {error_message}")
        self.details_text.append(
            "📌 Continue is locked because the external RTC was not saved and verified successfully."
        )
        self.details_text.append(
            "📌 Retry the RTC step. If the error persists, check RTC hardware/connections or escalate to technical support."
        )
        self.update_status(StepStatus.USER_ACTION_REQUIRED)

    @handle_step_error
    def _sync_from_external_rtc(self, checked: bool = False) -> None:
        """Sync system time from external RTC with comprehensive error handling."""
        try:
            username = self.state.get_user_input(UserInputKey.USERNAME, "")
            if not username:
                raise FlashTVError("Username not available", ErrorType.VALIDATION_ERROR)

            # Set sudo password from state for RTC operations
            if not self.process_runner.set_sudo_password_from_state():
                self.logger.error("Sudo password not available for RTC operations")
                raise FlashTVError(
                    "Sudo password required for RTC operations",
                    ErrorType.VALIDATION_ERROR,
                )

            self.logger.info("Syncing system time from external RTC")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.sync_from_external_rtc_button.setEnabled(False)

            # Run the RTC sync script
            python_path = get_python_path(username)
            # Get the script path relative to user's home directory
            rtc_sync_script = f"/home/{username}/flash-tv-scripts/python_scripts/update_or_check_system_time_from_RTCs.py"

            # Get the data path for start_date.txt
            data_path = self.state.get_user_input(UserInputKey.DATA_PATH, "")
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            combined_id = build_participant_full_id(participant_id, device_id)

            if not data_path:
                self.logger.error("Data path not available for RTC sync")
                self.update_status(StepStatus.FAILED)
                raise FlashTVError(
                    "Data path not available for RTC sync",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first",
                )

            # Ensure the data directory exists before accessing the start_date file
            os.makedirs(data_path, exist_ok=True)

            start_date_file = os.path.join(data_path, f"{combined_id}_start_date.txt")

            # Use run_sudo_command for immediate execution
            result, error = self.process_runner.run_sudo_command(
                [python_path, rtc_sync_script, "update", start_date_file],
                "sync system time from external RTC",
            )

            if not self._command_succeeded(result, error):
                self.logger.error(f"Failed to sync from RTC: {error}")
                self.details_text.append(
                    "❌ The system time could not be restored from the external RTC."
                )
                self.details_text.append(
                    "📌 Try 'Sync from External RTC' again. If it still fails, check the RTC connection."
                )
                self.details_text.append(
                    "📌 If the RTC should be available but still does not work, ask technical support for help."
                )
                self.update_status(StepStatus.FAILED)
                raise FlashTVError(
                    f"Failed to sync from external RTC: {error}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try syncing from the external RTC again. If it still fails after checking the RTC connection, ask technical support for help.",
                )
            else:
                self.details_text.append("✅ System time synced from external RTC!")
                self.logger.info("RTC sync completed successfully")
                self._set_time_source("rtc")
                rtc_verified = self._check_rtc_status()
                if rtc_verified:
                    self._set_ready_to_continue_state(
                        "System time was restored from the external RTC.",
                        "External RTC check succeeded.",
                    )
                else:
                    self._block_until_rtc_is_fixed(
                        "System time was restored, but the external RTC check failed afterward."
                    )

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
            username = self.state.get_user_input(UserInputKey.USERNAME, "")
            if not username:
                raise FlashTVError("Username not available", ErrorType.VALIDATION_ERROR)

            # Set sudo password from state for RTC operations
            if not self.process_runner.set_sudo_password_from_state():
                self.logger.error("Sudo password not available for RTC operations")
                raise FlashTVError(
                    "Sudo password required for RTC operations",
                    ErrorType.VALIDATION_ERROR,
                )

            self.logger.info("Setting external RTC to system time")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.set_external_rtc_button.setEnabled(False)

            # Run the RTC set script with start_date.txt path
            python_path = get_python_path(username)
            # Get the script path relative to user's home directory
            rtc_set_script = f"/home/{username}/flash-tv-scripts/python_scripts/set_external_RTC_and_save_start_date.py"

            # Get the data path for start_date.txt
            data_path = self.state.get_user_input(UserInputKey.DATA_PATH, "")
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            combined_id = build_participant_full_id(participant_id, device_id)

            if not data_path:
                self.logger.error("Data path not available")
                raise FlashTVError(
                    "Data path not available for RTC setup",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first",
                )

            # Ensure the data directory exists before writing the start_date file
            os.makedirs(data_path, exist_ok=True)

            start_date_file = os.path.join(data_path, f"{combined_id}_start_date.txt")

            # Use run_sudo_command for immediate execution instead of run_script
            # This avoids the process being terminated prematurely
            result, error = self.process_runner.run_sudo_command(
                [python_path, rtc_set_script, start_date_file],
                "set external RTC to system time",
            )

            if not self._command_succeeded(result, error):
                self.logger.error(f"Failed to set RTC: {error}")
                self.details_text.append(
                    "❌ The external RTC could not be saved with the current time."
                )
                self.details_text.append(
                    "📌 Try the RTC save again. If it still fails, check the RTC connection."
                )
                self.details_text.append(
                    "📌 If the RTC should be available but still does not save, ask technical support for help."
                )
                self.update_status(StepStatus.FAILED)
                raise FlashTVError(
                    f"Failed to set external RTC: {error}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try saving the time to the external RTC again. If it still fails after checking the RTC connection, ask technical support for help.",
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
                    self.details_text.append(
                        f"⚠️ Warning: Could not disable NTP: {ntp_error}"
                    )
                else:
                    self.details_text.append(
                        "✅ NTP disabled - system will use RTC time"
                    )

                # Now check RTC status to verify it was set
                if self._current_time_source == "unknown":
                    self._set_time_source("rtc")
                rtc_verified = self._check_rtc_status()
                if rtc_verified:
                    system_message = {
                        "manual": "System time was set manually.",
                        "ntp": "System time was synchronized from network time.",
                        "rtc": "System time was set and preserved for RTC use.",
                    }.get(self._current_time_source, "System time is valid.")
                    self._set_ready_to_continue_state(
                        system_message,
                        "External RTC was written and verified successfully.",
                    )
                else:
                    self._block_until_rtc_is_fixed(
                        "The system time looks valid, but the external RTC write/check did not succeed."
                    )

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
                self.details_text.append(
                    "❌ The current time could not be checked automatically."
                )
                self.details_text.append(
                    "📌 Try the check again once. If it still fails, use manual time setup or ask technical support for help."
                )
                self.logger.error(f"Time status check failed: {error_msg}")

        except Exception as e:
            self.logger.error(f"Error checking time status: {e}")
            self.details_text.append(
                "❌ The current time could not be checked because of an unexpected problem."
            )
            self.details_text.append(
                "📌 Try again once. If it still fails, use manual time setup or ask technical support for help."
            )
            raise FlashTVError(
                f"Failed to check time status: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try the time check again. If it still fails, use manual time setup or ask technical support for help.",
            )

    def _parse_time_status(self, status_output: str) -> None:
        """Parse timedatectl status output and update UI."""
        try:
            lower_output = status_output.lower()
            synchronized = "synchronized: yes" in lower_output
            ntp_active = "ntp service: active" in lower_output

            if synchronized:
                self._set_time_source("ntp")
                self.workflow_status_label.setText(
                    "⏳ System time is valid. Saving/checking the external RTC is still required."
                )
                self.workflow_status_label.setStyleSheet(
                    f"color: {self.config.warning_color}; font-weight: bold; padding: 5px;"
                )
                self.workflow_steps_label.setText(
                    "System time is valid, but this step is not complete until the RTC succeeds."
                )
                self.workflow_hint_label.setText(
                    "The wizard will now try to save the valid system time to the external RTC."
                )
                self.logger.info("System time is synchronized via NTP")
            elif self._current_time_source == "rtc":
                self.sync_status_label.setText("✅ Time configured from external RTC")
                self.sync_status_label.setStyleSheet(
                    f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
                )
                self.logger.info("System time is configured from RTC")
            elif self._current_time_source == "manual":
                self.sync_status_label.setText("✅ Time set manually and saved to RTC")
                self.sync_status_label.setStyleSheet(
                    f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
                )
                self.logger.info("System time is configured manually")
            else:
                self.sync_status_label.setText(
                    "⚠️ System time still needs to be configured"
                )
                self.sync_status_label.setStyleSheet(
                    f"color: {self.config.warning_color}; font-weight: bold; padding: 5px;"
                )
                self.logger.warning("System time is not yet configured")

            if "ntp service: active" in status_output.lower():
                self.details_text.append("✅ NTP service is active")
                self.logger.debug("NTP service is active")
            else:
                self.details_text.append("⚠️ NTP service is inactive")
                self.logger.debug("NTP service is inactive")

            if (
                not synchronized
                and ntp_active
                and self._current_time_source == "unknown"
            ):
                self.details_text.append(
                    "⏳ NTP is active but synchronization is still pending."
                )

        except Exception as e:
            self.logger.error(f"Error parsing time status: {e}")

    def _set_time_source(self, source: str) -> None:
        self._current_time_source = source
        source_messages = {
            "ntp": "✅ Time synchronized from network time",
            "rtc": "✅ Time configured from external RTC",
            "manual": "✅ Time set manually and saved to RTC",
            "unknown": "🔍 Checking time synchronization status...",
        }
        status_type = "success" if source != "unknown" else "info"
        self.sync_status_label.setText(
            source_messages.get(source, source_messages["unknown"])
        )
        self.sync_status_label.setStyleSheet(
            self.ui_factory.create_status_label(
                "tmp", status_type=status_type
            ).styleSheet()
        )

    def _is_system_time_reasonable(self) -> bool:
        now = datetime.now()
        return 2024 <= now.year <= datetime.now().year + 1

    def _begin_ntp_polling(self) -> None:
        self._ntp_poll_attempts = 0
        self.ntp_poll_timer.start()

    def _poll_ntp_status(self) -> None:
        self._ntp_poll_attempts += 1
        self._update_workflow_step(
            3,
            4,
            f"Waiting for network time sync ({self._ntp_poll_attempts}/{self.NTP_POLL_MAX_ATTEMPTS})...",
        )

        result = self.process_runner.run_command(
            ["timedatectl", "status"], timeout_ms=5000
        )
        if (
            result
            and result.returncode == 0
            and "synchronized: yes" in result.stdout.lower()
        ):
            self.ntp_poll_timer.stop()
            self.details_text.append("✅ Network time synchronization confirmed")
            self._set_time_source("ntp")
            self._schedule_workflow_callback(500, self._automatic_set_rtc)
            return

        if self._ntp_poll_attempts >= self.NTP_POLL_MAX_ATTEMPTS:
            self.ntp_poll_timer.stop()
            self.details_text.append(
                "⚠️ WiFi is connected, but internet time did not finish in time."
            )
            self._handle_automatic_workflow_failure(
                "WiFi is connected but time servers are unreachable or still pending."
            )
            return

    def _check_wifi_connected(self) -> bool:
        """Check if WiFi is currently connected."""
        try:
            # Check if any WiFi interface is connected
            result = self.process_runner.run_command(
                ["nmcli", "-t", "-f", "TYPE,STATE", "connection", "show", "--active"],
                timeout_ms=5000,
            )

            if result and result.returncode == 0:
                # Look for active wireless connections
                for line in result.stdout.strip().split("\n"):
                    if "802-11-wireless" in line and "activated" in line:
                        self.logger.info("WiFi connection detected")
                        return True

            self.logger.info("No active WiFi connection found")
            return False

        except Exception as e:
            self.logger.warning(f"Error checking WiFi status: {e}")
            return False

    def _automatic_ntp_workflow(self) -> None:
        """Automatically sync time with NTP and configure RTC."""
        try:
            self.logger.info("Starting automatic NTP workflow")
            self.update_status(StepStatus.AUTOMATION_RUNNING)

            # Switch to auto-workflow view (hides manual buttons)
            self._show_auto_workflow_view()

            # Step 1: Enable NTP
            self._update_workflow_step(1, 4, "Enabling NTP synchronization...")
            self.details_text.append("⏰ Step 1/4: Enabling NTP synchronization...")
            result1, error1 = self.process_runner.run_sudo_command(
                ["timedatectl", "set-ntp", "1"], "enable NTP"
            )

            if error1:
                self._handle_automatic_workflow_failure(
                    f"Failed to enable NTP: {error1}"
                )
                return

            self.details_text.append("✅ NTP enabled")

            # Step 2: Restart time sync service
            self._update_workflow_step(2, 4, "Restarting time sync service...")
            self.details_text.append(
                "⏰ Step 2/4: Restarting time synchronization service..."
            )
            result2, error2 = self.process_runner.run_sudo_command(
                ["systemctl", "restart", MESSAGES.Services.SYSTEMD_TIMESYNCD],
                "restart time sync",
            )

            if error2:
                self.logger.warning(f"Time sync service restart warning: {error2}")

            self.details_text.append("✅ Time sync service restarted")
            self.details_text.append(
                "⏰ Waiting for network time to finish synchronizing..."
            )
            self._schedule_workflow_callback(
                self.NTP_POLL_INTERVAL_MS, self._begin_ntp_polling
            )

        except Exception as e:
            self._handle_automatic_workflow_failure(f"Automatic workflow error: {e}")

    def _automatic_set_rtc(self) -> None:
        """Automatically set the external RTC to system time."""
        try:
            username = self.state.get_user_input(UserInputKey.USERNAME, "")
            if not username:
                raise FlashTVError("Username not available", ErrorType.VALIDATION_ERROR)

            # Set sudo password from state
            if not self.process_runner.set_sudo_password_from_state():
                raise FlashTVError("Sudo password required", ErrorType.VALIDATION_ERROR)

            # Get paths
            python_path = get_python_path(username)
            rtc_set_script = f"/home/{username}/flash-tv-scripts/python_scripts/set_external_RTC_and_save_start_date.py"

            data_path = self.state.get_user_input(UserInputKey.DATA_PATH, "")
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            combined_id = build_participant_full_id(participant_id, device_id)

            if not data_path:
                raise FlashTVError(
                    "Data path not available", ErrorType.VALIDATION_ERROR
                )

            # Ensure data directory exists
            os.makedirs(data_path, exist_ok=True)
            start_date_file = os.path.join(data_path, f"{combined_id}_start_date.txt")

            # Set external RTC
            result, error = self.process_runner.run_sudo_command(
                [python_path, rtc_set_script, start_date_file],
                "set external RTC automatically",
            )

            if not self._command_succeeded(result, error):
                self.details_text.append(
                    f"⚠️ Warning: Could not set external RTC: {error}"
                )
                self.logger.warning(f"RTC setup failed: {error}")
                self._handle_automatic_workflow_failure(
                    f"Could not configure external RTC: {error or result.stderr}"
                )
                return
            else:
                self.details_text.append("✅ External RTC configured successfully")

                # Disable NTP to preserve RTC time
                ntp_result, ntp_error = self.process_runner.run_sudo_command(
                    ["timedatectl", "set-ntp", "0"], "disable NTP"
                )
                if not ntp_error:
                    self.details_text.append(
                        "✅ NTP disabled - system will use RTC time"
                    )
                self._set_time_source("rtc")

            # Check RTC status
            self.details_text.append("🔍 Checking RTC status...")
            self._schedule_workflow_callback(1000, self._complete_automatic_workflow)

        except Exception as e:
            self._handle_automatic_workflow_failure(f"RTC setup error: {e}")

    def _complete_automatic_workflow(self) -> None:
        """Complete the automatic workflow and show results."""
        try:
            # Check RTC status
            rtc_verified = self._check_rtc_status()
            if rtc_verified:
                self._set_ready_to_continue_state(
                    "System time was synchronized from network time.",
                    "External RTC was written and checked successfully.",
                )
            else:
                self._block_until_rtc_is_fixed(
                    "Automatic time setup finished, but the external RTC check did not succeed."
                )
            self._show_manual_controls_view()

        except Exception as e:
            self.logger.error(f"Error completing workflow: {e}")
            self.update_status(StepStatus.USER_ACTION_REQUIRED)
            self._show_manual_controls_view()

    def _handle_automatic_workflow_failure(self, error_message: str) -> None:
        """Handle failure in automatic workflow."""
        self.logger.error(f"Automatic workflow failed: {error_message}")

        # Update workflow status to show failure
        self.workflow_status_label.setText("❌ Automatic Time Sync Failed")
        self.workflow_status_label.setStyleSheet("""
            font-weight: bold;
            padding: 15px;
            background-color: #ffebee;
            border: 2px solid #f44336;
            border-radius: 8px;
        """)
        self.workflow_steps_label.setText("Please use manual controls below")
        self.workflow_hint_label.setText(
            "Try the manual time or RTC controls below. If the step still will not finish after one retry, ask technical support for help."
        )

        self.details_text.append("\n❌ Automatic time setup could not finish.")
        self.details_text.append(
            "📌 What to try next: use the manual time button or retry the RTC action below."
        )
        self.details_text.append(
            "📌 When to ask for help: if the clock still will not set correctly or the RTC still fails after one retry, ask technical support."
        )

        self.update_status(StepStatus.USER_ACTION_REQUIRED)

        # Switch to manual controls view
        self._show_manual_controls_view()

    def _enable_continue(self) -> None:
        """Enable continue button and mark step as completed."""
        if not self._rtc_persistence_verified:
            self.logger.warning(
                "Attempted to complete time sync step before RTC persistence was verified"
            )
            self.continue_button.setEnabled(False)
            self.update_status(StepStatus.USER_ACTION_REQUIRED)
            return

        self.continue_button.setEnabled(True)
        self.update_status(StepStatus.COMPLETED)
        # Save time sync completion
        self.state.set_user_input(UserInputKey.TIME_SYNCED, True)
        if self.state_manager:
            self.state_manager.save_state(self.state)

    @handle_step_error
    def _synchronize_time(self, checked: bool = False) -> None:
        """Synchronize system time using NTP with comprehensive error handling."""
        try:
            self.logger.info("Starting time synchronization process")
            if not self.process_runner.set_sudo_password_from_state():
                self.logger.error(
                    "Sudo password not available for time sync operations"
                )
                raise FlashTVError(
                    "Sudo password required for time sync operations",
                    ErrorType.VALIDATION_ERROR,
                )

            self._automatic_ntp_workflow()

        except Exception as e:
            self.logger.error(f"Error during time synchronization: {e}")
            self.update_status(StepStatus.FAILED)
            raise FlashTVError(
                f"Time synchronization failed: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try manually setting the time or check NTP service",
            )

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

                # Set sudo password from state for manual time operations
                if not self.process_runner.set_sudo_password_from_state():
                    self.logger.error(
                        "Sudo password not available for manual time setting"
                    )
                    raise FlashTVError(
                        "Sudo password required for manual time setting",
                        ErrorType.VALIDATION_ERROR,
                    )

                # CRITICAL FIX: Disable NTP FIRST before setting time manually
                self.details_text.append(
                    "📡 Disabling NTP before manual time setting..."
                )
                ntp_result, ntp_error = self.process_runner.run_sudo_command(
                    ["timedatectl", "set-ntp", "0"],
                    "disable NTP before manual time setting",
                )

                if ntp_error:
                    self.logger.warning(f"Warning: Could not disable NTP: {ntp_error}")
                    self.details_text.append(
                        f"⚠️ Warning: Could not disable NTP: {ntp_error}"
                    )
                    # Continue anyway as it might still work
                else:
                    self.details_text.append(
                        "✅ NTP disabled - ready for manual time setting"
                    )

                # Now set the time
                self.details_text.append(f"⏰ Setting system time to: {new_datetime}")
                result, error = self.process_runner.run_sudo_command(
                    ["date", "-s", new_datetime], "set system time manually"
                )

                if error:
                    self.logger.error(f"Failed to set time manually: {error}")
                    raise FlashTVError(
                        f"Failed to set time manually: {error}",
                        ErrorType.PROCESS_ERROR,
                        recovery_action="Check system permissions or try NTP sync",
                    )
                else:
                    self.details_text.append("✅ System time set successfully!")

                    # Update status and UI
                    self._check_time_status()

                    self.logger.info("Manual time setting completed successfully")
                    self.details_text.append(
                        "✅ Manual time setting completed successfully!"
                    )
                    self._set_time_source("manual")

                    # Automatically configure RTC after manual time set
                    self.details_text.append(
                        "\n⏰ Automatically configuring external RTC..."
                    )
                    self._schedule_workflow_callback(1000, self._automatic_set_rtc)
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
                self.logger.info(
                    "Time synchronization step completed, proceeding to gallery setup"
                )

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but time not synchronized")
                self.details_text.append(
                    "⚠️ Please configure the system time before continuing."
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
        """Activate the time sync step with automatic workflow."""
        super().activate_step()

        self.logger.info("Time synchronization step activated")
        self._current_time_source = "unknown"
        self._rtc_persistence_verified = False
        self.continue_button.setEnabled(False)

        # Check if already completed in state
        if (
            self.state.get_user_input(UserInputKey.TIME_SYNCED, False)
            and self._is_system_time_reasonable()
        ):
            self.logger.info("Time synchronization already completed")
            self.sync_status_label.setText(
                "✅ Previously configured time still looks valid"
            )
            self.sync_status_label.setStyleSheet(
                f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
            )
            self.details_text.append("✅ Previously configured time still looks valid.")
            self.workflow_status_label.setText(
                "✅ External RTC save/check already completed earlier."
            )
            self.workflow_status_label.setStyleSheet(
                f"color: {self.config.success_color}; font-weight: bold; padding: 5px;"
            )
            self.workflow_steps_label.setText("Ready to continue")
            self.workflow_hint_label.setText(
                "System time is valid and the prior RTC completion state was restored."
            )
            self._rtc_persistence_verified = True
            self._enable_continue()
            self._show_manual_controls_view()
            return

        # Check current time status first
        self._check_time_status()

        if self._current_time_source == "ntp":
            self.logger.info(
                "System time is already synchronized - now persisting to external RTC"
            )
            self.details_text.append(
                "✅ System time is already valid. The wizard will now save it to the external RTC."
            )
            self._schedule_workflow_callback(500, self._automatic_set_rtc)
            return

        # Time is NOT synchronized - need to set it up
        # Check if WiFi is connected to determine workflow
        wifi_connected = self._check_wifi_connected()

        if wifi_connected:
            # Automatically sync with NTP and set RTC
            self.details_text.append(
                "✅ WiFi connected - starting automatic time synchronization..."
            )
            self._schedule_workflow_callback(500, self._automatic_ntp_workflow)
        else:
            # No WiFi and time not synchronized - prompt user to manually set time
            self.details_text.append("⚠️ No WiFi connection detected")
            self.details_text.append(
                "📌 Please set the current time manually using the button below. If you expected WiFi to work, ask the study technician for help before continuing."
            )
            self._show_manual_controls_view()

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()
        # No longer monitoring RTC processes since we use synchronous run_sudo_command

    def deactivate_step(self) -> None:
        """Deactivate step when navigating away."""
        self.logger.info("Deactivating time synchronization step")
        super().deactivate_step()  # Base class handles timer cleanup

    def cleanup(self) -> None:
        """Clean up resources when step is destroyed."""
        self.logger.info("Cleaning up time synchronization step")
        super().cleanup()  # Base class handles timer cleanup

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Time synchronization step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
