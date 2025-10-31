"""Camera setup step - comprehensive camera positioning, detection, and POV capture."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional

from PyQt6.QtWidgets import QWidget, QListWidget, QListWidgetItem, QMessageBox, QTextEdit, QLabel, QGroupBox
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from constants import UI, Messages
from utils.ui_factory import ButtonStyle


class CameraSetupStep(WizardStep):
    """Step 6: Complete camera setup - positioning, detection, testing, and POV picture."""

    # Signals for process monitoring
    cheese_closed = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Camera detection state
        self.cameras_detected = False

        # POV workflow state
        self.cheese_process: Optional[subprocess.Popen] = None
        self.image_viewer_process: Optional[subprocess.Popen] = None
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_cheese_process)
        self.temp_image_path: Optional[str] = None
        self.pov_workflow_step = "initial"  # initial -> cheese_running -> image_found -> fullscreen -> confirmed -> cleanup

    def create_content_widget(self) -> QWidget:
        """Create the comprehensive camera setup UI."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Overview section
        overview_section = self._create_overview_section()
        main_layout.addWidget(overview_section)

        # Main content area with two columns
        content_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Left column: Detection/test and Positioning (with integrated preview)
        left_column = self.ui_factory.create_vertical_layout(spacing=8)

        detection_section = self._create_detection_section()
        left_column.addWidget(detection_section)

        positioning_section = self._create_positioning_section()
        left_column.addWidget(positioning_section, 1)

        content_row.addLayout(left_column, 1)

        # Right column: POV picture
        right_column = self.ui_factory.create_vertical_layout(spacing=8)

        pov_section = self._create_pov_section()
        right_column.addWidget(pov_section, 1)

        content_row.addLayout(right_column, 1)

        main_layout.addLayout(content_row, 1)

        # Notes section
        notes_section = self._create_notes_section()
        main_layout.addWidget(notes_section)

        # Continue button
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        return content

    def _create_overview_section(self) -> QWidget:
        """Create the overview section explaining the complete workflow."""
        overview_group, overview_layout = self.ui_factory.create_group_box("Camera Setup Overview")

        overview_text = self.ui_factory.create_label(
            "This step will help you position the camera, verify it's working, "
            "and capture a Point of View (POV) picture showing what the camera sees.\n\n"
            "The camera should be positioned to view the seating area where family members sit when watching TV. "
            "The POV picture will show the empty seating area from the camera's perspective - "
            "this serves as a baseline reference image."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_positioning_section(self) -> QWidget:
        """Create the camera positioning guidelines section with integrated preview."""
        positioning_group, positioning_layout = self.ui_factory.create_group_box("Step 2: Position the Camera")

        positioning_text = (
            "Position your camera to view the TV-watching seating area:\n"
            "PLACEMENT: Please prioritize, in order, placing on top of the TV if the TV is not too high, placing near the TV on a surface, and mounting on the wall.\n"
            "HEIGHT: Please try to avoid placing the camera too high as higher heights are not necessarily validated.\n"
            "ANGLE: Please try to avoid extreme horizontal side angles (>15 degrees from the camera facing straight ahead) as these are not necessarily validated.\n"
            "FIELD OF VIEW: The camera should be placed to maximize coverage of the areas the child watches TV in, the entire areas if possible.\n"
            "LIGHTING: Try to minimize backlighting/glare from windows behind subjects but do not try to change participant preferences unless they offer.\n"
            "CONNECTION: Make sure the cable cannot be easily interfered with.\n"
        )

        positioning_label = self.ui_factory.create_label(positioning_text)
        positioning_label.setWordWrap(True)
        positioning_layout.addWidget(positioning_label)

        # Add live preview button directly in positioning section
        positioning_layout.addSpacing(15)

        self.launch_preview_button = self.ui_factory.create_action_button(
            "📹 Launch Live Preview",
            callback=self._launch_live_preview,
            style=ButtonStyle.PRIMARY,
            height=35,
            enabled=True,
        )
        positioning_layout.addWidget(self.launch_preview_button)

        # Preview status
        self.preview_status = self.ui_factory.create_status_label("Use live preview to help position camera", status_type="info")
        positioning_layout.addWidget(self.preview_status)

        positioning_layout.addStretch()

        return positioning_group

    def _create_detection_section(self) -> QWidget:
        """Create the combined camera detection and test section."""
        detection_group, detection_layout = self.ui_factory.create_group_box("Step 1: Detect and Test Camera")

        # Status label showing test results
        self.camera_status = self.ui_factory.create_label("Testing camera automatically...")
        self.camera_status.setWordWrap(True)
        self.camera_status.setMinimumHeight(60)
        from PyQt6.QtGui import QFont
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.camera_status.setFont(font)
        detection_layout.addWidget(self.camera_status)

        detection_layout.addSpacing(10)

        # Single re-test button
        self.retest_button = self.ui_factory.create_action_button(
            "🔄 Re-test Camera",
            callback=self._run_camera_detection_and_test,
            style=ButtonStyle.PRIMARY,
            height=35,
            enabled=False,
        )
        detection_layout.addWidget(self.retest_button)

        # Camera list label (for details)
        camera_label = self.ui_factory.create_label("Detected cameras:")
        detection_layout.addWidget(camera_label)

        # Camera list - compact
        self.camera_list = QListWidget()
        self.camera_list.setMaximumHeight(60)
        self.camera_list.itemSelectionChanged.connect(self._on_camera_selection_changed)
        detection_layout.addWidget(self.camera_list)

        detection_layout.addStretch()

        return detection_group

    def _create_pov_section(self) -> QWidget:
        """Create the POV picture capture section."""
        pov_group, pov_layout = self.ui_factory.create_group_box("Step 3: Capture POV Baseline Picture")

        # POV instructions with proper word wrapping
        pov_instructions_text = (
            "After positioning the camera:\n\n"
            "1. Make sure NO PEOPLE are visible in the camera's view\n\n"
            "2. Click 'Capture POV Picture' to take a baseline image\n\n"
            "3. The camera will capture what it sees of the empty seating area\n\n"
            "4. Picture will display fullscreen for iPad photo documentation\n\n"
            "5. Use your iPad to photograph the screen\n\n"
            "6. Confirm when iPad photo is taken\n\n"
            "This baseline image documents the camera's view of the empty room."
        )
        pov_instructions = self.ui_factory.create_label(pov_instructions_text)
        pov_layout.addWidget(pov_instructions)

        # POV capture button
        self.capture_pov_button = self.ui_factory.create_action_button(
            "📷 Capture POV Picture",
            callback=self._launch_pov_capture,
            style=ButtonStyle.SUCCESS,
            height=40,
            enabled=False,
        )
        pov_layout.addWidget(self.capture_pov_button)

        # iPad confirmation button - initially hidden
        self.ipad_confirm_button = self.ui_factory.create_action_button(
            "✅ I've taken the iPad photo",
            callback=self._on_ipad_photo_confirmed,
            style=ButtonStyle.SUCCESS,
            height=40,
        )
        self.ipad_confirm_button.setVisible(False)
        pov_layout.addWidget(self.ipad_confirm_button)

        # POV status
        self.pov_status = self.ui_factory.create_status_label("Complete camera setup before capturing POV picture", status_type="info")
        pov_layout.addWidget(self.pov_status)

        pov_layout.addStretch()

        return pov_group

    def _create_notes_section(self) -> QWidget:
        """Create notes section for camera setup observations."""
        notes_group, notes_layout = self.ui_factory.create_group_box("Setup Notes")

        notes_label = self.ui_factory.create_label("Document observations (camera position, angle, field of view, lighting, issues):")
        notes_layout.addWidget(notes_label)

        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        self.notes_text.setPlaceholderText(
            "Example: Camera mounted 6ft high at 15° angle, covers full couch area, slight window glare in afternoon..."
        )
        notes_layout.addWidget(self.notes_text)

        return notes_group

    def _create_continue_section(self):
        """Create the continue button section."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text="Camera Setup Complete - Continue"
        )
        self.continue_button.setEnabled(False)

        return button_layout

    @handle_step_error
    def _run_camera_detection_and_test(self, checked: bool = False) -> None:
        """Run camera detection and immediately test the first camera found."""
        try:
            # First detect cameras
            self.camera_status.setText("Detecting cameras...")
            self._detect_cameras()

            # If cameras were found, automatically test the first one
            if self.cameras_detected and self.camera_list.count() > 0:
                # Small delay for UI update
                QTimer.singleShot(500, self._test_camera)
        except Exception as e:
            self.logger.error(f"Error in camera detection and test: {e}")
            self.camera_status.setText(f"Error: {str(e)}")
            raise

    @handle_step_error
    def _detect_cameras(self, checked: bool = False) -> None:
        """Detect available cameras with comprehensive error handling and duplicate filtering."""
        try:
            self.logger.info("Starting camera detection")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.retest_button.setEnabled(False)
            self.camera_list.clear()

            # Import the improved camera detection utility
            import sys

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "python_scripts"))

            try:
                from utils.camera_detection_utils import get_unique_cameras

                # Use improved camera detection that filters duplicates
                unique_cameras = get_unique_cameras()
                video_devices = []

                for camera in unique_cameras:
                    video_devices.append(
                        {
                            "path": camera["path"],
                            "name": camera["name"],
                            "number": camera["number"],
                            "capabilities": camera.get("capabilities", "unknown"),
                            "is_capture_device": camera.get("is_capture_device", True),
                        }
                    )
                    self.logger.debug(
                        f"Detected unique camera: {camera['name']} at {camera['path']} (capabilities: {camera.get('capabilities', 'unknown')})"
                    )

                self.logger.info(f"Found {len(video_devices)} unique cameras (duplicates filtered)")

            except ImportError as e:
                self.logger.warning(f"Could not import improved camera detection: {e}")

                # Simple fallback using basic v4l2-ctl --list-devices approach
                video_devices = self._fallback_camera_detection()

            # Populate camera list with enhanced information
            for camera in video_devices:
                display_text = f"{camera['name']} ({camera['path']})"
                if camera.get("capabilities") and camera["capabilities"] != "unknown":
                    display_text += f" - {camera['capabilities']}"

                item = QListWidgetItem(display_text)
                item.setData(32, camera)  # Store camera data
                self.camera_list.addItem(item)

            # Update state
            self.state.set_system_state("detected_cameras", video_devices)

            # Persist state
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.cameras_detected = True

            if video_devices:
                self.logger.info(f"Found {len(video_devices)} cameras")

                # Auto-select the first camera
                self.camera_list.setCurrentRow(0)
                first_camera = video_devices[0]
                self.state.set_user_input("selected_camera", first_camera["path"])
                self.state.set_user_input("selected_camera_name", first_camera["name"])

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.logger.info(f"Auto-selected first camera: {first_camera['name']} ({first_camera['path']})")
            else:
                self.update_status(StepStatus.FAILED)
                self.camera_status.setText("Camera not detected")
                self.logger.warning("No cameras detected")
                raise FlashTVError(
                    "No cameras detected on system",
                    ErrorType.SYSTEM_ERROR,
                    recovery_action="Check camera connections and try again",
                )

        except Exception as e:
            self.logger.error(f"Error during camera detection: {e}")
            self.update_status(StepStatus.FAILED)
            self.camera_status.setText("Camera not detected")
            raise

        finally:
            self.retest_button.setEnabled(True)

    @handle_step_error
    def _on_camera_selection_changed(self) -> None:
        """Handle camera selection changes with logging."""
        try:
            selected_items = self.camera_list.selectedItems()

            if selected_items:
                camera_data = selected_items[0].data(32)
                camera_path = camera_data["path"]
                camera_name = camera_data["name"]

                self.state.set_user_input("selected_camera", camera_path)
                self.state.set_user_input("selected_camera_name", camera_name)

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.logger.info(f"Selected camera: {camera_name} ({camera_path})")
            else:
                self.logger.debug("No camera selected")

        except Exception as e:
            self.logger.error(f"Error handling camera selection: {e}")
            raise FlashTVError(
                f"Failed to handle camera selection: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try selecting the camera again",
            )

    @handle_step_error
    def _test_camera(self, checked: bool = False) -> None:
        """Test the selected camera with comprehensive error handling."""
        try:
            camera_path = self.state.get_user_input("selected_camera")
            camera_name = self.state.get_user_input("selected_camera_name", "")
            if not camera_path:
                self.logger.warning("No camera selected for testing")
                self.camera_status.setText("Camera not detected")
                return

            self.logger.info(f"Testing camera: {camera_path}")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.retest_button.setEnabled(False)
            self.camera_status.setText(f"Testing {camera_name}...")

            # Test camera with v4l2-ctl using process runner
            result = self.process_runner.run_command(
                ["v4l2-ctl", "--device", camera_path, "--list-formats-ext"],
                timeout_ms=10000,
            )

            if result and result.returncode == 0:
                self.logger.info("Camera format test successful")

                # Try to capture a test frame
                test_result = self.process_runner.run_command(
                    [
                        "v4l2-ctl",
                        "--device",
                        camera_path,
                        "--stream-mmap",
                        "--stream-count=1",
                    ],
                    timeout_ms=5000,
                )

                if test_result and test_result.returncode == 0:
                    # Save successful test status
                    self.state.set_user_input("camera_tested", True)

                    # Persist state
                    if self.state_manager:
                        self.state_manager.save_state(self.state)

                    # Enable POV capture (preview already enabled)
                    self.capture_pov_button.setEnabled(True)
                    self.preview_status.setText("Camera tested - preview ready for use")
                    self.pov_status.setText("Ready to capture POV picture")

                    # Show success status
                    self.camera_status.setText(f"Camera detected and test passed")
                    self.update_status(StepStatus.USER_ACTION_REQUIRED)
                    self.logger.info("Camera test completed successfully")
                else:
                    error_msg = test_result.stderr if test_result else "Unknown error"
                    self.camera_status.setText(f"Camera detected but test failed")
                    self.update_status(StepStatus.USER_ACTION_REQUIRED)
                    self.logger.warning(f"Frame capture failed: {error_msg}")
            else:
                error_msg = result.stderr if result else "Command failed"
                self.camera_status.setText(f"Camera detected but test failed")
                self.update_status(StepStatus.FAILED)
                self.logger.error(f"Camera test failed: {error_msg}")

        except Exception as e:
            self.logger.error(f"Error testing camera: {e}")
            self.camera_status.setText(f"Camera detected but test failed")
            self.update_status(StepStatus.FAILED)

        finally:
            self.retest_button.setEnabled(True)

    @handle_step_error
    def _launch_live_preview(self, checked: bool = False) -> None:
        """Launch live camera preview using cheese or other camera app."""
        try:
            camera_path = self.state.get_user_input("selected_camera")
            if not camera_path:
                self.logger.warning("No camera selected for preview")
                return

            self.logger.info(f"Launching live camera preview for: {camera_path}")
            self.preview_status.setText("📹 Launching camera preview...")

            # Check if cheese is available
            if not self._check_cheese_available():
                raise FlashTVError(
                    "Camera application 'cheese' not found",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Install cheese with: sudo apt-get install cheese",
                )

            # Launch cheese for live preview
            try:
                subprocess.Popen(["cheese", "--device", camera_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.preview_status.setText("✅ Live preview launched - adjust camera positioning as needed")
                self.logger.info("Camera preview launched successfully")

            except Exception as e:
                self.logger.error(f"Failed to launch camera preview: {e}")
                raise FlashTVError(
                    f"Camera preview launch failed: {e}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try restarting or check camera connections",
                )

        except Exception as e:
            self.logger.error(f"Error launching live preview: {e}")
            self.preview_status.setText(f"❌ Preview failed: {e}")
            raise

    @handle_step_error
    def _launch_pov_capture(self, checked: bool = False) -> None:
        """Launch camera app to capture POV picture."""
        try:
            if self.pov_workflow_step != "initial":
                self.pov_status.setText(f"⚠️ POV workflow already in progress")
                return

            self.logger.info("Starting POV picture capture workflow")

            # Update status
            self.pov_status.setText("📸 Starting POV picture capture...")

            # Show instructions
            reply = QMessageBox.information(
                self,
                "POV Picture Capture",
                "The camera app will now open.\n\n"
                "IMPORTANT:\n"
                "• Make sure NO PEOPLE are visible in the camera's view\n"
                "• The camera will capture the empty seating area\n"
                "• This is a baseline image of what the camera sees\n"
                "• Take the picture when the room is empty\n"
                "• Close the camera app after taking the picture\n\n"
                "Click OK to continue...",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            )

            if reply != QMessageBox.StandardButton.Ok:
                self.logger.info("User cancelled POV capture")
                return

            # Close any existing cheese instances first
            self._close_existing_cheese_instances()

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
                camera_path = self.state.get_user_input("selected_camera")
                self.cheese_process = subprocess.Popen(
                    ["cheese", "--device", camera_path] if camera_path else ["cheese"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )

                self.pov_workflow_step = "cheese_running"
                self.pov_status.setText("📸 Camera app launched - capture empty seating area, then close app")

                # Disable the capture button while cheese is running
                self.capture_pov_button.setEnabled(False)

                # Store existing images for comparison
                self.existing_images = existing_images

                # Start monitoring cheese process
                self.monitor_timer.start(1000)  # Check every second

                self.logger.info("Cheese launched for POV capture, monitoring process")

            except Exception as e:
                self.logger.error(f"Failed to launch cheese for POV: {e}")
                raise FlashTVError(
                    f"Camera application launch failed: {e}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try restarting the application",
                )

        except Exception as e:
            self.logger.error(f"Error launching POV capture: {e}")
            self._reset_pov_workflow()
            QMessageBox.warning(
                self,
                "POV Capture Error",
                f"Could not launch POV capture: {e}\n\nPlease try again.",
            )
            raise

    def _monitor_cheese_process(self) -> None:
        """Monitor cheese process and detect when it closes."""
        if self.pov_workflow_step != "cheese_running" or not self.cheese_process:
            return

        # Check if cheese process is still running
        if self.cheese_process.poll() is not None:
            # Cheese has closed
            self.monitor_timer.stop()
            self.pov_workflow_step = "image_search"

            self.logger.info("Cheese process closed, searching for POV image")
            self.pov_status.setText("🔍 Camera closed - searching for captured image...")

            # Give cheese a moment to finish saving the file
            QTimer.singleShot(2000, self._find_and_display_pov_image)

    def _find_and_display_pov_image(self) -> None:
        """Find the newest POV image and display it fullscreen."""
        try:
            # Get current images
            current_images = self._get_webcam_images()

            # Find new images (not in existing list)
            new_images = []
            existing_paths = {img.resolve() for img in getattr(self, "existing_images", [])}

            for img in current_images:
                if img.resolve() not in existing_paths:
                    new_images.append(img)

            if not new_images:
                # No new images found - show error
                self.logger.warning("No new POV image found in webcam directory")
                self._handle_no_pov_image_found()
                return

            # Get the newest image (by modification time)
            newest_image = max(new_images, key=lambda p: p.stat().st_mtime)
            self.temp_image_path = str(newest_image)

            self.logger.info(f"Found new POV image: {newest_image}")

            # Save POV image to participant data folder
            self._save_pov_image_to_data_folder(newest_image)

            # Display image fullscreen for iPad photo
            self._display_image_fullscreen(newest_image)

        except Exception as e:
            self.logger.error(f"Error finding POV image: {e}")
            self._handle_no_pov_image_found()

    def _save_pov_image_to_data_folder(self, image_path: Path) -> None:
        """Save POV image to participant's data folder."""
        try:
            # Get participant info
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            full_participant_id = f"{participant_id}{device_id}" if device_id else participant_id

            # Create data directory
            data_path = f"/home/{username}/data/{full_participant_id}_data"
            os.makedirs(data_path, exist_ok=True)

            # Create filename
            pov_filename = f"{full_participant_id}_camera_pov.png"
            destination_path = os.path.join(data_path, pov_filename)

            # Copy the image
            import shutil

            shutil.copy2(image_path, destination_path)

            self.logger.info(f"Saved POV image to: {destination_path}")
            self.state.set_user_input("pov_image_path", destination_path)

            if self.state_manager:
                self.state_manager.save_state(self.state)

        except Exception as e:
            self.logger.error(f"Error saving POV image to data folder: {e}")
            # Don't fail the workflow, just log the error

    def _display_image_fullscreen(self, image_path: Path) -> None:
        """Display POV image fullscreen for iPad photo."""
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
                    which_result = subprocess.run(["which", viewer_cmd[0]], capture_output=True, timeout=5)
                    if which_result.returncode != 0:
                        continue

                    # Launch viewer
                    self.image_viewer_process = subprocess.Popen(viewer_cmd + [str(image_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    viewer_launched = True
                    self.logger.info(f"Launched image viewer: {viewer_cmd[0]}")
                    break

                except Exception as e:
                    self.logger.warning(f"Failed to launch {viewer_cmd[0]}: {e}")
                    continue

            if not viewer_launched:
                # Fallback: try to open with default application
                try:
                    self.image_viewer_process = subprocess.Popen(["xdg-open", str(image_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    viewer_launched = True
                    self.logger.info("Opened POV image with default application")
                except Exception as e:
                    self.logger.error(f"Failed to open with xdg-open: {e}")

            if viewer_launched:
                self.pov_workflow_step = "fullscreen"
                self.pov_status.setText("✅ POV image displayed - use iPad to photograph the screen")

                # Enable confirmation button
                self.ipad_confirm_button.setVisible(True)
                self.ipad_confirm_button.setEnabled(True)

            else:
                raise FlashTVError(
                    "No suitable image viewer found", ErrorType.SYSTEM_ERROR, recovery_action="Install an image viewer: sudo apt-get install eog"
                )

        except Exception as e:
            self.logger.error(f"Error displaying POV image fullscreen: {e}")
            self._handle_pov_display_error(e)

    def _on_ipad_photo_confirmed(self, checked: bool = False) -> None:
        """Handle iPad photo confirmation."""
        self.logger.info("User confirmed iPad photo of POV image was taken")
        self.pov_workflow_step = "confirmed"
        self._cleanup_pov_and_complete()

    def _cleanup_pov_and_complete(self) -> None:
        """Clean up POV workflow and complete the step."""
        try:
            self.pov_workflow_step = "cleanup"

            # Close image viewer
            if self.image_viewer_process:
                try:
                    self.image_viewer_process.terminate()
                    try:
                        self.image_viewer_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.image_viewer_process.kill()
                except Exception as e:
                    self.logger.warning(f"Error closing image viewer: {e}")
                finally:
                    self.image_viewer_process = None

            # Delete temporary webcam image (we already saved a copy to data folder)
            if self.temp_image_path and os.path.exists(self.temp_image_path):
                try:
                    os.remove(self.temp_image_path)
                    self.logger.info(f"Deleted temporary POV image: {self.temp_image_path}")
                except Exception as e:
                    self.logger.warning(f"Could not delete temp file: {e}")

            # Mark POV as completed
            self.state.set_user_input("pov_picture_complete", True)

            if self.state_manager:
                self.state_manager.save_state(self.state)

            # Update UI
            self.pov_status.setText("✅ POV picture captured and saved successfully!")
            self.ipad_confirm_button.setVisible(False)
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)

            self.logger.info("POV picture workflow completed successfully")

        except Exception as e:
            self.logger.error(f"Error during POV cleanup: {e}")
            # Still mark as complete even if cleanup had issues
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)

    def _handle_no_pov_image_found(self) -> None:
        """Handle case where no POV image was found."""
        self.pov_status.setText("❌ No POV image found")

        reply = QMessageBox.question(
            self,
            "No Picture Found",
            "No new POV picture was found.\n\n"
            "This could happen if:\n"
            "• You didn't take a picture\n"
            "• The camera app saved to a different location\n"
            "• There was an error saving the picture\n\n"
            "Would you like to try again?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._reset_pov_workflow()
        else:
            self._reset_pov_workflow()

    def _handle_pov_display_error(self, error: Exception) -> None:
        """Handle errors during POV image display."""
        self.pov_status.setText("❌ Error displaying POV image")

        QMessageBox.warning(self, "Display Error", f"Could not display the POV picture: {error}\n\nPlease try again.")

        self._reset_pov_workflow()

    def _reset_pov_workflow(self) -> None:
        """Reset POV workflow state to allow retry."""
        self.pov_workflow_step = "initial"
        self.capture_pov_button.setEnabled(True)
        self.pov_status.setText("✅ Ready to capture POV picture")
        self.ipad_confirm_button.setVisible(False)

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

    def _check_cheese_available(self) -> bool:
        """Check if cheese camera app is available."""
        try:
            result = subprocess.run(["which", "cheese"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _close_existing_cheese_instances(self) -> None:
        """Close any existing cheese processes before starting new one."""
        try:
            self.logger.info("Checking for existing cheese instances")

            # Use pkill to close any existing cheese processes
            result = subprocess.run(["pkill", "-9", "cheese"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                self.logger.info("Closed existing cheese instances")
                # Give processes time to fully terminate
                time.sleep(1)
            else:
                self.logger.debug("No existing cheese instances found")

        except subprocess.TimeoutExpired:
            self.logger.warning("Timeout while trying to close cheese instances")
        except Exception as e:
            self.logger.warning(f"Error closing existing cheese instances: {e}")
            # Don't fail the workflow if we can't close existing instances

    def _get_webcam_images(self) -> list[Path]:
        """Get list of existing images in webcam directory."""
        webcam_dir = Path.home() / "Pictures" / "Webcam"
        if not webcam_dir.exists():
            return []

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
        images = []

        for file_path in webcam_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                images.append(file_path)

        return sorted(images, key=lambda p: p.stat().st_mtime)

    def _fallback_camera_detection(self) -> List[Dict[str, str]]:
        """Fallback camera detection method when improved detection fails."""
        video_devices = []

        try:
            # Try v4l2-ctl --list-devices first
            result = self.process_runner.run_command(
                ["v4l2-ctl", "--list-devices"],
                timeout_ms=5000,
            )

            if result and result.returncode == 0:
                # Basic parsing to group devices and filter duplicates
                camera_groups = {}
                current_camera = None

                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue

                    if line.endswith(":"):
                        # Camera name line
                        import re

                        camera_name = re.sub(r"\s*\([^)]*\):?$", "", line).strip()
                        current_camera = camera_name
                        camera_groups[current_camera] = []
                    elif line.startswith("/dev/video") and current_camera:
                        camera_groups[current_camera].append(line)

                # For each camera group, keep only the first device (main capture)
                for camera_name, device_paths in camera_groups.items():
                    if device_paths:
                        # Sort and pick the first device (typically the main capture device)
                        device_path = sorted(device_paths)[0]
                        device_num = device_path.replace("/dev/video", "")

                        video_devices.append(
                            {"path": device_path, "name": camera_name, "number": device_num, "capabilities": "unknown", "is_capture_device": True}
                        )

                        self.logger.debug(f"Fallback detected: {camera_name} at {device_path}")

            else:
                # Final fallback: just scan /dev/video* devices
                self._basic_device_scan(video_devices)

        except Exception as e:
            self.logger.warning(f"Fallback v4l2-ctl failed: {e}")
            self._basic_device_scan(video_devices)

        return video_devices

    def _basic_device_scan(self, video_devices: List[Dict[str, str]]) -> None:
        """Most basic device scanning as final fallback."""
        video_dir = Path("/dev")

        for device in video_dir.glob("video*"):
            if device.is_char_device():
                device_num = device.name.replace("video", "")
                try:
                    # Simple even-number heuristic to avoid metadata devices
                    if int(device_num) % 2 == 0:
                        device_name = f"Camera {device_num}"
                        video_devices.append(
                            {"path": str(device), "name": device_name, "number": device_num, "capabilities": "unknown", "is_capture_device": True}
                        )
                        self.logger.debug(f"Basic scan found: {device_name} at {device}")
                except ValueError:
                    # Skip devices with non-numeric suffixes
                    pass

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            camera_tested = self.state.get_user_input("camera_tested", False)
            pov_complete = self.state.get_user_input("pov_picture_complete", False)

            if not camera_tested:
                QMessageBox.warning(self, "Camera Not Tested", "Please test the camera before continuing.")
                return

            if not pov_complete:
                QMessageBox.warning(self, "POV Picture Not Captured", "Please capture the POV baseline picture before continuing.")
                return

            camera_path = self.state.get_user_input("selected_camera", "")
            camera_name = self.state.get_user_input("selected_camera_name", "")

            self.logger.info(f"Camera setup completed with: {camera_name} ({camera_path})")

            # Save notes if any
            notes = self.notes_text.toPlainText().strip()
            if notes:
                self.state.set_user_input("camera_setup_notes", notes)
                self._save_notes_to_file("Camera Setup", notes)

            # Final state persistence
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.request_next_step.emit()

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete camera setup step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Complete all camera setup tasks first",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the camera setup step with state restoration."""
        super().activate_step()

        self.logger.info("Camera setup step activated")

        # Load any saved notes
        saved_notes = self.state.get_user_input("camera_setup_notes", "")
        if saved_notes:
            self.notes_text.setText(saved_notes)

        # Check if already completed
        camera_tested = self.state.get_user_input("camera_tested", False)
        pov_complete = self.state.get_user_input("pov_picture_complete", False)

        if camera_tested and pov_complete:
            selected_camera_name = self.state.get_user_input("selected_camera_name", "")
            self.camera_status.setText(f"Camera detected and test passed")
            self.pov_status.setText("POV picture already captured")
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)
            self.logger.info("Camera setup already completed, skipping")
            self.retest_button.setEnabled(True)
            return

        # Auto-detect and test camera on first activation
        if not self.cameras_detected:
            # Small delay to let UI render first
            QTimer.singleShot(500, self._run_camera_detection_and_test)

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()

        # Update continue button state based on completion
        has_camera = bool(self.state.get_user_input("selected_camera"))
        camera_tested = self.state.get_user_input("camera_tested", False)
        pov_complete = self.state.get_user_input("pov_picture_complete", False)
        self.continue_button.setEnabled(has_camera and camera_tested and pov_complete)

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Stop monitoring
            self.monitor_timer.stop()

            # Clean up cheese process
            if self.cheese_process:
                try:
                    if self.cheese_process.poll() is None:
                        self.cheese_process.terminate()
                        self.cheese_process.wait(timeout=5)
                except Exception as e:
                    self.logger.warning(f"Error cleaning up cheese process: {e}")
                finally:
                    self.cheese_process = None

            # Clean up image viewer
            if self.image_viewer_process:
                try:
                    self.image_viewer_process.terminate()
                    self.image_viewer_process.wait(timeout=5)
                except Exception as e:
                    self.logger.warning(f"Error cleaning up image viewer: {e}")
                finally:
                    self.image_viewer_process = None

            # Delete temp file if it still exists
            if hasattr(self, "temp_image_path") and self.temp_image_path and os.path.exists(self.temp_image_path):
                try:
                    os.remove(self.temp_image_path)
                    self.logger.info("Cleaned up temporary POV file")
                except Exception as e:
                    self.logger.warning(f"Could not delete temp file during cleanup: {e}")

            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Camera setup step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
