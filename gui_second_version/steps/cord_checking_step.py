"""Cord checking step implementation."""

from __future__ import annotations

from core import WizardStep
from models import StepStatus
from models.state_keys import UserInputKey
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QWidget
from utils.ui_factory import ButtonStyle


class CordCheckingStep(WizardStep):
    """Step 10: Check All Cords and Connections."""

    def create_content_widget(self) -> QWidget:
        """Create the cord checking UI."""
        content = QWidget()
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Overview
        overview_group, overview_layout = self.ui_factory.create_group_box(
            "Connection Verification Overview"
        )
        overview_text = self.ui_factory.create_label(
            "Before completing the setup, please verify all physical "
            "connections are secure to ensure reliable operation "
            "during the study period. Check each connection carefully."
        )
        overview_layout.addWidget(overview_text)
        main_layout.addWidget(overview_group)

        # Power Connections
        power_group, power_layout = self.ui_factory.create_group_box(
            "Power Connections"
        )
        self.flash_power_check = self.ui_factory.create_checkbox(
            "FLASH-TV device power cord connected and red RTC light on"
        )
        self.camera_power_check = self.ui_factory.create_checkbox(
            "Camera USB cord securely connected"
        )
        self.tv_power_check = self.ui_factory.create_checkbox(
            "TV power cord connected to smart plug"
        )
        self.smart_plug_check = self.ui_factory.create_checkbox(
            "Smart plug connected to outlet"
        )
        power_layout.addWidget(self.flash_power_check)
        power_layout.addWidget(self.camera_power_check)
        power_layout.addWidget(self.tv_power_check)
        power_layout.addWidget(self.smart_plug_check)
        power_layout.addStretch()
        main_layout.addWidget(power_group)

        # Middle row
        middle_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Physical Security
        security_group, security_layout = self.ui_factory.create_group_box(
            "Physical Security"
        )
        self.camera_mount_check = self.ui_factory.create_checkbox(
            "Camera mount is secure and stable"
        )
        self.cable_management_check = self.ui_factory.create_checkbox(
            "Cables won't be disturbed too much"
        )
        self.device_position_check = self.ui_factory.create_checkbox(
            "FLASH-TV device is in safe location"
        )
        security_layout.addWidget(self.camera_mount_check)
        security_layout.addWidget(self.cable_management_check)
        security_layout.addWidget(self.device_position_check)
        security_layout.addStretch()

        # Important Reminders
        instructions_group, instructions_layout = self.ui_factory.create_group_box(
            "Important Reminders"
        )
        instructions_text = self.ui_factory.create_label(
            "Ensure cables won't be accidentally unplugged during study\n"
            "Confirm family knows NOT to unplug camera during study\n"
            "Make sure power strips have room for all devices"
        )
        instructions_layout.addWidget(instructions_text)
        instructions_layout.addStretch()

        middle_row.addWidget(security_group, 1)
        middle_row.addWidget(instructions_group, 1)
        main_layout.addLayout(middle_row)

        # Connect checkboxes
        all_checks = [
            self.flash_power_check,
            self.camera_power_check,
            self.tv_power_check,
            self.smart_plug_check,
            self.camera_mount_check,
            self.cable_management_check,
            self.device_position_check,
        ]
        for check in all_checks:
            check.stateChanged.connect(self._update_progress)

        # Bottom row
        bottom_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Notes
        notes_group, notes_layout = self.ui_factory.create_group_box("Additional Notes")
        self.notes_text = self.ui_factory.create_text_area(
            placeholder="Note any special cord arrangements, concerns, or family instructions..."
        )
        notes_layout.addWidget(self.notes_text)

        # Progress
        progress_group, progress_layout = self.ui_factory.create_group_box(
            "Verification Progress"
        )
        self.progress_label = self.ui_factory.create_label(
            "Complete all connection checks to continue"
        )
        self.progress_label.setStyleSheet("font-weight: bold; padding: 5px;")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addStretch()

        bottom_row.addWidget(notes_group, 3)
        bottom_row.addWidget(progress_group, 2)
        main_layout.addLayout(bottom_row)

        # Continue button
        button_layout = self.ui_factory.create_horizontal_layout()
        self.continue_button = self.ui_factory.create_action_button(
            "All Connections Verified - Continue",
            callback=self._on_continue_clicked,
            style=ButtonStyle.SUCCESS,
            height=30,
            enabled=False,
        )
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
            self.camera_mount_check.isChecked(),
            self.cable_management_check.isChecked(),
            self.device_position_check.isChecked(),
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
        notes = self.notes_text.toPlainText().strip()
        if notes:
            self.state.set_user_input(UserInputKey.CORD_CHECKING_NOTES, notes)
            self._save_notes_to_file("Cord Checking", notes)

        self.state.set_user_input(UserInputKey.CORDS_VERIFIED, True)
        self.request_next_step.emit()

    def activate_step(self) -> None:
        """Activate the cord checking step."""
        super().activate_step()

        saved_notes = self.state.get_user_input(UserInputKey.CORD_CHECKING_NOTES, "")
        if saved_notes:
            self.notes_text.setText(saved_notes)

        if self.state.get_user_input(UserInputKey.CORDS_VERIFIED, False):
            checks = [
                self.flash_power_check,
                self.camera_power_check,
                self.tv_power_check,
                self.smart_plug_check,
                self.camera_mount_check,
                self.cable_management_check,
                self.device_position_check,
            ]
            for check in checks:
                check.setChecked(True)
            self._update_progress()
            self.logger.info("Restored cord checking completion state")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            if self.state_manager:
                self.state_manager.save_state(self.state)
            self.logger.info("Cord checking step cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
