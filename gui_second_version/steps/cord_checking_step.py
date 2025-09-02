"""Cord checking step implementation."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QGroupBox,
    QCheckBox,
    QTextEdit,
)

from core import WizardStep
from models import StepStatus


class CordCheckingStep(WizardStep):
    """Step 11: Check All Cords and Connections."""

    def create_content_widget(self) -> QWidget:
        """Create the cord checking UI."""
        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)

        # Overview (full width at top)
        overview_group = QGroupBox("Connection Verification Overview")
        overview_layout = QVBoxLayout(overview_group)
        overview_layout.setContentsMargins(8, 8, 8, 8)

        overview_text = QLabel(
            "Before completing the setup, let's verify all physical "
            "connections are secure to ensure reliable operation "
            "during the study period. Check each connection carefully."
        )
        overview_text.setWordWrap(True)
        overview_layout.addWidget(overview_text)

        main_layout.addWidget(overview_group)

        # Top row: Power and Data connections side by side
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # Left column: Power Connections
        power_group = QGroupBox("Power Connections")
        power_layout = QVBoxLayout(power_group)
        power_layout.setContentsMargins(8, 8, 8, 8)

        self.flash_power_check = QCheckBox(
            "✓ FLASH-TV device power cord connected and LED on"
        )
        self.camera_power_check = QCheckBox(
            "✓ Camera power/USB cord securely connected"
        )
        self.tv_power_check = QCheckBox("✓ TV power cord connected properly")
        self.smart_plug_check = QCheckBox("✓ Smart plug power connection verified")

        power_layout.addWidget(self.flash_power_check)
        power_layout.addWidget(self.camera_power_check)
        power_layout.addWidget(self.tv_power_check)
        power_layout.addWidget(self.smart_plug_check)
        power_layout.addStretch()

        # Right column: Data Connections
        data_group = QGroupBox("Data Connections")
        data_layout = QVBoxLayout(data_group)
        data_layout.setContentsMargins(8, 8, 8, 8)

        self.ethernet_check = QCheckBox("✓ Ethernet cable connected to FLASH-TV device")
        self.camera_data_check = QCheckBox(
            "✓ Camera USB data cable connected to FLASH-TV"
        )
        self.wifi_check = QCheckBox("✓ WiFi connection verified and stable")

        data_layout.addWidget(self.ethernet_check)
        data_layout.addWidget(self.camera_data_check)
        data_layout.addWidget(self.wifi_check)
        data_layout.addStretch()

        # Add both to top row
        top_row.addWidget(power_group, 1)
        top_row.addWidget(data_group, 1)

        main_layout.addLayout(top_row)

        # Middle row: Physical Security and Important Reminders
        middle_row = QHBoxLayout()
        middle_row.setSpacing(12)

        # Left side: Physical Security
        security_group = QGroupBox("Physical Security")
        security_layout = QVBoxLayout(security_group)
        security_layout.setContentsMargins(8, 8, 8, 8)

        self.camera_mount_check = QCheckBox("✓ Camera mount is secure and stable")
        self.cable_management_check = QCheckBox(
            "✓ Cables are organized and won't be disturbed"
        )
        self.device_position_check = QCheckBox(
            "✓ FLASH-TV device is in safe, ventilated location"
        )
        self.access_check = QCheckBox("✓ Family can access power buttons if needed")

        security_layout.addWidget(self.camera_mount_check)
        security_layout.addWidget(self.cable_management_check)
        security_layout.addWidget(self.device_position_check)
        security_layout.addWidget(self.access_check)
        security_layout.addStretch()

        # Right side: Important Reminders
        instructions_group = QGroupBox("Important Reminders")
        instructions_layout = QVBoxLayout(instructions_group)
        instructions_layout.setContentsMargins(8, 8, 8, 8)

        instructions_text = QLabel(
            "• Ensure cables won't be accidentally unplugged during study\n"
            "• Verify power surge protection if available\n"
            "• Check that ventilation around FLASH-TV device is adequate\n"
            "• Confirm family knows NOT to unplug camera during study\n"
            "• Make sure power strips have room for all devices"
        )
        instructions_text.setWordWrap(True)
        instructions_layout.addWidget(instructions_text)
        instructions_layout.addStretch()

        # Add both to middle row
        middle_row.addWidget(security_group, 1)
        middle_row.addWidget(instructions_group, 1)

        main_layout.addLayout(middle_row)

        # Connect all checkboxes to progress update
        all_checks = [
            self.flash_power_check,
            self.camera_power_check,
            self.tv_power_check,
            self.smart_plug_check,
            self.ethernet_check,
            self.camera_data_check,
            self.wifi_check,
            self.camera_mount_check,
            self.cable_management_check,
            self.device_position_check,
            self.access_check,
        ]

        for check in all_checks:
            check.stateChanged.connect(self._update_progress)

        # Bottom: Notes and Progress
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        # Left side: Additional Notes
        notes_group = QGroupBox("Additional Notes")
        notes_layout = QVBoxLayout(notes_group)
        notes_layout.setContentsMargins(8, 8, 8, 8)

        self.notes_text = QTextEdit()
        self.notes_text.setPlaceholderText(
            "Note any special cord arrangements, concerns, or family instructions..."
        )
        notes_layout.addWidget(self.notes_text)

        # Right side: Progress status
        progress_group = QGroupBox("Verification Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(8, 8, 8, 8)

        self.progress_label = QLabel("Complete all connection checks to continue")
        self.progress_label.setStyleSheet("font-weight: bold; padding: 5px;")
        self.progress_label.setWordWrap(True)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addStretch()

        # Add both to bottom row
        bottom_row.addWidget(notes_group, 3)  # 60% width
        bottom_row.addWidget(progress_group, 2)  # 40% width

        main_layout.addLayout(bottom_row)

        # Continue button
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 5, 0, 0)

        self.continue_button = QPushButton("All Connections Verified - Continue")
        self.continue_button.setFixedHeight(30)
        self.continue_button.clicked.connect(self._on_continue_clicked)
        self.continue_button.setEnabled(False)
        button_layout.addStretch()
        button_layout.addWidget(self.continue_button)

        main_layout.addLayout(button_layout)

        return content

    def _update_progress(self) -> None:
        """Update progress based on checkbox states."""
        checks = [
            self.flash_power_check.isChecked(),
            self.camera_power_check.isChecked(),
            self.tv_power_check.isChecked(),
            self.smart_plug_check.isChecked(),
            self.ethernet_check.isChecked(),
            self.camera_data_check.isChecked(),
            self.wifi_check.isChecked(),
            self.camera_mount_check.isChecked(),
            self.cable_management_check.isChecked(),
            self.device_position_check.isChecked(),
            self.access_check.isChecked(),
        ]

        completed = sum(checks)
        total = len(checks)

        if completed == total:
            self.progress_label.setText("✅ All connections verified!")
            self.progress_label.setStyleSheet(
                "color: green; font-weight: bold; padding: 10px;"
            )
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)
        else:
            self.progress_label.setText(
                f"Progress: {completed}/{total} connections verified"
            )
            self.progress_label.setStyleSheet("font-weight: bold; padding: 10px;")
            self.continue_button.setEnabled(False)
            self.update_status(StepStatus.USER_ACTION_REQUIRED)

    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click."""
        # Save notes if any
        notes = self.notes_text.toPlainText().strip()
        if notes:
            self.state.set_user_input("cord_checking_notes", notes)

        # Mark cord checking as complete
        self.state.set_user_input("cords_verified", True)
        self.request_next_step.emit()

    def activate_step(self) -> None:
        """Activate the cord checking step."""
        super().activate_step()

        # Load any saved notes
        saved_notes = self.state.get_user_input("cord_checking_notes", "")
        if saved_notes:
            self.notes_text.setText(saved_notes)

        # Check if already completed
        if self.state.get_user_input("cords_verified", False):
            # Auto-check all boxes if previously completed
            checks = [
                self.flash_power_check,
                self.camera_power_check,
                self.tv_power_check,
                self.smart_plug_check,
                self.ethernet_check,
                self.camera_data_check,
                self.wifi_check,
                self.camera_mount_check,
                self.cable_management_check,
                self.device_position_check,
                self.access_check,
            ]

            for check in checks:
                check.setChecked(True)

            self._update_progress()
            self.logger.info("Restored cord checking completion state")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Cord checking step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
