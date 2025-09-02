"""Network configuration step implementation using new framework patterns."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QDialog,
    QLineEdit,
)

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from constants import UI, Messages, Network
from utils.ui_factory import ButtonStyle


class WiFiConnectionStep(WizardStep):
    """Step 2: Network Configuration."""

    def create_content_widget(self) -> QWidget:
        """Create the WiFi connection UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Status section using UI factory
        status_section = self._create_status_section()
        main_layout.addWidget(status_section)

        # Main content using UI factory
        content_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Networks and controls sections
        networks_section = self._create_networks_section()
        controls_section = self._create_controls_section()

        content_row.addWidget(networks_section, 3)  # 60% width
        content_row.addWidget(controls_section, 2)  # 40% width

        main_layout.addLayout(content_row, 1)  # Give it stretch

        # Continue button using UI factory
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        # Track connection status
        self.wifi_connected = False

        return content

    def _create_status_section(self) -> QWidget:
        """Create the WiFi status section using UI factory."""
        status_group, status_layout = self.ui_factory.create_group_box(
            "WiFi Connection Status"
        )

        self.wifi_status_label = self.ui_factory.create_status_label(
            Messages.CHECKING_WIFI_CONNECTION, status_type="info"
        )
        status_layout.addWidget(self.wifi_status_label)

        return status_group

    def _create_networks_section(self) -> QWidget:
        """Create the networks list section using UI factory."""
        networks_group, networks_layout = self.ui_factory.create_group_box(
            "Available Networks"
        )

        networks_label = self.ui_factory.create_label(
            "Double-click a network to connect:"
        )
        networks_layout.addWidget(networks_label)

        self.networks_list = QListWidget()
        self.networks_list.itemDoubleClicked.connect(self._connect_to_network)
        self.networks_list.itemSelectionChanged.connect(self._on_network_selected)
        networks_layout.addWidget(self.networks_list)

        return networks_group

    def _create_controls_section(self) -> QWidget:
        """Create the connection controls section using UI factory."""
        controls_group, controls_layout = self.ui_factory.create_group_box(
            "Connection Controls"
        )

        # Scan button
        self.scan_button = self.ui_factory.create_action_button(
            UI.SCAN_FOR_NETWORKS,
            callback=self._scan_networks,
            style=ButtonStyle.PRIMARY,
            height=40,
        )
        controls_layout.addWidget(self.scan_button)

        controls_layout.addSpacing(10)

        # Connect button
        self.connect_button = self.ui_factory.create_action_button(
            UI.CONNECT_TO_SELECTED_NETWORK,
            callback=self._connect_to_selected_network,
            style=ButtonStyle.SUCCESS,
            height=40,
            enabled=False,
        )
        controls_layout.addWidget(self.connect_button)

        controls_layout.addSpacing(20)

        # Skip button
        self.skip_button = self.ui_factory.create_action_button(
            UI.SKIP_WIFI_SETUP,
            callback=self._skip_wifi_setup,
            style=ButtonStyle.SECONDARY,
            height=30,
        )
        controls_layout.addWidget(self.skip_button)

        controls_layout.addStretch()

        return controls_group

    def _create_continue_section(self):
        """Create the continue button section using UI factory."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text=UI.CONTINUE_TO_NEXT_STEP
        )

        return button_layout

    @handle_step_error
    def _check_current_wifi(self) -> None:
        """Check current WiFi connection status with error handling."""
        try:
            self.logger.info("Checking current WiFi connection status")

            result = self.process_runner.run_command(
                ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
                timeout_ms=Network.WIFI_SCAN_TIMEOUT * 1000,
            )

            if result and result.returncode == 0:
                for line in result.stdout.split("\\n"):
                    if line.startswith("yes:"):
                        ssid = line.split(":", 1)[1]
                        self._handle_wifi_connected(ssid)
                        return

            self._handle_no_wifi_connection()

        except Exception as e:
            self.logger.error(f"Error checking WiFi status: {e}")
            raise FlashTVError(
                f"Failed to check WiFi status: {e}",
                ErrorType.NETWORK_ERROR,
                recovery_action="Try manually checking network settings",
            )

    def _handle_wifi_connected(self, ssid: str) -> None:
        """Handle successful WiFi connection detection."""
        self.wifi_status_label.setText(
            Messages.WIFI_CONNECTION_SUCCESS.format(ssid=ssid)
        )
        self.state.set_user_input("wifi_ssid", ssid)

        # Persist state
        if self.state_manager:
            self.state_manager.save_state(self.state)

        self.wifi_connected = True
        self.continue_button.setEnabled(True)
        self.update_status(StepStatus.COMPLETED)

        self.logger.info(f"WiFi already connected to: {ssid}")

    def _handle_no_wifi_connection(self) -> None:
        """Handle no WiFi connection detected."""
        self.wifi_status_label.setText(Messages.NO_WIFI_CONNECTION)
        self.logger.warning("No active WiFi connection detected")

    @handle_step_error
    def _on_network_selected(self) -> None:
        """Handle network selection with logging."""
        has_selection = self.networks_list.currentItem() is not None
        self.connect_button.setEnabled(has_selection)

        if has_selection:
            selected_item = self.networks_list.currentItem()
            network_data = selected_item.data(32)
            if network_data:
                self.logger.debug(
                    f"Selected network: {network_data.get('ssid', 'Unknown')}"
                )

    @handle_step_error
    def _scan_networks(self, checked: bool = False) -> None:
        """Scan for available WiFi networks with comprehensive error handling."""
        try:
            self.logger.info("Starting WiFi network scan")

            # Update UI state
            self.scan_button.setEnabled(False)
            self.scan_button.setText("Scanning...")
            self.networks_list.clear()

            # Trigger scan using process runner
            scan_result = self.process_runner.run_command(
                ["nmcli", "dev", "wifi", "rescan"],
                timeout_ms=Network.WIFI_SCAN_TIMEOUT * 1000,
            )

            if not scan_result or scan_result.returncode != 0:
                raise FlashTVError(
                    "Failed to trigger WiFi scan",
                    ErrorType.NETWORK_ERROR,
                    recovery_action="Check WiFi adapter is enabled",
                )

            # Get scan results
            result = self.process_runner.run_command(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi"],
                timeout_ms=Network.WIFI_SCAN_TIMEOUT * 1000,
            )

            if result and result.returncode == 0:
                self._process_scan_results(result.stdout)
            else:
                raise FlashTVError(
                    "Failed to get WiFi scan results",
                    ErrorType.NETWORK_ERROR,
                    recovery_action="Try scanning again",
                )

        except Exception as e:
            self.logger.error(f"Error during WiFi scan: {e}")
            error_item = QListWidgetItem(f"Error scanning networks: {e}")
            self.networks_list.addItem(error_item)
            raise

        finally:
            # Restore button state
            self.scan_button.setEnabled(True)
            self.scan_button.setText("Scan for Networks")

    def _process_scan_results(self, scan_output: str) -> None:
        """Process and display WiFi scan results."""
        networks = []

        for line in scan_output.split("\\n"):
            if line.strip():
                parts = line.split(":")
                if len(parts) >= 3:
                    ssid = parts[0]
                    signal = parts[1] if parts[1] else "0"
                    security = parts[2]
                    if ssid:  # Skip hidden networks
                        networks.append((ssid, signal, security))

        # Sort by signal strength
        networks.sort(key=lambda x: int(x[1]) if x[1].isdigit() else 0, reverse=True)

        for ssid, signal, security in networks:
            signal_bars = "█" * (int(signal) // 20) + "░" * (5 - int(signal) // 20)
            security_icon = "🔒" if security else "🔓"
            item_text = f"{ssid} [{signal_bars}] {signal}% {security_icon}"

            item = QListWidgetItem(item_text)
            item.setData(32, {"ssid": ssid, "security": security})
            self.networks_list.addItem(item)

        self.logger.info(f"Found {len(networks)} WiFi networks")
        self.connect_button.setEnabled(len(networks) > 0)

    @handle_step_error
    def _connect_to_selected_network(self) -> None:
        """Connect to the selected network with validation."""
        try:
            current_item = self.networks_list.currentItem()
            if not current_item:
                QMessageBox.warning(
                    self, Messages.NO_NETWORK_SELECTED, Messages.SELECT_NETWORK_FIRST
                )
                return

            network_data = current_item.data(32)
            if not network_data:
                self.logger.warning("Selected network has no data")
                return

            self._connect_to_network(current_item)

        except Exception as e:
            self.logger.error(f"Error connecting to selected network: {e}")
            raise FlashTVError(
                f"Failed to connect to selected network: {e}",
                ErrorType.NETWORK_ERROR,
                recovery_action="Try selecting and connecting again",
            )

    @handle_step_error
    def _connect_to_network(self, item: QListWidgetItem) -> None:
        """Connect to a specific network with comprehensive handling."""
        try:
            network_data = item.data(32)
            if not network_data:
                self.logger.warning("Network item has no data")
                return

            ssid = network_data["ssid"]
            has_security = bool(network_data["security"])

            self.logger.info(f"Attempting to connect to network: {ssid}")

            # Show password dialog if network is secured
            if has_security:
                password = self._get_network_password(ssid)
                if not password:
                    self.logger.info("User cancelled password entry")
                    return
            else:
                password = ""

            # Attempt connection
            success = self._connect_to_wifi_network(ssid, password)

            if success:
                self._handle_wifi_connected(ssid)
                QMessageBox.information(
                    self,
                    Messages.CONNECTED_SUCCESS,
                    Messages.SUCCESSFULLY_CONNECTED.format(ssid=ssid),
                )
            else:
                self.logger.error(f"Failed to connect to network: {ssid}")
                QMessageBox.critical(
                    self,
                    Messages.CONNECTION_FAILED,
                    Messages.FAILED_TO_CONNECT.format(ssid=ssid),
                )

        except Exception as e:
            self.logger.error(f"Error connecting to network: {e}")
            raise FlashTVError(
                f"Failed to connect to network: {e}",
                ErrorType.NETWORK_ERROR,
                recovery_action="Check network credentials and try again",
            )

    @handle_step_error
    def _get_network_password(self, ssid: str) -> str | None:
        """Show password dialog for secured network with error handling."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Connect to: {ssid}")
            dialog.setModal(True)
            dialog.resize(400, 150)

            # Use UI factory for dialog layout
            layout = self.ui_factory.create_vertical_layout()
            dialog.setLayout(layout)

            # Network info labels
            layout.addWidget(self.ui_factory.create_label(f"Network: {ssid}"))
            layout.addWidget(
                self.ui_factory.create_label(Messages.NETWORK_REQUIRES_PASSWORD)
            )

            # Password input
            layout.addWidget(self.ui_factory.create_label("Password:"))
            password_input = self.ui_factory.create_input_field(
                "Enter network password"
            )
            password_input.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(password_input)

            # Dialog buttons
            button_layout = self.ui_factory.create_horizontal_layout()
            cancel_button = self.ui_factory.create_standard_button(
                "Cancel", dialog.reject
            )
            connect_button = self.ui_factory.create_standard_button(
                "Connect", dialog.accept
            )

            button_layout.addWidget(cancel_button)
            button_layout.addWidget(connect_button)
            layout.addLayout(button_layout)

            self.logger.debug(f"Showing password dialog for network: {ssid}")

            if dialog.exec() == QDialog.DialogCode.Accepted:
                password = password_input.text()
                self.logger.info(f"Password entered for network: {ssid}")
                return password

            return None

        except Exception as e:
            self.logger.error(f"Error showing password dialog: {e}")
            raise FlashTVError(
                f"Failed to show password dialog: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try connecting to the network again",
            )

    @handle_step_error
    def _connect_to_wifi_network(self, ssid: str, password: str) -> bool:
        """Attempt to connect to WiFi network using process runner."""
        try:
            self.logger.info(f"Attempting WiFi connection to: {ssid}")

            # Check if connection profile exists
            result = self.process_runner.run_command(
                ["nmcli", "-t", "-f", "NAME", "connection", "show"], timeout_ms=10000
            )

            if result and ssid in result.stdout:
                # Connection exists, just activate it
                self.logger.debug(f"Using existing connection profile for: {ssid}")
                connect_result = self.process_runner.run_command(
                    ["nmcli", "connection", "up", ssid],
                    timeout_ms=Network.WIFI_CONNECT_TIMEOUT * 1000,
                )
            else:
                # Create new connection
                self.logger.debug(f"Creating new connection profile for: {ssid}")
                if password:
                    cmd = [
                        "nmcli",
                        "dev",
                        "wifi",
                        "connect",
                        ssid,
                        "password",
                        password,
                    ]
                else:
                    cmd = ["nmcli", "dev", "wifi", "connect", ssid]

                connect_result = self.process_runner.run_command(
                    cmd, timeout_ms=Network.WIFI_CONNECT_TIMEOUT * 1000
                )

            success = connect_result and connect_result.returncode == 0

            if success:
                self.logger.info(f"Successfully connected to WiFi: {ssid}")
            else:
                self.logger.error(f"Failed to connect to WiFi: {ssid}")
                if connect_result:
                    self.logger.error(f"Connection error: {connect_result.stderr}")

            return success

        except Exception as e:
            self.logger.error(f"Exception during WiFi connection: {e}")
            return False

    @handle_step_error
    def _skip_wifi_setup(self, checked: bool = False) -> None:
        """Skip WiFi setup and continue with confirmation."""
        try:
            reply = QMessageBox.question(
                self,
                Messages.SKIP_WIFI_SETUP,
                Messages.SKIP_WIFI_CONFIRMATION,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("User chose to skip WiFi setup")

                self.wifi_status_label.setText(Messages.WIFI_SETUP_SKIPPED)
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

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            wifi_ssid = self.state.get_user_input("wifi_ssid", "")

            if self.wifi_connected or wifi_ssid == "SKIPPED":
                self.logger.info(f"WiFi step completed with SSID: {wifi_ssid}")

                # Persist final state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning(
                    "Continue clicked but WiFi not connected and not skipped"
                )

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete WiFi step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Check WiFi connection or skip setup",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the network configuration step with enhanced logic."""
        super().activate_step()

        self.logger.info("WiFi connection step activated")

        # Check current WiFi status
        self._check_current_wifi()

        # If not connected, automatically scan for networks
        if not self.wifi_connected:
            self._scan_networks()

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()

        # Periodic WiFi status check if not connected
        if not self.wifi_connected and hasattr(self, "_last_wifi_check"):
            import time

            current_time = time.time()
            if current_time - self._last_wifi_check > 30:  # Check every 30 seconds
                try:
                    self._check_current_wifi()
                    self._last_wifi_check = current_time
                except Exception as e:
                    self.logger.error(f"Error during periodic WiFi check: {e}")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("WiFi connection step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
