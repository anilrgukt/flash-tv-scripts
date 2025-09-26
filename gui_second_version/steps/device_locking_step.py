"""Device locking step implementation."""

from __future__ import annotations

import subprocess

from core import WizardStep
from models import StepStatus
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DeviceLockingStep(WizardStep):
    """Step 12: Device Locking and Final Setup."""

    def create_content_widget(self) -> QWidget:
        """Create the device locking UI."""
        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)

        # Overview (full width at top)
        overview_group = QGroupBox("Device Locking and Final Setup")
        overview_layout = QVBoxLayout(overview_group)
        overview_layout.setContentsMargins(8, 8, 8, 8)

        overview_text = QLabel(
            "Final step: Lock the device to prevent accidental changes "
            "during the study period. This ensures the FLASH-TV system "
            "runs uninterrupted. Complete the verification checklist before locking."
        )
        overview_text.setWordWrap(True)
        overview_layout.addWidget(overview_text)

        main_layout.addWidget(overview_group)

        # Top row: Verification and Lock Options side by side
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # Left side: Pre-Lock Verification
        verification_group = QGroupBox("Pre-Device Lock Verification")
        verification_layout = QVBoxLayout(verification_group)
        verification_layout.setContentsMargins(8, 8, 8, 8)

        verification_text = QLabel("Before locking the device, verify that:\n• All setup steps are complete\n• FLASH-TV system is running properly\n")
        verification_layout.addWidget(verification_text)

        verification_layout.addSpacing(10)

        self.setup_complete_check = QCheckBox("✓ All setup steps verified complete")
        self.services_running_check = QCheckBox("✓ FLASH-TV services are running properly")

        verification_layout.addWidget(self.setup_complete_check)
        verification_layout.addWidget(self.services_running_check)
        verification_layout.addStretch()

        # Connect checkboxes to progress update
        self.setup_complete_check.stateChanged.connect(self._update_lock_readiness)
        self.services_running_check.stateChanged.connect(self._update_lock_readiness)
        # Right side: Device Lock Options
        lock_group = QGroupBox("Device Locking Options")
        lock_layout = QVBoxLayout(lock_group)
        lock_layout.setContentsMargins(8, 8, 8, 8)

        lock_info = QLabel("Choose how to secure the system during the study period:")
        lock_info.setWordWrap(True)
        lock_layout.addWidget(lock_info)

        lock_layout.addSpacing(10)

        # Lock options
        self.lock_device_button = QPushButton("🔒 Lock Device Now")
        self.lock_device_button.setFixedHeight(35)
        self.lock_device_button.clicked.connect(self._lock_device)
        self.lock_device_button.setEnabled(False)
        lock_layout.addWidget(self.lock_device_button)

        self.auto_lock_button = QPushButton("⏰ Enable Auto-Lock (5 minutes) for device")
        self.auto_lock_button.setFixedHeight(35)
        self.auto_lock_button.clicked.connect(self._enable_auto_lock)
        self.auto_lock_button.setEnabled(False)
        lock_layout.addWidget(self.auto_lock_button)

        self.manual_lock_button = QPushButton("📝 Manual Lock Instructions")
        self.manual_lock_button.setFixedHeight(35)
        self.manual_lock_button.clicked.connect(self._show_manual_instructions)
        self.manual_lock_button.setEnabled(False)
        lock_layout.addWidget(self.manual_lock_button)

        lock_layout.addStretch()

        # Add both to top row
        top_row.addWidget(verification_group, 3)  # 60% width
        top_row.addWidget(lock_group, 2)  # 40% width

        main_layout.addLayout(top_row)

        # Final Instructions section
        final_group = QGroupBox("Final Instructions for Participant")
        final_layout = QVBoxLayout(final_group)
        final_layout.setContentsMargins(8, 8, 8, 8)

        final_instructions = QLabel(
            "Please inform the participant:\n"
            "• FLASH-TV system is now active and recording\n"
            "• Device is locked to prevent accidental changes\n"
            "• DO NOT unlock device during study period\n"
            "• Contact research team if any technical issues\n"
            "• Normal TV viewing can continue as usual"
        )
        final_instructions.setWordWrap(True)
        final_layout.addWidget(final_instructions)

        final_layout.addSpacing(10)

        # Custom instructions text area with proper sizing
        instructions_label = QLabel("Additional Notes for Participant:")
        instructions_label.setStyleSheet("font-weight: bold;")
        final_layout.addWidget(instructions_label)

        self.instructions_text = QTextEdit()
        self.instructions_text.setMaximumHeight(80)  # Limit height to prevent excessive space
        self.instructions_text.setMinimumHeight(60)  # Ensure minimum usable height
        self.instructions_text.setPlaceholderText("Add any specific notes for this participant...")
        final_layout.addWidget(self.instructions_text)

        final_layout.addStretch()  # Add stretch to push content to top

        main_layout.addWidget(final_group)

        # Continue button
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 5, 0, 0)

        self.continue_button = QPushButton("Setup Complete - Device Locked")
        self.continue_button.setFixedHeight(30)
        self.continue_button.clicked.connect(self._on_continue_clicked)
        self.continue_button.setEnabled(False)
        button_layout.addStretch()
        button_layout.addWidget(self.continue_button)

        main_layout.addLayout(button_layout)

        return content

    def _update_lock_readiness(self) -> None:
        """Update lock button availability based on verification."""
        all_verified = self.setup_complete_check.isChecked() and self.services_running_check.isChecked()

        self.lock_device_button.setEnabled(all_verified)
        self.auto_lock_button.setEnabled(all_verified)
        self.manual_lock_button.setEnabled(all_verified)

        if all_verified:
            self.update_status(StepStatus.USER_ACTION_REQUIRED)

    def _lock_device(self) -> None:
        """Lock the device immediately."""
        reply = QMessageBox.question(
            self,
            "Lock Device",
            "This will lock the device immediately.\n\nLock device now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Lock the device using process runner
                result = self.process_runner.run_command(["loginctl", "lock-session"], timeout_ms=5000)

                if result and result.returncode == 0:
                    self._mark_setup_complete()
                else:
                    # Try alternative method
                    result = self.process_runner.run_command(["gnome-screensaver-command", "--lock"], timeout_ms=5000)
                    if result and result.returncode == 0:
                        self._mark_setup_complete()
                    else:
                        raise Exception("Device lock failed")

            except Exception as e:
                self.logger.warning(f"Device lock failed: {e}")
                QMessageBox.warning(
                    self,
                    "Lock Failed",
                    "Could not lock device automatically.\nPlease lock manually using system controls.",
                )

    def _enable_auto_lock(self) -> None:
        """Enable automatic device lock after 5 minutes."""
        try:
            # Set device to lock after 5 minutes of inactivity
            subprocess.run(
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.screensaver",
                    "lock-delay",
                    "uint32 300",
                ],
                check=True,
            )

            subprocess.run(
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.screensaver",
                    "lock-enabled",
                    "true",
                ],
                check=True,
            )

            QMessageBox.information(
                self,
                "Auto-Lock Enabled",
                "Device will automatically lock after 5 minutes of inactivity.\n\nThe system is now ready for the study period.",
            )

            self._mark_setup_complete()

        except subprocess.CalledProcessError:
            QMessageBox.warning(
                self,
                "Auto-Lock Failed",
                "Could not enable auto-lock.\nPlease configure manually or lock immediately.",
            )

    def _show_manual_instructions(self) -> None:
        """Show manual lock instructions."""
        instructions = """Manual Device Lock Instructions:

        1. Click top right power button on screen → Lock
        OR
        2. Super key → Type "lock" → Enter

        Important:
        • Lock device before leaving the location
        """

        QMessageBox.information(self, "Manual Lock Instructions", instructions)

        reply = QMessageBox.question(
            self,
            "Manual Lock Confirmation",
            "Will you lock the device manually before leaving?\n\nClick Yes to confirm setup is complete.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._mark_setup_complete()

    def _mark_setup_complete(self) -> None:
        """Mark the entire setup as complete."""
        # Save final instructions
        instructions = self.instructions_text.toPlainText().strip()
        if instructions:
            self.state.set_user_input("final_instructions", instructions)

        # Mark as complete
        self.state.set_user_input("device_locked", True)
        self.state.set_user_input("setup_complete", True)
        self.continue_button.setEnabled(True)
        self.update_status(StepStatus.COMPLETED)

    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click."""
        if self.state.get_user_input("device_locked", False):
            # This is the final step
            QMessageBox.information(
                self,
                "Setup Complete!",
                "FLASH-TV setup is now complete!\n\n"
                "The system is ready for data collection.\n"
                "Participant can resume normal TV viewing.\n\n"
                "Remember to lock the screen if not already done.",
            )
            self.request_next_step.emit()

    def activate_step(self) -> None:
        """Activate the device locking step."""
        super().activate_step()

        # Load any saved instructions
        saved_instructions = self.state.get_user_input("final_instructions", "")
        if saved_instructions:
            self.instructions_text.setText(saved_instructions)

        # Check if already completed
        if self.state.get_user_input("device_locked", False):
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)

            # Auto-check verification boxes
            self.setup_complete_check.setChecked(True)
            self.services_running_check.setChecked(True)

            self.logger.info("Restored device locking completion state")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Device locking step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
