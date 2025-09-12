"""Service configuration step implementation."""

from __future__ import annotations

import subprocess

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QGroupBox,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
)

from core import WizardStep
from models import StepStatus


class ServiceConfigurationStep(WizardStep):
    """Step 8: System Service Setup."""

    def create_content_widget(self) -> QWidget:
        """Create the service configuration UI."""
        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)

        # Overview section (full width at top)
        overview_group = QGroupBox("System Service Configuration")
        overview_layout = QVBoxLayout(overview_group)
        overview_layout.setContentsMargins(8, 8, 8, 8)

        overview_text = QLabel("""This step configures system services for automatic FLASH-TV operation:

• flash-run-on-boot.service: Starts FLASH-TV automatically on system boot
• flash-periodic-restart.service: Restarts FLASH-TV periodically to prevent memory issues
• System integration with participant-specific configuration
• Automatic log rotation and cleanup

Services will be configured with your participant and user information.""")
        overview_text.setWordWrap(True)
        overview_layout.addWidget(overview_text)

        main_layout.addWidget(overview_group)

        # Middle row: Status and Configuration side by side
        middle_row = QHBoxLayout()
        middle_row.setSpacing(12)

        # Left side: Service Status
        status_group = QGroupBox("Current Service Status")
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(8, 8, 8, 8)

        self.refresh_status_button = QPushButton("Refresh Service Status")
        self.refresh_status_button.setFixedHeight(30)
        self.refresh_status_button.clicked.connect(self._refresh_service_status)
        status_layout.addWidget(self.refresh_status_button)

        self.service_list = QListWidget()
        status_layout.addWidget(self.service_list)

        # Right side: Configuration controls
        config_group = QGroupBox("Service Controls")
        config_layout = QVBoxLayout(config_group)
        config_layout.setContentsMargins(8, 8, 8, 8)

        self.configure_button = QPushButton("Configure System Services")
        self.configure_button.setFixedHeight(40)
        self.configure_button.clicked.connect(self._configure_services)
        config_layout.addWidget(self.configure_button)

        config_layout.addSpacing(10)

        # Service control buttons
        service_control_label = QLabel("Service Management:")
        config_layout.addWidget(service_control_label)

        self.start_services_button = QPushButton("Start Services")
        self.start_services_button.setFixedHeight(30)
        self.start_services_button.clicked.connect(self._start_services)
        self.start_services_button.setEnabled(False)
        config_layout.addWidget(self.start_services_button)

        self.stop_services_button = QPushButton("Stop Services")
        self.stop_services_button.setFixedHeight(30)
        self.stop_services_button.clicked.connect(self._stop_services)
        self.stop_services_button.setEnabled(False)
        config_layout.addWidget(self.stop_services_button)

        config_layout.addStretch()

        # Add both to middle row
        middle_row.addWidget(status_group, 3)  # 60% width
        middle_row.addWidget(config_group, 2)  # 40% width

        main_layout.addLayout(middle_row)

        # Bottom: Output (full width)
        output_group = QGroupBox("Configuration Progress")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(8, 8, 8, 8)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)

        main_layout.addWidget(output_group, 1)  # Give it stretch

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 5, 0, 0)

        self.continue_button = QPushButton("Continue to Next Step")
        self.continue_button.setFixedHeight(30)
        self.continue_button.clicked.connect(self._on_continue_clicked)
        self.continue_button.setEnabled(False)

        button_layout.addStretch()
        button_layout.addWidget(self.continue_button)

        main_layout.addLayout(button_layout)

        return content

    def _refresh_service_status(self) -> None:
        """Refresh the status of FLASH-TV services."""
        self.service_list.clear()

        services = ["flash-run-on-boot.service", "flash-periodic-restart.service"]

        for service in services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                status = result.stdout.strip()
                if status == "active":
                    status_icon = "🟢"
                    status_text = "ACTIVE"
                elif status == "inactive":
                    status_icon = "🔴"
                    status_text = "INACTIVE"
                elif status == "failed":
                    status_icon = "❌"
                    status_text = "FAILED"
                else:
                    status_icon = "⚪"
                    status_text = status.upper()

                # Check if service is enabled
                enabled_result = subprocess.run(
                    ["systemctl", "is-enabled", service],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                enabled_status = enabled_result.stdout.strip()
                if enabled_status == "enabled":
                    enabled_text = "ENABLED"
                else:
                    enabled_text = "DISABLED"

                display_text = (
                    f"{status_icon} {service}: {status_text} ({enabled_text})"
                )

            except Exception as e:
                display_text = f"❓ {service}: ERROR - {e}"

            item = QListWidgetItem(display_text)
            self.service_list.addItem(item)

        # Check if services are properly configured
        self._check_service_configuration()

    def _check_service_configuration(self) -> None:
        """Check if services are properly configured."""
        try:
            # Check if service files exist
            service_files = [
                "/etc/systemd/system/flash-run-on-boot.service",
                "/etc/systemd/system/flash-periodic-restart.service",
            ]

            all_configured = True
            for service_file in service_files:
                try:
                    with open(service_file, "r") as f:
                        content = f.read()
                        # Check if placeholder XXX is still present
                        if "XXX" in content:
                            all_configured = False
                            break
                except FileNotFoundError:
                    all_configured = False
                    break

            if all_configured:
                self.start_services_button.setEnabled(True)
                self.stop_services_button.setEnabled(True)
                self.state.set_system_state("services_configured", True)

                # Check if all services are active
                active_count = 0
                for i in range(self.service_list.count()):
                    item_text = self.service_list.item(i).text()
                    if "ACTIVE" in item_text:
                        active_count += 1

                if active_count == 2:  # Both services active
                    self.continue_button.setEnabled(True)
                    self.update_status(StepStatus.COMPLETED)
                    self.output_text.append(
                        "✅ All services are configured and running"
                    )
                else:
                    self.output_text.append(
                        "⚠️ Services configured but not all are running"
                    )
            else:
                self.output_text.append(
                    "❌ Services not properly configured - run configuration"
                )

        except Exception as e:
            self.output_text.append(f"Error checking service configuration: {e}")

    def _configure_services(self) -> None:
        """Configure system services."""
        participant_id = self.state.get_user_input("participant_id", "")
        device_id = self.state.get_user_input("device_id", "")
        username = self.state.get_user_input("username", "")

        if not all([participant_id, username]):
            self.output_text.append("❌ Missing participant ID or username")
            return

        # Combine participant_id and device_id
        full_participant_id = f"{participant_id}{device_id}" if device_id else participant_id

        self.update_status(StepStatus.AUTOMATION_RUNNING)
        self.configure_button.setEnabled(False)

        self.output_text.append("🔧 Configuring system services...")
        self.output_text.append(f"Participant: {full_participant_id}")
        self.output_text.append(f"Username: {username}")

        # Run service configuration script with combined ID
        script_path = "../setup_scripts/service_setup.sh"
        command = ["bash", script_path, full_participant_id, username]

        process_info = self.process_runner.run_script(
            command=command,
            description="Configuring system services",
            working_dir="../setup_scripts",
            process_name="service_configuration",
        )

        if process_info:
            self.output_text.append("Service configuration started...")
        else:
            self.output_text.append("❌ Failed to start service configuration")
            self.configure_button.setEnabled(True)
            self.update_status(StepStatus.FAILED)

    def _start_services(self) -> None:
        """Start FLASH-TV services."""
        self.start_services_button.setEnabled(False)
        self.output_text.append("🚀 Starting FLASH-TV services...")

        try:
            # Run start services script
            result = subprocess.run(
                ["bash", "../services/start_services.sh"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="../services",
            )

            if result.returncode == 0:
                self.output_text.append("✅ Services started successfully")
                self.output_text.append(result.stdout)
                self._refresh_service_status()
            else:
                self.output_text.append(f"❌ Failed to start services: {result.stderr}")

        except Exception as e:
            self.output_text.append(f"❌ Error starting services: {e}")

        finally:
            self.start_services_button.setEnabled(True)

    def _stop_services(self) -> None:
        """Stop FLASH-TV services."""
        self.stop_services_button.setEnabled(False)
        self.output_text.append("🛑 Stopping FLASH-TV services...")

        try:
            # Run stop services script
            result = subprocess.run(
                ["bash", "../services/stop_services.sh"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="../services",
            )

            if result.returncode == 0:
                self.output_text.append("✅ Services stopped successfully")
                self.output_text.append(result.stdout)
                self._refresh_service_status()
            else:
                self.output_text.append(f"❌ Failed to stop services: {result.stderr}")

        except Exception as e:
            self.output_text.append(f"❌ Error stopping services: {e}")

        finally:
            self.stop_services_button.setEnabled(True)

    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click."""
        if self.is_completed():
            self.request_next_step.emit()

    def activate_step(self) -> None:
        """Activate the service configuration step."""
        super().activate_step()

        # Refresh service status on activation
        self._refresh_service_status()

    def update_ui(self) -> None:
        """Update UI elements periodically."""
        super().update_ui()

        # Check service configuration process status
        process_info = self.state.get_process("service_configuration")
        if process_info:
            if not process_info.is_running():
                status = process_info.get_status()

                if status.value == "completed":
                    self.output_text.append("\\n✅ Service configuration completed!")
                    self.output_text.append("Refreshing service status...")
                    self._refresh_service_status()
                    self.update_status(StepStatus.USER_ACTION_REQUIRED)
                else:
                    self.output_text.append("\\n❌ Service configuration failed")
                    self.output_text.append(
                        f"Exit code: {process_info.process.returncode}"
                    )
                    self.update_status(StepStatus.FAILED)

                self.configure_button.setEnabled(True)
                # Remove completed process
                self.state.remove_process("service_configuration")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Service configuration step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
