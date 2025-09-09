"""POV picture step implementation with new iPad workflow."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from utils.ui_factory import ButtonStyle


class POVPictureStep(WizardStep):
    """Step 7: POV Picture with iPad workflow - cheese app + fullscreen display."""

    # Signals for process monitoring
    cheese_closed = pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Process monitoring
        self.cheese_process: Optional[subprocess.Popen] = None
        self.image_viewer_process: Optional[subprocess.Popen] = None
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_cheese_process)
        
        # State tracking
        self.temp_image_path: Optional[str] = None
        self.workflow_step = "initial"  # initial -> cheese_running -> image_found -> fullscreen -> confirmed -> cleanup

    def create_content_widget(self) -> QWidget:
        """Create the POV picture UI."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Overview section
        overview_section = self._create_overview_section()
        main_layout.addWidget(overview_section)

        # Main content row
        content_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Left column: Instructions
        instructions_section = self._create_instructions_section()
        content_row.addWidget(instructions_section, 2)

        # Right column: Actions and Status
        right_column = self.ui_factory.create_vertical_layout(spacing=8)
        
        actions_section = self._create_actions_section()
        right_column.addWidget(actions_section)
        
        status_section = self._create_status_section()
        right_column.addWidget(status_section, 1)
        
        content_row.addLayout(right_column, 3)

        main_layout.addLayout(content_row, 1)

        # Continue button
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        return content

    def _create_overview_section(self) -> QWidget:
        """Create the overview section."""
        overview_group, overview_layout = self.ui_factory.create_group_box(
            "POV Picture Overview"
        )

        overview_text = self.ui_factory.create_label(
            "Now that the camera is positioned correctly, take a "
            "Point of View (POV) picture to document the camera's "
            "perspective. This workflow uses your computer's camera app "
            "and then displays the picture fullscreen for you to photograph "
            "with your iPad."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_instructions_section(self) -> QWidget:
        """Create the instructions section."""
        instructions_group, instructions_layout = self.ui_factory.create_group_box(
            "POV Picture Workflow"
        )

        instructions = self.ui_factory.create_label(
            "NEW WORKFLOW:\n\n"
            "1. Click 'Open Camera Application' to launch cheese\n"
            "2. Position yourself at the TV location\n"
            "3. Make sure NO PEOPLE are in the room at all\n"
            "4. Take picture FROM TV's perspective of the room\n"
            "5. Close the camera app after taking the picture\n"
            "6. The picture will automatically display fullscreen\n"
            "7. Use your iPad to photograph the computer screen\n"
            "8. Confirm in the GUI that you took the iPad picture\n"
            "9. The system will automatically clean up\n\n"
            "IMPORTANT: Child's face should NOT be visible\n"
            "The TV screen should NOT be in the picture"
        )
        instructions_layout.addWidget(instructions)
        instructions_layout.addStretch()

        return instructions_group

    def _create_actions_section(self) -> QWidget:
        """Create the camera actions section."""
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

        self.help_button = self.ui_factory.create_action_button(
            "❓ POV Picture Help",
            callback=self._show_pov_help,
            style=ButtonStyle.SECONDARY,
            height=30,
        )
        actions_layout.addWidget(self.help_button)

        actions_layout.addStretch()

        return actions_group

    def _create_status_section(self) -> QWidget:
        """Create the status section."""
        status_group, status_layout = self.ui_factory.create_group_box(
            "Workflow Status"
        )

        self.workflow_status_label = self.ui_factory.create_status_label(
            "📷 Ready to start POV picture workflow", status_type="info"
        )
        status_layout.addWidget(self.workflow_status_label)

        self.step_details_label = self.ui_factory.create_label(
            "Click 'Open Camera Application' to begin"
        )
        status_layout.addWidget(self.step_details_label)
        
        status_layout.addStretch()

        return status_group

    def _create_continue_section(self):
        """Create the continue button section."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text="POV Picture Complete - Continue"
        )
        
        # Initially disabled until workflow complete
        self.continue_button.setEnabled(False)

        return button_layout

    @handle_step_error
    def _launch_camera_app(self, checked: bool = False) -> None:
        """Launch cheese camera application and monitor it."""
        try:
            if self.workflow_step != "initial":
                QMessageBox.information(
                    self,
                    "Workflow In Progress",
                    f"Workflow is already in progress (step: {self.workflow_step})"
                )
                return
                
            self.logger.info("Launching cheese camera application for POV picture")

            # Show workflow instructions
            QMessageBox.information(
                self,
                "POV Picture Workflow Starting",
                "The camera application will launch after you click OK.\n\n"
                "WORKFLOW STEPS:\n"
                "1. Position yourself at the TV location (NOT the camera)\n"
                "2. Make sure NO PEOPLE are in the room at all\n"
                "3. Take picture FROM TV's perspective of the room\n"
                "4. Child's face should NOT be visible\n"
                "5. TV screen should NOT be in the picture\n"
                "6. Close the camera app when done\n\n"
                "After you close the camera app, the picture will automatically\n"
                "display fullscreen for you to photograph with your iPad."
            )
            
            # Check if cheese is available
            if not self._check_cheese_available():
                raise FlashTVError(
                    "Camera application 'cheese' not found",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Install cheese with: sudo apt-get install cheese",
                )
            
            # Create Pictures/Webcam directory if it doesn't exist
            webcam_dir = Path.home() / "Pictures" / "Webcam"
            webcam_dir.mkdir(parents=True, exist_ok=True)
            
            # Get baseline of existing images
            existing_images = self._get_webcam_images()
            
            # Launch cheese
            try:
                self.cheese_process = subprocess.Popen(
                    ["cheese"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                self.workflow_step = "cheese_running"
                self._update_workflow_status("Camera app launched - take your POV picture", "info")
                self.step_details_label.setText("Close the camera app when you're done taking the picture")
                
                # Disable the launch button while cheese is running
                self.launch_camera_button.setEnabled(False)
                
                # Store existing images for comparison
                self.existing_images = existing_images
                
                # Start monitoring cheese process
                self.monitor_timer.start(1000)  # Check every second
                
                self.logger.info("Cheese launched successfully, monitoring process")
                
            except Exception as e:
                self.logger.error(f"Failed to launch cheese: {e}")
                raise FlashTVError(
                    f"Camera application launch failed: {e}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try restarting the application",
                )

        except Exception as e:
            self.logger.error(f"Error launching camera app: {e}")
            self._reset_workflow_state()
            QMessageBox.warning(
                self,
                "Camera Error",
                f"Could not launch camera app: {e}\n\n"
                "Please try again or contact support.",
            )
            raise

    def _check_cheese_available(self) -> bool:
        """Check if cheese camera app is available."""
        try:
            result = subprocess.run(
                ["which", "cheese"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_webcam_images(self) -> list[Path]:
        """Get list of existing images in webcam directory."""
        webcam_dir = Path.home() / "Pictures" / "Webcam"
        if not webcam_dir.exists():
            return []
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        images = []
        
        for file_path in webcam_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                images.append(file_path)
        
        return sorted(images, key=lambda p: p.stat().st_mtime)

    def _monitor_cheese_process(self) -> None:
        """Monitor cheese process and detect when it closes."""
        if self.workflow_step != "cheese_running" or not self.cheese_process:
            return
            
        # Check if cheese process is still running
        if self.cheese_process.poll() is not None:
            # Cheese has closed
            self.monitor_timer.stop()
            self.workflow_step = "image_search"
            
            self.logger.info("Cheese process closed, searching for new image")
            self._update_workflow_status("Camera app closed - searching for new picture...", "info")
            self.step_details_label.setText("Automatically detecting the picture you took")
            
            # Give cheese a moment to finish saving the file
            QTimer.singleShot(2000, self._find_and_display_new_image)

    def _find_and_display_new_image(self) -> None:
        """Find the newest image and display it fullscreen."""
        try:
            # Get current images
            current_images = self._get_webcam_images()
            
            # Find new images (not in existing list)
            new_images = []
            existing_paths = {img.resolve() for img in getattr(self, 'existing_images', [])}
            
            for img in current_images:
                if img.resolve() not in existing_paths:
                    new_images.append(img)
            
            if not new_images:
                # No new images found - show error
                self.logger.warning("No new images found in webcam directory")
                self._handle_no_image_found()
                return
            
            # Get the newest image (by modification time)
            newest_image = max(new_images, key=lambda p: p.stat().st_mtime)
            self.temp_image_path = str(newest_image)
            
            self.logger.info(f"Found new POV image: {newest_image}")
            
            # Display image fullscreen
            self._display_image_fullscreen(newest_image)
            
        except Exception as e:
            self.logger.error(f"Error finding new image: {e}")
            self._handle_no_image_found()

    def _display_image_fullscreen(self, image_path: Path) -> None:
        """Display image fullscreen using available image viewer."""
        try:
            # Try different image viewers in order of preference
            viewers = [
                ["eog", "--fullscreen"],
                ["feh", "--fullscreen", "--auto-zoom"],
                ["gpicview", "--fullscreen"],
                ["display", "-fullscreen"],  # ImageMagick
            ]
            
            viewer_launched = False
            for viewer_cmd in viewers:
                try:
                    # Check if viewer is available
                    which_result = subprocess.run(
                        ["which", viewer_cmd[0]], 
                        capture_output=True, 
                        timeout=5
                    )
                    if which_result.returncode != 0:
                        continue
                    
                    # Launch viewer
                    self.image_viewer_process = subprocess.Popen(
                        viewer_cmd + [str(image_path)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    
                    viewer_launched = True
                    self.logger.info(f"Launched image viewer: {viewer_cmd[0]}")
                    break
                    
                except Exception as e:
                    self.logger.warning(f"Failed to launch {viewer_cmd[0]}: {e}")
                    continue
            
            if not viewer_launched:
                # Fallback: try to open with default application
                try:
                    self.image_viewer_process = subprocess.Popen(
                        ["xdg-open", str(image_path)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    viewer_launched = True
                    self.logger.info("Opened image with default application")
                except Exception as e:
                    self.logger.error(f"Failed to open with xdg-open: {e}")
            
            if viewer_launched:
                self.workflow_step = "fullscreen"
                self._update_workflow_status("Picture displayed fullscreen - take iPad photo", "success")
                self.step_details_label.setText("Use your iPad to photograph the computer screen showing this image")
                
                # Show confirmation dialog
                QTimer.singleShot(1000, self._show_ipad_confirmation)
                
            else:
                raise FlashTVError(
                    "No suitable image viewer found",
                    ErrorType.SYSTEM_ERROR,
                    recovery_action="Install an image viewer: sudo apt-get install eog"
                )
                
        except Exception as e:
            self.logger.error(f"Error displaying image fullscreen: {e}")
            self._handle_display_error(e)

    def _show_ipad_confirmation(self) -> None:
        """Show dialog to confirm iPad photo was taken."""
        try:
            reply = QMessageBox.question(
                self,
                "iPad Photo Confirmation",
                "The POV picture is now displayed fullscreen.\n\n"
                "INSTRUCTIONS:\n"
                "1. Use your iPad to take a photo of this computer screen\n"
                "2. Make sure you capture the entire displayed image\n"
                "3. The iPad photo shows what the TV 'sees'\n\n"
                "Have you successfully taken the iPad photo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("User confirmed iPad photo was taken")
                self.workflow_step = "confirmed"
                self._cleanup_and_complete()
            else:
                self.logger.info("User needs to retake iPad photo")
                # Keep fullscreen image open, show confirmation again
                QTimer.singleShot(5000, self._show_ipad_confirmation)
                
        except Exception as e:
            self.logger.error(f"Error showing iPad confirmation: {e}")
            self._handle_display_error(e)

    def _cleanup_and_complete(self) -> None:
        """Clean up processes and files, then complete the step."""
        try:
            self.workflow_step = "cleanup"
            
            # Close image viewer
            if self.image_viewer_process:
                try:
                    self.image_viewer_process.terminate()
                    # Give it a moment to close gracefully
                    try:
                        self.image_viewer_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.image_viewer_process.kill()
                except Exception as e:
                    self.logger.warning(f"Error closing image viewer: {e}")
                finally:
                    self.image_viewer_process = None
            
            # Delete temporary POV picture file
            if self.temp_image_path and os.path.exists(self.temp_image_path):
                try:
                    os.remove(self.temp_image_path)
                    self.logger.info(f"Deleted temporary POV picture: {self.temp_image_path}")
                except Exception as e:
                    self.logger.warning(f"Could not delete temp file: {e}")
            
            # Mark step as completed
            self.state.set_user_input("pov_picture_complete", True)
            self.state.set_user_input("pov_picture_ipad_workflow", True)
            
            if self.state_manager:
                self.state_manager.save_state(self.state)
            
            # Update UI
            self._update_workflow_status("POV picture workflow completed successfully!", "success")
            self.step_details_label.setText("iPad photo taken and temporary files cleaned up")
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)
            
            self.logger.info("POV picture step completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            # Still mark as complete even if cleanup had issues
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)

    def _handle_no_image_found(self) -> None:
        """Handle case where no new image was found."""
        self._update_workflow_status("No new picture found", "error")
        self.step_details_label.setText("Please try taking the picture again")
        
        reply = QMessageBox.question(
            self,
            "No Picture Found",
            "No new picture was found in the webcam directory.\n\n"
            "This could happen if:\n"
            "• You didn't take a picture\n"
            "• The camera app saved to a different location\n"
            "• There was an error saving the picture\n\n"
            "Would you like to try again?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._reset_workflow_state()
        else:
            self._reset_workflow_state()

    def _handle_display_error(self, error: Exception) -> None:
        """Handle errors during image display."""
        self._update_workflow_status("Error displaying picture", "error")
        self.step_details_label.setText("Please try the workflow again")
        
        QMessageBox.warning(
            self,
            "Display Error",
            f"Could not display the POV picture fullscreen: {error}\n\n"
            "Please try the workflow again."
        )
        
        self._reset_workflow_state()

    def _reset_workflow_state(self) -> None:
        """Reset workflow state to allow retry."""
        self.workflow_step = "initial"
        self.launch_camera_button.setEnabled(True)
        self._update_workflow_status("Ready to start POV picture workflow", "info")
        self.step_details_label.setText("Click 'Open Camera Application' to begin")
        
        # Clean up processes
        if self.cheese_process:
            try:
                if self.cheese_process.poll() is None:
                    self.cheese_process.terminate()
            except Exception:
                pass
            self.cheese_process = None
        
        if self.image_viewer_process:
            try:
                self.image_viewer_process.terminate()
            except Exception:
                pass
            self.image_viewer_process = None
        
        self.monitor_timer.stop()

    def _update_workflow_status(self, message: str, status_type: str) -> None:
        """Update the workflow status display."""
        status_icons = {
            "info": "📷",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️"
        }
        
        icon = status_icons.get(status_type, "📷")
        self.workflow_status_label.setText(f"{icon} {message}")
        
        colors = {
            "info": self.config.info_color,
            "success": self.config.success_color,
            "error": self.config.error_color,
            "warning": self.config.warning_color
        }
        
        color = colors.get(status_type, self.config.info_color)
        self.workflow_status_label.setStyleSheet(
            f"color: {color}; font-weight: bold; padding: 10px;"
        )

    @handle_step_error
    def _show_pov_help(self, checked: bool = False) -> None:
        """Show POV picture help."""
        try:
            self.logger.info("Showing POV picture help dialog")

            help_text = """POV Picture Workflow Help:

PURPOSE: Document what the TV 'sees' when looking at the viewing area

NEW WORKFLOW STEPS:
1. Click 'Open Camera Application' - launches cheese camera app
2. Position yourself at the TV location (NOT the camera!)
3. Make sure NO PEOPLE are in the room at all
4. Take picture FROM TV's perspective of empty room/couch area
5. Close camera app - picture auto-displays fullscreen
6. Use iPad to photograph the computer screen
7. Confirm iPad photo taken - system cleans up automatically

CRITICAL REQUIREMENTS:
• Take picture FROM the TV's position, not camera position
• NO PEOPLE should be visible anywhere in the picture
• Child's face must NOT be in the picture
• TV screen should NOT be in the picture
• Shows empty room/couch area from TV's perspective
• Room must be completely empty of people

WHY THIS WORKFLOW:
• POV picture is temporary, not saved permanently
• iPad photo documents the viewing perspective
• Automatic cleanup prevents file accumulation
• Fullscreen display ensures complete capture

TECHNICAL DETAILS:
• Camera app (cheese) saves to ~/Pictures/Webcam/
• System auto-detects newest image
• Displays fullscreen using system image viewer
• Temporary file deleted after iPad photo confirmation"""

            QMessageBox.information(self, "POV Picture Workflow Help", help_text)

        except Exception as e:
            self.logger.error(f"Error showing POV help: {e}")
            raise FlashTVError(
                f"Failed to show help dialog: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try clicking help again",
            )

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click."""
        try:
            if self.state.get_user_input("pov_picture_complete", False):
                self.logger.info("POV picture step completed via iPad workflow")
                
                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but POV picture workflow not completed")
                QMessageBox.warning(
                    self,
                    "Workflow Not Complete",
                    "Please complete the POV picture workflow first."
                )

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to continue from POV picture step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Complete the workflow first",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the POV picture step."""
        super().activate_step()
        self.logger.info("POV picture step activated")

        # Check if step was previously completed
        if self.state.get_user_input("pov_picture_complete", False):
            self._update_workflow_status("POV picture workflow previously completed", "success")
            self.step_details_label.setText("Step completed in previous session")
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)
            self.logger.info("POV picture step already completed")
        else:
            self._reset_workflow_state()

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Stop monitoring
            self.monitor_timer.stop()
            
            # Clean up processes
            if self.cheese_process:
                try:
                    if self.cheese_process.poll() is None:
                        self.cheese_process.terminate()
                        self.cheese_process.wait(timeout=5)
                except Exception as e:
                    self.logger.warning(f"Error cleaning up cheese process: {e}")
                finally:
                    self.cheese_process = None
            
            if self.image_viewer_process:
                try:
                    self.image_viewer_process.terminate()
                    self.image_viewer_process.wait(timeout=5)
                except Exception as e:
                    self.logger.warning(f"Error cleaning up image viewer: {e}")
                finally:
                    self.image_viewer_process = None
            
            # Delete temp file if it still exists
            if hasattr(self, 'temp_image_path') and self.temp_image_path and os.path.exists(self.temp_image_path):
                try:
                    os.remove(self.temp_image_path)
                    self.logger.info("Cleaned up temporary POV picture file")
                except Exception as e:
                    self.logger.warning(f"Could not delete temp file during cleanup: {e}")

            # Final state save
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("POV picture step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")