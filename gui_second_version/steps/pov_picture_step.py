"""POV picture step implementation using new framework patterns."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from utils.ui_factory import ButtonStyle


class POVPictureStep(WizardStep):
    """Step 7: Capture Point of View (POV) Picture using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the POV picture UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Overview section using UI factory
        overview_section = self._create_overview_section()
        main_layout.addWidget(overview_section)

        # Top row using UI factory
        top_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Instructions and actions sections
        instructions_section = self._create_instructions_section()
        actions_section = self._create_actions_section()

        top_row.addWidget(instructions_section, 3)  # 60% width
        top_row.addWidget(actions_section, 2)  # 40% width

        main_layout.addLayout(top_row)

        # Middle row using UI factory
        middle_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Status and guidelines sections
        status_section = self._create_status_section()
        guidelines_section = self._create_guidelines_section()

        middle_row.addWidget(status_section, 3)  # 60% width
        middle_row.addWidget(guidelines_section, 2)  # 40% width

        main_layout.addLayout(middle_row, 1)  # Give it stretch

        # Continue button using UI factory
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        return content

    def _create_overview_section(self) -> QWidget:
        """Create the overview section using UI factory."""
        overview_group, overview_layout = self.ui_factory.create_group_box(
            "POV Picture Overview"
        )

        overview_text = self.ui_factory.create_label(
            "Now that the camera is positioned correctly, take a "
            "Point of View (POV) picture to document the camera's "
            "perspective of the viewing area. This picture shows exactly what "
            "the FLASH-TV camera will see during operation."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_instructions_section(self) -> QWidget:
        """Create the instructions section using UI factory."""
        instructions_group, instructions_layout = self.ui_factory.create_group_box(
            "POV Picture Instructions"
        )

        instructions = self.ui_factory.create_label(
            "1. Have the target child sit in their usual TV viewing position\n"
            "2. Turn on the TV to typical viewing content\n"
            "3. Take a picture FROM THE CAMERA'S POSITION\n"
            "4. The picture should show what the camera sees\n"
            "5. Include: TV screen, child's seating area, room lighting"
        )
        instructions_layout.addWidget(instructions)
        instructions_layout.addStretch()

        return instructions_group

    def _create_actions_section(self) -> QWidget:
        """Create the camera actions section using UI factory."""
        actions_group, actions_layout = self.ui_factory.create_group_box(
            "Take POV Picture"
        )

        self.launch_camera_button = self.ui_factory.create_action_button(
            "📷 Open Camera Application",
            callback=self._launch_camera_app,
            style=ButtonStyle.PRIMARY,
            height=40,
        )
        actions_layout.addWidget(self.launch_camera_button)

        or_label = self.ui_factory.create_label("OR")
        or_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        actions_layout.addWidget(or_label)

        self.use_phone_button = self.ui_factory.create_action_button(
            "📱 I'll Use My Phone Camera",
            callback=self._use_phone_camera,
            style=ButtonStyle.SECONDARY,
            height=40,
        )
        actions_layout.addWidget(self.use_phone_button)

        actions_layout.addStretch()

        return actions_group

    def _create_status_section(self) -> QWidget:
        """Create the picture status section using UI factory."""
        status_group, status_layout = self.ui_factory.create_group_box(
            "POV Picture Status"
        )

        self.picture_status_label = self.ui_factory.create_status_label(
            "📷 POV picture not yet captured", status_type="info"
        )
        status_layout.addWidget(self.picture_status_label)

        self.picture_path_label = self.ui_factory.create_label("")
        status_layout.addWidget(self.picture_path_label)

        # Button layout for picture actions
        button_layout = self.ui_factory.create_horizontal_layout(spacing=8)

        self.select_picture_button = self.ui_factory.create_action_button(
            "Select POV Picture File",
            callback=self._select_picture_file,
            style=ButtonStyle.PRIMARY,
            height=30,
        )
        button_layout.addWidget(self.select_picture_button)

        self.verify_picture_button = self.ui_factory.create_action_button(
            "Verify Picture Quality",
            callback=self._verify_picture,
            style=ButtonStyle.SUCCESS,
            height=30,
            enabled=False,
        )
        button_layout.addWidget(self.verify_picture_button)

        status_layout.addLayout(button_layout)
        status_layout.addStretch()

        return status_group

    def _create_guidelines_section(self) -> QWidget:
        """Create the guidelines section using UI factory."""
        guidelines_group, guidelines_layout = self.ui_factory.create_group_box(
            "POV Picture Quality Guidelines"
        )

        guidelines_text = self.ui_factory.create_label(
            "✓ Child's face is visible in typical viewing position\n"
            "✓ TV screen is in frame\n"
            "✓ Lighting conditions represent typical viewing\n"
            "✓ No major obstructions between camera and child\n"
            "✓ Picture is clear and not blurry"
        )
        guidelines_layout.addWidget(guidelines_text)

        self.help_button = self.ui_factory.create_action_button(
            "❓ POV Picture Help",
            callback=self._show_pov_help,
            style=ButtonStyle.SECONDARY,
            height=30,
        )
        guidelines_layout.addWidget(self.help_button)

        guidelines_layout.addStretch()

        return guidelines_group

    def _create_continue_section(self):
        """Create the continue button section using UI factory."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text="POV Picture Complete - Continue"
        )

        return button_layout

    @handle_step_error
    def _launch_camera_app(self, checked: bool = False) -> None:
        """Launch camera application with comprehensive error handling."""
        try:
            self.logger.info("Launching camera application for POV picture")

            # Launch camera using process runner
            result = self.process_runner.run_command(["cheese"], timeout_ms=5000)

            if result and result.returncode == 0:
                self.logger.info("Camera application launched successfully")
                QMessageBox.information(
                    self,
                    "Camera Launched",
                    "Camera application launched.\n\n"
                    "1. Position yourself at the camera location\n"
                    "2. Take a picture of the viewing area\n"
                    "3. Save the picture\n"
                    "4. Click 'Select POV Picture File' to choose it",
                )
            else:
                error_msg = result.stderr if result else "Command failed"
                self.logger.error(f"Camera app launch failed: {error_msg}")
                raise FlashTVError(
                    f"Camera application launch failed: {error_msg}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try using phone camera instead",
                )

        except Exception as e:
            self.logger.error(f"Error launching camera app: {e}")
            QMessageBox.warning(
                self,
                "Camera Error",
                f"Could not launch camera app: {e}\n\n"
                "Please use another method to take the POV picture.",
            )
            raise

    @handle_step_error
    def _use_phone_camera(self, checked: bool = False) -> None:
        """Instructions for using phone camera with logging."""
        try:
            self.logger.info("User chose to use phone camera for POV picture")

            QMessageBox.information(
                self,
                "Using Phone Camera",
                "To use your phone camera:\n\n"
                "1. Stand at the FLASH-TV camera position\n"
                "2. Hold phone at same height/angle as camera\n"
                "3. Take picture showing child's viewing area\n"
                "4. Transfer picture to this computer\n"
                "5. Click 'Select POV Picture File' to choose it\n\n"
                "Tip: Email or USB transfer work well",
            )

        except Exception as e:
            self.logger.error(f"Error showing phone camera instructions: {e}")
            raise FlashTVError(
                f"Failed to show phone camera instructions: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try using the camera application instead",
            )

    @handle_step_error
    def _select_picture_file(self, checked: bool = False) -> None:
        """Select POV picture file with comprehensive error handling."""
        try:
            data_path = self.state.get_user_input("data_path", "")
            start_dir = data_path if data_path else str(Path.home())

            self.logger.info(f"Opening file dialog from directory: {start_dir}")

            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select POV Picture",
                start_dir,
                "Image Files (*.png *.jpg *.jpeg *.bmp)",
            )

            if file_path:
                self.logger.info(f"Selected POV picture file: {file_path}")

                # Validate file exists and is readable
                if not os.path.exists(file_path):
                    raise FlashTVError(
                        f"Selected file does not exist: {file_path}",
                        ErrorType.FILE_ERROR,
                        recovery_action="Select a different file",
                    )

                # Save picture path
                self.state.set_user_input("pov_picture_path", file_path)

                # Copy to participant folder
                participant_id = self.state.get_user_input("participant_id", "")
                if participant_id and data_path:
                    try:
                        dest_dir = Path(data_path) / f"{participant_id}_data"
                        dest_dir.mkdir(parents=True, exist_ok=True)

                        dest_path = dest_dir / f"{participant_id}_pov_picture.jpg"

                        self.logger.info(f"Copying POV picture to: {dest_path}")
                        shutil.copy2(file_path, dest_path)

                        self.picture_status_label.setText(
                            "✅ POV picture captured and saved"
                        )
                        self.picture_status_label.setStyleSheet(
                            f"color: {self.config.success_color}; font-weight: bold; padding: 10px;"
                        )
                        self.picture_path_label.setText(f"Saved to: {dest_path}")

                        # Update state with final path
                        self.state.set_user_input(
                            "pov_picture_final_path", str(dest_path)
                        )

                        self.logger.info("POV picture copied successfully")

                    except Exception as e:
                        self.logger.error(f"Error copying POV picture: {e}")
                        QMessageBox.warning(
                            self,
                            "Save Error",
                            f"Could not save picture to participant folder: {e}",
                        )
                        # Still allow verification of original file
                        self.picture_status_label.setText("✅ POV picture selected")
                        self.picture_path_label.setText(f"File: {file_path}")
                else:
                    self.picture_status_label.setText("✅ POV picture selected")
                    self.picture_path_label.setText(f"File: {file_path}")
                    self.logger.info(
                        "POV picture selected (no participant folder copy)"
                    )

                self.verify_picture_button.setEnabled(True)

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)
            else:
                self.logger.info("User cancelled file selection")

        except Exception as e:
            self.logger.error(f"Error selecting POV picture file: {e}")
            raise FlashTVError(
                f"Failed to select POV picture: {e}",
                ErrorType.FILE_ERROR,
                recovery_action="Try selecting the file again",
            )

    @handle_step_error
    def _verify_picture(self) -> None:
        """Verify picture quality with comprehensive validation."""
        try:
            picture_path = self.state.get_user_input("pov_picture_path", "")

            if not picture_path or not os.path.exists(picture_path):
                self.logger.warning("No POV picture available for verification")
                QMessageBox.warning(self, "No Picture", "No POV picture selected")
                return

            self.logger.info(f"Verifying POV picture: {picture_path}")

            # In a real implementation, could display the image for review
            reply = QMessageBox.question(
                self,
                "Verify POV Picture",
                "Please confirm the POV picture meets these criteria:\n\n"
                "✓ Shows child's typical viewing position\n"
                "✓ TV screen is visible in frame\n"
                "✓ Adequate lighting to see faces\n"
                "✓ Camera view is unobstructed\n"
                "✓ Picture quality is clear\n\n"
                "Does the picture meet all criteria?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("User verified POV picture quality")

                self.state.set_user_input("pov_picture_verified", True)
                self.state.set_user_input("pov_picture_complete", True)

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)

                QMessageBox.information(
                    self, "Picture Verified", "POV picture verified successfully!"
                )
            else:
                self.logger.info("User rejected POV picture quality")
                QMessageBox.information(
                    self,
                    "Retake Picture",
                    "Please retake the POV picture to meet all criteria.",
                )

        except Exception as e:
            self.logger.error(f"Error during picture verification: {e}")
            raise FlashTVError(
                f"Failed to verify POV picture: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Try verifying the picture again",
            )

    @handle_step_error
    def _show_pov_help(self, checked: bool = False) -> None:
        """Show POV picture help with logging."""
        try:
            self.logger.info("Showing POV picture help dialog")

            help_text = """POV Picture Guidelines:

Purpose: Documents what the FLASH-TV camera sees during operation

Key Requirements:
• Take picture FROM the camera's mounted position
• Include the target child's typical viewing area
• Show typical TV viewing conditions

Common Issues:
• Taking picture from wrong angle - stand at camera!
• Too dark - turn on typical room lighting
• Child not in frame - have them sit normally
• TV not visible - adjust camera angle if needed

The POV picture helps researchers understand:
• Camera coverage of viewing area
• Typical viewing distances
• Lighting conditions
• Potential obstructions"""

            QMessageBox.information(self, "POV Picture Help", help_text)

        except Exception as e:
            self.logger.error(f"Error showing POV help: {e}")
            raise FlashTVError(
                f"Failed to show help dialog: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try clicking help again",
            )

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            if self.state.get_user_input("pov_picture_verified", False):
                picture_path = self.state.get_user_input("pov_picture_path", "")
                self.logger.info(
                    f"POV picture step completed with file: {picture_path}"
                )

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but POV picture not verified")

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete POV picture step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Verify the picture first",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the POV picture step with state restoration."""
        super().activate_step()

        self.logger.info("POV picture step activated")

        # Check if picture already captured
        pov_path = self.state.get_user_input("pov_picture_path", "")
        if pov_path and os.path.exists(pov_path):
            self.picture_status_label.setText("✅ POV picture previously captured")
            self.picture_path_label.setText(f"File: {pov_path}")
            self.verify_picture_button.setEnabled(True)
            self.logger.info(f"Restored previous POV picture: {pov_path}")

            if self.state.get_user_input("pov_picture_verified", False):
                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)
                self.logger.info("POV picture already verified, step completed")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("POV picture step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
