"""Simplified WiFi connection step using system network settings."""

from __future__ import annotations

import os
import subprocess
from PyQt6.QtWidgets import QWidget, QMessageBox, QInputDialog, QLineEdit

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from constants import UI, Messages
from utils.ui_factory import ButtonStyle


class WiFiConnectionStep(WizardStep):
    """Step 2: Simple WiFi Configuration using system network settings."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def create_content_widget(self) -> QWidget:
        """Create the simplified WiFi connection UI."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Status section
        status_section = self._create_status_section()
        main_layout.addWidget(status_section)

        # Instructions section
        instructions_section = self._create_instructions_section()
        main_layout.addWidget(instructions_section)

        # Controls section
        controls_section = self._create_controls_section()
        main_layout.addWidget(controls_section)

        # Continue button
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        return content

    def _create_status_section(self) -> QWidget:
        """Create the WiFi status section."""
        status_group, status_layout = self.ui_factory.create_group_box("WiFi Connection Setup")

        self.wifi_status_label = self.ui_factory.create_status_label("Use the button below to open network settings", status_type="info")
        status_layout.addWidget(self.wifi_status_label)

        return status_group

    def _create_instructions_section(self) -> QWidget:
        """Create the instructions section."""
        instructions_group, instructions_layout = self.ui_factory.create_group_box("WiFi Setup Instructions")

        instructions_text = (
            "To connect to WiFi:\n\n"
            "Option 1 - Auto-Connect (Recommended):\n"
            "• Click 'Auto-Connect to Hotspot' to automatically connect\n"
            "• If credentials are not in .bashrc, you'll be prompted to enter them\n"
            "• Supports HOTSPOT1_PSK, HOTSPOT2_PSK, and HOTSPOT3_PSK\n\n"
            "Option 2 - Manual Setup:\n"
            "• Click 'Manual Network Settings' to configure manually\n"
            "• Connect to your WiFi network using the system settings\n\n"
            "Click 'Continue' when connected to proceed"
        )

        instructions_label = self.ui_factory.create_label(instructions_text)
        instructions_layout.addWidget(instructions_label)

        return instructions_group

    def _create_controls_section(self) -> QWidget:
        """Create the control buttons section."""
        controls_group, controls_layout = self.ui_factory.create_group_box("Connection Controls")

        # Auto-connect to hotspot button
        self.auto_connect_button = self.ui_factory.create_action_button(
            "Auto-Connect to Hotspot",
            callback=self._auto_connect_hotspot,
            style=ButtonStyle.PRIMARY,
            height=50,
        )
        controls_layout.addWidget(self.auto_connect_button)

        controls_layout.addSpacing(10)

        self.network_settings_button = self.ui_factory.create_action_button(
            "Manual Network Settings",
            callback=self._open_network_settings,
            style=ButtonStyle.SECONDARY,
            height=40,
        )
        controls_layout.addWidget(self.network_settings_button)

        controls_layout.addSpacing(20)

        # Skip button
        self.skip_button = self.ui_factory.create_action_button(
            "Skip WiFi Setup (If You Will Manually Set Time in the Next Step)",
            callback=self._skip_wifi_setup,
            style=ButtonStyle.SECONDARY,
            height=30,
        )
        controls_layout.addWidget(self.skip_button)

        return controls_group

    def _create_continue_section(self):
        """Create the continue button section."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(callback=self._on_continue_clicked, text="Continue to Next Step")
        return button_layout

    @handle_step_error
    def _open_network_settings(self, checked: bool = False) -> None:
        """Open the system network settings."""
        try:
            self.logger.info("Opening system network settings")

            # Try different network settings commands based on desktop environment
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
                    # Use subprocess.Popen directly to run in background
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    success = True
                    self.logger.info(f"Successfully opened network settings using: {' '.join(cmd)}")
                    break
                except (FileNotFoundError, OSError) as e:
                    self.logger.debug(f"Command {' '.join(cmd)} not found: {e}")
                    continue
                except Exception as e:
                    self.logger.debug(f"Command {' '.join(cmd)} failed: {e}")
                    continue

            if not success:
                # Fallback: show message with manual instructions
                QMessageBox.information(
                    self,
                    "Open Network Settings",
                    "Please open your system's network settings manually to connect to WiFi.\n\n"
                    "Common ways to access network settings:\n"
                    "• Click on the network icon in the system tray\n"
                    "• Go to System Settings → Network\n"
                    "• Search for 'Network' in your application launcher",
                )

        except Exception as e:
            self.logger.error(f"Error opening network settings: {e}")
            QMessageBox.warning(
                self,
                "Error",
                "Could not open network settings automatically. Please open your system's network settings manually to connect to WiFi.",
            )

    @handle_step_error
    def _auto_connect_hotspot(self, checked: bool = False) -> None:
        """Auto-connect to hotspot using the setup_wifi_connection.py script."""
        try:
            self.logger.info("Starting auto-connect to hotspot")

            self.wifi_status_label.setText("Attempting to connect to hotspot...")

            bashrc_path = os.path.expanduser("~/.bashrc")
            self.logger.info(f"Checking for hotspot credentials in: {bashrc_path}")
            has_credentials = False

            if os.path.exists(bashrc_path):
                self.logger.debug(f"Reading {bashrc_path} to check for credentials")
                with open(bashrc_path, "r") as f:
                    content = f.read()
                    if "HOTSPOT1_PSK" in content or "HOTSPOT2_PSK" in content or "HOTSPOT3_PSK" in content:
                        has_credentials = True
                        self.logger.info("Found existing hotspot credentials in .bashrc")
                    else:
                        self.logger.info("No hotspot credentials found in .bashrc")
            else:
                self.logger.warning(f".bashrc not found at {bashrc_path}")

            if not has_credentials:
                self.logger.info("No credentials found - prompting user for hotspot passwords")
                # Prompt for credentials
                hotspot_configs = []
                for i in range(1, 4):
                    reply = QMessageBox.question(
                        self,
                        f"Configure HOTSPOT{i}",
                        f"Do you want to configure HOTSPOT{i}?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self.logger.debug(f"User chose to configure HOTSPOT{i}")
                        password, ok = QInputDialog.getText(
                            self, f"HOTSPOT{i} Password", f"Enter the password for HOTSPOT{i}:", QLineEdit.EchoMode.Normal
                        )

                        if ok and password:
                            hotspot_configs.append(f"export HOTSPOT{i}_PSK='{password}'")
                            self.logger.info(f"User provided password for HOTSPOT{i}")
                        else:
                            self.logger.info(f"User cancelled password input for HOTSPOT{i}")
                    else:
                        self.logger.debug(f"User skipped configuration for HOTSPOT{i}")

                # Write credentials to .bashrc if any were provided
                if hotspot_configs:
                    self.logger.info(f"Writing {len(hotspot_configs)} hotspot credential(s) to .bashrc")
                    with open(bashrc_path, "a") as f:
                        f.write("\n# FLASH-TV Hotspot Credentials\n")
                        for config in hotspot_configs:
                            f.write(config + "\n")
                    self.logger.info("Successfully saved hotspot credentials to .bashrc")
                else:
                    self.logger.warning("No hotspot credentials were provided by user")

            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "python_scripts", "setup_wifi_connection.py"
            )

            self.logger.info(f"WiFi setup script path: {script_path}")

            if not os.path.exists(script_path):
                self.logger.error(f"WiFi setup script not found at: {script_path}")
                raise FileNotFoundError(f"WiFi setup script not found: {script_path}")
            else:
                self.logger.debug(f"WiFi setup script exists at: {script_path}")

            self.logger.info(f"Running WiFi setup script: {script_path}")
            self.logger.info("Executing: python3 " + script_path)

            result = subprocess.run(["python3", script_path], capture_output=True, text=True, timeout=30)

            # Log the complete output
            self.logger.info(f"WiFi script completed with return code: {result.returncode}")

            if result.stdout:
                self.logger.info(f"WiFi script stdout:\n{result.stdout}")
            else:
                self.logger.warning("WiFi script produced no stdout output")

            if result.stderr:
                self.logger.error(f"WiFi script stderr:\n{result.stderr}")
            else:
                self.logger.debug("WiFi script produced no stderr output")

            if result.returncode == 0:
                self.wifi_status_label.setText("✅ Successfully connected to hotspot!")
                self.logger.info("WiFi connection successful - script exited with code 0")
                self.state.set_user_input("wifi_ssid", "HOTSPOT_CONNECTED")
                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)

                QMessageBox.information(self, "Connection Successful", "Successfully connected to hotspot!\n\nClick 'Continue' to proceed.")
            else:
                error_msg = result.stderr if result.stderr else result.stdout if result.stdout else "Unknown error - no output"
                self.logger.error(f"WiFi connection failed with return code {result.returncode}")
                self.logger.error(f"Error details: {error_msg}")
                self.wifi_status_label.setText("❌ Failed to connect to hotspot")

                reply = QMessageBox.warning(
                    self,
                    "Connection Failed",
                    f"Failed to connect to hotspot.\n\nReturn code: {result.returncode}\n\nError: {error_msg}\n\n"
                    "Would you like to try manual network settings instead?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self._open_network_settings()

        except subprocess.TimeoutExpired:
            self.logger.error("WiFi connection timeout")
            self.wifi_status_label.setText("❌ Connection timeout")
            QMessageBox.warning(
                self,
                "Connection Timeout",
                "WiFi connection attempt timed out.\n\nPlease try manual network settings or check your hotspot configuration.",
            )
        except Exception as e:
            self.logger.error(f"Error during auto-connect: {e}")
            self.wifi_status_label.setText("❌ Auto-connect failed")
            QMessageBox.warning(self, "Auto-Connect Error", f"Failed to auto-connect to hotspot: {e}\n\nPlease try manual network settings instead.")

    @handle_step_error
    def _skip_wifi_setup(self, checked: bool = False) -> None:
        """Skip WiFi setup and continue with confirmation."""
        try:
            reply = QMessageBox.question(
                self,
                "Skip WiFi Setup (If You Will Manually Set Time in the Next Step)",
                "Are you sure you want to skip WiFi configuration?\n\nThe device will not be able to sync the time automatically.\nYou will need to set the time manually in the next step.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("User chose to skip WiFi setup")

                self.wifi_status_label.setText("WiFi setup skipped")
                self.state.set_user_input("wifi_ssid", "SKIPPED")

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)

        except Exception as e:
            self.logger.error(f"Error skipping WiFi setup: {e}")
            raise FlashTVError(
                f"Failed to skip WiFi setup: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try clicking skip again",
            )

    # WiFi checking removed - user manages connection through system settings

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            # User clicked continue - they know if WiFi is connected or not
            wifi_ssid = self.state.get_user_input("wifi_ssid", "")

            # Just continue - user has already opened network settings if needed
            self.logger.info(f"WiFi step completed")

            # Persist final state
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.request_next_step.emit()

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete WiFi step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Check WiFi connection or skip setup",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the network configuration step."""
        super().activate_step()
        self.logger.info("WiFi connection step activated")
        # Don't check WiFi automatically - let user handle it

    def update_ui(self) -> None:
        """Update UI elements periodically."""
        super().update_ui()
        # Don't continuously check WiFi - user will click Continue when ready

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("WiFi connection step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
