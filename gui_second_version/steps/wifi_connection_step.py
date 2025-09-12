"""Simplified WiFi connection step using system network settings."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QMessageBox

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
        status_group, status_layout = self.ui_factory.create_group_box(
            "WiFi Connection Setup"
        )

        self.wifi_status_label = self.ui_factory.create_status_label(
            "Use the button below to open network settings", status_type="info"
        )
        status_layout.addWidget(self.wifi_status_label)

        return status_group

    def _create_instructions_section(self) -> QWidget:
        """Create the instructions section."""
        instructions_group, instructions_layout = self.ui_factory.create_group_box(
            "WiFi Setup Instructions"
        )

        instructions_text = (
            "To connect to WiFi:\n\n"
            "1. Click 'Open Network Settings' below\n"
            "2. Connect to your WiFi network using the system settings\n"
            "3. Close the network settings window\n"
            "4. Click 'Continue' to proceed"
        )
        
        instructions_label = self.ui_factory.create_label(instructions_text)
        instructions_layout.addWidget(instructions_label)

        return instructions_group

    def _create_controls_section(self) -> QWidget:
        """Create the control buttons section."""
        controls_group, controls_layout = self.ui_factory.create_group_box(
            "Connection Controls"
        )

        # Open Network Settings button
        self.network_settings_button = self.ui_factory.create_action_button(
            "Open Network Settings",
            callback=self._open_network_settings,
            style=ButtonStyle.PRIMARY,
            height=50,
        )
        controls_layout.addWidget(self.network_settings_button)

        controls_layout.addSpacing(20)

        # Skip button
        self.skip_button = self.ui_factory.create_action_button(
            "Skip WiFi Setup",
            callback=self._skip_wifi_setup,
            style=ButtonStyle.SECONDARY,
            height=30,
        )
        controls_layout.addWidget(self.skip_button)

        return controls_group

    def _create_continue_section(self):
        """Create the continue button section."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text="Continue to Next Step"
        )
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
                    import subprocess
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
                    "• Search for 'Network' in your application launcher"
                )
                
        except Exception as e:
            self.logger.error(f"Error opening network settings: {e}")
            QMessageBox.warning(
                self,
                "Error",
                "Could not open network settings automatically. "
                "Please open your system's network settings manually to connect to WiFi."
            )

    @handle_step_error
    def _skip_wifi_setup(self, checked: bool = False) -> None:
        """Skip WiFi setup and continue with confirmation."""
        try:
            reply = QMessageBox.question(
                self,
                "Skip WiFi Setup",
                "Are you sure you want to skip WiFi setup?\n\n"
                "Some features may not work without an internet connection.",
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
            # Save final state before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("WiFi connection step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
