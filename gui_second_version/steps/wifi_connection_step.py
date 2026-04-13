from __future__ import annotations

import subprocess

from config.messages import MESSAGES
from core import WizardStep
from core.exceptions import ErrorType, FlashTVError, handle_step_error
from models import StepStatus
from models.state_keys import UserInputKey
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
from utils.ui_factory import ButtonStyle


class WiFiConnectionStep(WizardStep):
    NETWORK_SETTINGS_POLL_INTERVAL_MS = 3000
    NETWORK_SETTINGS_POLL_MAX_ATTEMPTS = 10

    def create_content_widget(self) -> QWidget:
        from PySide6.QtWidgets import QHBoxLayout

        content = QWidget()
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)

        status_section = self._create_status_section()
        columns_layout.addWidget(status_section, stretch=1)

        instructions_section = self._create_instructions_section()
        columns_layout.addWidget(instructions_section, stretch=1)

        main_layout.addLayout(columns_layout)
        main_layout.addStretch()

        button_row = self._create_action_buttons()
        main_layout.addLayout(button_row)

        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        self.network_settings_poll_timer = self.create_timer(
            self.NETWORK_SETTINGS_POLL_INTERVAL_MS,
            self._poll_for_wifi_connection,
            start=False,
        )
        self._network_settings_poll_attempts = 0

        self._show_disconnected_status()
        return content

    def _create_status_section(self) -> QWidget:
        status_group, status_layout = self.ui_factory.create_group_box(
            "Current WiFi Status"
        )

        self.wifi_status_label = self.ui_factory.create_status_label(
            "Checking WiFi connection...", status_type="info"
        )
        status_layout.addWidget(self.wifi_status_label)

        self.internet_status_label = self.ui_factory.create_status_label(
            "Internet time status will appear here.", status_type="info"
        )
        status_layout.addWidget(self.internet_status_label)

        return status_group

    def _create_instructions_section(self) -> QWidget:
        instructions_group, instructions_layout = self.ui_factory.create_group_box(
            "Instructions"
        )

        instructions_text = (
            "WiFi is required for automatic time synchronization.\n\n"
            "• Click 'Open Network Settings' to connect this device to WiFi\n"
            "• If you connect successfully, this page will detect it automatically\n"
            "• Or click 'Skip WiFi Setup' if you will set the time manually in the next step"
        )

        instructions_label = self.ui_factory.create_label(instructions_text)
        instructions_layout.addWidget(instructions_label)

        return instructions_group

    def _create_action_buttons(self):
        from PySide6.QtWidgets import QHBoxLayout

        button_row = QHBoxLayout()
        button_row.setSpacing(15)

        self.network_settings_button = self.ui_factory.create_action_button(
            "Open Network Settings",
            callback=self._open_network_settings,
            style=ButtonStyle.PRIMARY,
            height=50,
        )
        button_row.addWidget(self.network_settings_button)

        self.skip_button = self.ui_factory.create_action_button(
            "Skip WiFi Setup (Manual Time)",
            callback=self._skip_wifi_setup,
            style=ButtonStyle.SECONDARY,
            height=50,
        )
        button_row.addWidget(self.skip_button)

        return button_row

    def _create_continue_section(self):
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text=MESSAGES.UI.CONTINUE
        )
        return button_layout

    def _set_status_label(self, label, text: str, status_type: str) -> None:
        label.setText(text)

        styles = {
            "info": "color: #1976d2; font-weight: bold; padding: 5px;",
            "success": "color: #2e7d32; font-weight: bold; padding: 5px;",
            "warning": "color: #f57c00; font-weight: bold; padding: 5px;",
            "error": "color: #c62828; font-weight: bold; padding: 5px;",
        }
        label.setStyleSheet(styles[status_type])

    def _persist_wifi_state(self, ssid: str, connected: bool) -> None:
        self.state.set_user_input(UserInputKey.WIFI_SSID, ssid)
        self.state.set_user_input(UserInputKey.WIFI_CONNECTED, connected)

        if self.state_manager:
            self.state_manager.save_state(self.state)

    def _show_disconnected_status(self) -> None:
        self._set_status_label(
            self.wifi_status_label,
            "❌ Not connected to WiFi",
            "error",
        )
        self._set_status_label(
            self.internet_status_label,
            "Open network settings to connect, then this page will keep checking for you.",
            "info",
        )
        self.continue_button.setEnabled(False)

    def _show_skipped_status(self) -> None:
        self._set_status_label(
            self.wifi_status_label,
            "WiFi setup skipped",
            "warning",
        )
        self._set_status_label(
            self.internet_status_label,
            "You can continue and set the time manually in the next step.",
            "info",
        )
        self.continue_button.setEnabled(True)

    def _refresh_connection_status(self) -> bool:
        wifi_connected, network_name = self._check_wifi_connected()

        if not wifi_connected:
            self._persist_wifi_state("", False)
            self._show_disconnected_status()
            return False

        ntp_reachable, ntp_server = self._check_ntp_reachable()

        self._persist_wifi_state(network_name, True)
        self._set_status_label(
            self.wifi_status_label,
            f"✅ Already connected to: {network_name}",
            "success",
        )

        if ntp_reachable:
            self._set_status_label(
                self.internet_status_label,
                f"✅ Internet time is available. The clock can sync automatically. ({ntp_server})",
                "success",
            )
        else:
            self._set_status_label(
                self.internet_status_label,
                "⚠️ Connected to WiFi, but internet time is not reachable right now. You can still continue.",
                "warning",
            )

        self.update_status(StepStatus.COMPLETED)
        self.continue_button.setEnabled(True)
        return True

    def _stop_network_settings_polling(self) -> None:
        self.network_settings_poll_timer.stop()
        self._network_settings_poll_attempts = 0

    def _start_network_settings_polling(self) -> None:
        self._network_settings_poll_attempts = 0
        self.network_settings_poll_timer.start()
        self._set_status_label(
            self.wifi_status_label,
            "🔎 Waiting for a WiFi connection...",
            "info",
        )
        self._set_status_label(
            self.internet_status_label,
            "This page will check every 3 seconds for up to 30 seconds after you open network settings.",
            "info",
        )
        self.continue_button.setEnabled(False)

    def _poll_for_wifi_connection(self) -> None:
        self._network_settings_poll_attempts += 1
        self.logger.info(
            "Checking for WiFi connection after opening settings "
            f"({self._network_settings_poll_attempts}/{self.NETWORK_SETTINGS_POLL_MAX_ATTEMPTS})"
        )

        if self._refresh_connection_status():
            self.logger.info("Detected WiFi connection during post-settings polling")
            self._stop_network_settings_polling()
            return

        if (
            self._network_settings_poll_attempts
            >= self.NETWORK_SETTINGS_POLL_MAX_ATTEMPTS
        ):
            self._stop_network_settings_polling()
            self._set_status_label(
                self.internet_status_label,
                "Still not connected. If you need more time, finish connecting and then click 'Open Network Settings' again.",
                "warning",
            )

    @handle_step_error
    def _open_network_settings(self, checked: bool = False) -> None:
        try:
            self.logger.info("Opening system network settings")

            commands_to_try = [
                ["gnome-control-center", "wifi"],
                ["unity-control-center", "network"],
                ["systemsettings5", "kcm_networkmanagement"],
                ["nm-connection-editor"],
                ["network-manager-gnome"],
            ]

            success = False
            for cmd in commands_to_try:
                try:
                    subprocess.Popen(
                        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    success = True
                    self.logger.info(
                        f"Successfully opened network settings using: {' '.join(cmd)}"
                    )
                    break
                except (FileNotFoundError, OSError) as e:
                    self.logger.debug(f"Command {' '.join(cmd)} not found: {e}")
                except Exception as e:
                    self.logger.debug(f"Command {' '.join(cmd)} failed: {e}")

            if not success:
                QMessageBox.information(
                    self,
                    "Open Network Settings",
                    "The setup window could not open network settings automatically.\n\n"
                    "Please open WiFi settings yourself and connect to the study network.\n"
                    "Common ways to do that:\n"
                    "• Click the network icon in the system tray\n"
                    "• Go to System Settings → Network\n"
                    "• Search for 'Network' in your app launcher\n\n"
                    "If you cannot find the WiFi settings or the network will not connect, ask the study technician for help.",
                )

            self._start_network_settings_polling()

        except Exception as e:
            self.logger.error(f"Error opening network settings: {e}")
            self._start_network_settings_polling()
            QMessageBox.warning(
                self,
                "Error",
                "The setup window could not open network settings automatically.\n\n"
                "Please open WiFi settings yourself and connect to the study network.\n"
                "If that still does not work, ask the study technician for help.",
            )

    @handle_step_error
    def _skip_wifi_setup(self, checked: bool = False) -> None:
        try:
            reply = QMessageBox.question(
                self,
                "Skip WiFi Setup (If You Will Manually Set Time in the Next Step)",
                "Are you sure you want to skip WiFi setup?\n\n"
                "What happened: this device will not be able to set the time automatically.\n"
                "What to do next: continue only if you are ready to set the time manually in the next step.\n"
                "When to ask for help: if you expected WiFi to work, stop here and ask the study technician.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("User chose to skip WiFi setup")
                self._stop_network_settings_polling()
                self._persist_wifi_state("SKIPPED", False)
                self._show_skipped_status()
                self.update_status(StepStatus.COMPLETED)

        except Exception as e:
            self.logger.error(f"Error skipping WiFi setup: {e}")
            raise FlashTVError(
                f"Failed to skip WiFi setup: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try clicking skip again",
            )

    def _check_wifi_connected(self) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                [
                    "nmcli",
                    "-t",
                    "-f",
                    "TYPE,NAME,STATE",
                    "connection",
                    "show",
                    "--active",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split(":")
                        if len(parts) >= 3:
                            conn_type = parts[0].strip()
                            conn_name = parts[1].strip()

                            if (
                                "wireless" in conn_type.lower()
                                or "wifi" in conn_type.lower()
                            ):
                                self.logger.info(f"WiFi connected: {conn_name}")
                                return True, conn_name

                self.logger.info("No active WiFi connection found")
                return False, ""

            self.logger.warning(f"nmcli command failed: {result.stderr}")
            return False, ""

        except subprocess.TimeoutExpired:
            self.logger.error("WiFi check timed out")
            return False, ""
        except Exception as e:
            self.logger.error(f"Error checking WiFi connection: {e}")
            return False, ""

    def _check_ntp_reachable(self) -> tuple[bool, str]:
        ntp_servers = ["time.google.com", "pool.ntp.org", "time.cloudflare.com"]

        for server in ntp_servers:
            try:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "2", server],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    self.logger.info(f"NTP server reachable: {server}")
                    return True, server

            except subprocess.TimeoutExpired:
                self.logger.debug(f"Ping to {server} timed out")
            except Exception as e:
                self.logger.debug(f"Error pinging {server}: {e}")

        self.logger.warning("No NTP servers reachable")
        return False, ""

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        try:
            wifi_ssid = self.state.get_user_input(UserInputKey.WIFI_SSID, "")
            if wifi_ssid == "SKIPPED":
                self.logger.info("WiFi was skipped, proceeding to next step")
                if self.state_manager:
                    self.state_manager.save_state(self.state)
                self.request_next_step.emit()
                return

            self._stop_network_settings_polling()
            self._set_status_label(
                self.wifi_status_label,
                "Checking WiFi connection...",
                "info",
            )
            self.continue_button.setEnabled(False)
            QApplication.processEvents()

            wifi_connected, network_name = self._check_wifi_connected()

            if not wifi_connected:
                self._persist_wifi_state("NO_CONNECTION", False)
                self._show_disconnected_status()

                reply = QMessageBox.warning(
                    self,
                    "No WiFi Connection",
                    "No WiFi connection was found.\n\n"
                    "What happened: this device is not connected to WiFi right now.\n"
                    "What to try next: connect to WiFi, then try again. You can continue without WiFi only if you are ready to set the time manually in the next step.\n"
                    "When to ask for help: if the study network should be available but will not connect, ask the study technician.\n\n"
                    "Do you want to continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self.logger.info("User chose to continue without WiFi")
                    self.update_status(StepStatus.COMPLETED)
                    self.continue_button.setEnabled(True)
                    if self.state_manager:
                        self.state_manager.save_state(self.state)
                    self.request_next_step.emit()
                else:
                    self.continue_button.setEnabled(True)
                return

            ntp_reachable, ntp_server = self._check_ntp_reachable()
            self._persist_wifi_state(network_name, True)

            self._set_status_label(
                self.wifi_status_label,
                f"✅ Already connected to: {network_name}",
                "success",
            )

            if ntp_reachable:
                self._set_status_label(
                    self.internet_status_label,
                    f"✅ Internet time is available. The clock can sync automatically. ({ntp_server})",
                    "success",
                )
            else:
                self._set_status_label(
                    self.internet_status_label,
                    "⚠️ WiFi is connected, but internet time is not available right now. You can continue, but the next step may ask you to set the time manually. If this keeps happening on a known-good network, ask the study technician for help.",
                    "warning",
                )

            self.logger.info(
                f"WiFi step completed successfully: {network_name}, NTP reachable: {ntp_reachable}"
            )
            self.update_status(StepStatus.COMPLETED)
            self.continue_button.setEnabled(True)
            self.request_next_step.emit()

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            self.continue_button.setEnabled(True)
            raise FlashTVError(
                f"Failed to complete WiFi step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Check the WiFi connection and try again. If WiFi still will not connect, continue without WiFi only if you can set the time manually in the next step. Ask the study technician for help if needed.",
            )

    @handle_step_error
    def activate_step(self) -> None:
        super().activate_step()
        self.logger.info("WiFi connection step activated")

        wifi_ssid = self.state.get_user_input(UserInputKey.WIFI_SSID, "")
        if wifi_ssid == "SKIPPED":
            self._show_skipped_status()
            self.update_status(StepStatus.COMPLETED)
            return

        self._stop_network_settings_polling()
        self._refresh_connection_status()

    def update_ui(self) -> None:
        super().update_ui()

    def _cleanup_step_resources(self) -> None:
        try:
            self._stop_network_settings_polling()
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("WiFi connection step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
