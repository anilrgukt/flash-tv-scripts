"""POV picture step implementation using new framework patterns."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QMessageBox, QFileDialog, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

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

        # Main content row
        content_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Left column: Instructions
        instructions_section = self._create_instructions_section()
        content_row.addWidget(instructions_section, 2)  # 40% width

        # Right column: Actions and Status combined
        right_column = self.ui_factory.create_vertical_layout(spacing=8)
        
        # Actions section at top of right column
        actions_section = self._create_actions_section()
        right_column.addWidget(actions_section)
        
        # Status section directly below actions
        status_section = self._create_status_section()
        right_column.addWidget(status_section, 1)  # Give it stretch
        
        content_row.addLayout(right_column, 3)  # 60% width

        main_layout.addLayout(content_row, 1)  # Give it stretch

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
            "1. Make sure NO PEOPLE are in the room at all\n"
            "2. Take a picture FROM THE TV'S PERSPECTIVE\n"
            "3. Picture shows what the TV 'sees' - the room/couch area\n"
            "4. The child's face should NOT be visible\n"
            "5. The TV screen should NOT be in the picture\n"
            "6. Shows the viewing area from TV's point of view"
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

        self.use_ipad_button = self.ui_factory.create_action_button(
            "📱 I'll Use My iPad Camera",
            callback=self._use_ipad_camera,
            style=ButtonStyle.SECONDARY,
            height=40,
        )
        actions_layout.addWidget(self.use_ipad_button)

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
        
        # Add image preview label
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setStyleSheet(
            "border: 2px solid #ccc; padding: 10px; background-color: #f5f5f5; border-radius: 4px;"
        )
        self.image_preview.setMinimumHeight(200)
        self.image_preview.setMaximumHeight(400)
        self.image_preview.setText("No image selected")
        status_layout.addWidget(self.image_preview, 1)

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
            "✓ NO PEOPLE are visible anywhere in the picture\n"
            "✓ Child's face is NOT visible\n"
            "✓ TV screen is NOT in the picture\n"
            "✓ Shows room/couch area from TV's perspective\n"
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

            # Launch camera using process runner (no timeout for GUI app)
            result = self.process_runner.run_command(["cheese"])

            if result and result.returncode == 0:
                self.logger.info("Camera application launched successfully")
                QMessageBox.information(
                    self,
                    "Camera Launched",
                    "Camera application launched.\n\n"
                    "1. Position yourself at the TV location\n"
                    "2. Make sure NO PEOPLE are in the room at all\n"
                    "3. Take picture FROM TV's perspective of the room\n"
                    "4. Child's face should NOT be visible\n"
                    "5. TV screen should NOT be in the picture\n"
                    "6. Save the picture\n"
                    "7. Click 'Select POV Picture File' to choose it",
                )
            else:
                error_msg = result.stderr if result else "Command failed"
                self.logger.error(f"Camera app launch failed: {error_msg}")
                raise FlashTVError(
                    f"Camera application launch failed: {error_msg}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try using iPad camera instead",
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
    def _use_ipad_camera(self, checked: bool = False) -> None:
        """Instructions for using iPad camera with logging."""
        try:
            self.logger.info("User chose to use iPad camera for POV picture")

            QMessageBox.information(
                self,
                "Using iPad Camera",
                "To use your iPad camera:\n\n"
                "1. Stand at the TV's position (NOT the camera)\n"
                "2. Make sure NO PEOPLE are in the room at all\n"
                "3. Take picture FROM TV's perspective of the room\n"
                "4. Child's face should NOT be visible\n"
                "5. TV screen should NOT be in the picture\n"
                "6. Shows what the TV 'sees' - empty room/couch area\n"
                "7. Transfer picture to this computer\n"
                "8. Click 'Select POV Picture File' to choose it\n\n"
                "Tip: Email or USB transfer work well",
            )

        except Exception as e:
            self.logger.error(f"Error showing iPad camera instructions: {e}")
            raise FlashTVError(
                f"Failed to show iPad camera instructions: {e}",
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
                
                # Load and display the image preview
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    # Scale image to fit while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(
                        600, 400,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.image_preview.setPixmap(scaled_pixmap)
                else:
                    self.image_preview.setText("Error loading image")

                # Copy to participant folder
                participant_id = self.state.get_user_input("participant_id", "")
                device_id = self.state.get_user_input("device_id", "")
                if participant_id and data_path:
                    try:
                        # Data path already includes participant and device ID
                        dest_dir = Path(data_path)
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Include device_id in filename if available
                        if device_id:
                            dest_path = dest_dir / f"{participant_id}{device_id}_pov_picture.jpg"
                        else:
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
    def _verify_picture(self, checked: bool = False) -> None:
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
                "✓ NO PEOPLE are visible anywhere\n"
                "✓ Child's face is NOT visible\n"
                "✓ TV screen is NOT in the picture\n"
                "✓ Shows room/couch area from TV's perspective\n"
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

Purpose: Documents what the TV 'sees' when looking at the viewing area

Key Requirements:
• Take picture FROM the TV's position (NOT the camera!)
• NO PEOPLE should be visible anywhere in the picture
• Child's face must NOT be in the picture
• TV screen should NOT be in the picture  
• Shows the empty room/couch area from TV's perspective
• Picture is FROM TV looking at where people sit

CRITICAL: The room must be completely empty of people!

Common Issues:
• Taking picture from wrong location - stand at TV, not camera!
• Including people in the picture - room must be completely empty
• Showing child's face - this violates privacy requirements  
• Including TV screen - picture is FROM TV looking out at room
• Too dark - turn on typical room lighting

The POV picture helps researchers understand:
• What the TV 'sees' when looking at the empty viewing area
• Room layout and seating arrangements (without people)
• Lighting conditions
• Viewing area setup from TV's perspective"""

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
