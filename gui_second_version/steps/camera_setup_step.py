"""Camera setup step implementation using new framework patterns."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QWidget, QListWidget, QListWidgetItem

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from constants import UI, Messages
from utils.ui_factory import ButtonStyle


class CameraSetupStep(WizardStep):
    """Step 3: Camera Detection and Setup using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the camera setup UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections using UI factory
        detection_section = self._create_detection_section()
        test_section = self._create_test_section()

        main_layout.addWidget(detection_section)
        main_layout.addWidget(test_section)

        # Add stretch to push button to bottom
        main_layout.addStretch()

        # Continue button using UI factory
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        # Auto-detect cameras on activation
        self.cameras_detected = False

        return content

    def _create_detection_section(self) -> QWidget:
        """Create the camera detection section using UI factory."""
        detection_group, detection_layout = self.ui_factory.create_group_box(
            UI.CAMERA_DETECTION
        )

        # Detection button
        self.detect_button = self.ui_factory.create_action_button(
            UI.DETECT_AVAILABLE_CAMERAS,
            callback=self._detect_cameras,
            style=ButtonStyle.PRIMARY,
            height=35,
        )
        detection_layout.addWidget(self.detect_button)

        # Camera list label
        camera_label = self.ui_factory.create_label(UI.AVAILABLE_CAMERAS)
        detection_layout.addWidget(camera_label)

        # Camera list
        self.camera_list = QListWidget()
        self.camera_list.setMinimumHeight(120)
        self.camera_list.itemSelectionChanged.connect(self._on_camera_selection_changed)
        detection_layout.addWidget(self.camera_list)

        return detection_group

    def _create_test_section(self) -> QWidget:
        """Create the camera test section using UI factory."""
        test_group, test_layout = self.ui_factory.create_group_box(UI.CAMERA_TEST)

        # Test button
        self.test_button = self.ui_factory.create_action_button(
            UI.TEST_SELECTED_CAMERA,
            callback=self._test_camera,
            style=ButtonStyle.SUCCESS,
            height=35,
            enabled=False,
        )
        test_layout.addWidget(self.test_button)

        # Test output
        test_output_label = self.ui_factory.create_label(UI.TEST_OUTPUT)
        test_layout.addWidget(test_output_label)

        self.test_output = self.ui_factory.create_text_area(
            placeholder="Camera test results will appear here...",
            max_height=150,
            read_only=True,
        )
        test_layout.addWidget(self.test_output)

        return test_group

    def _create_continue_section(self):
        """Create the continue button section using UI factory."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text=UI.CONTINUE_TO_NEXT_STEP
        )

        return button_layout

    @handle_step_error
    def _detect_cameras(self, checked: bool = False) -> None:
        """Detect available cameras with comprehensive error handling and duplicate filtering."""
        try:
            self.logger.info("Starting camera detection")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.detect_button.setEnabled(False)
            self.camera_list.clear()
            self.test_output.clear()
            self.test_output.append("🔍 Scanning for unique cameras...")

            # Import the improved camera detection utility
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python_scripts'))
            
            try:
                from utils.camera_detection_utils import get_unique_cameras
                
                # Use improved camera detection that filters duplicates
                unique_cameras = get_unique_cameras()
                video_devices = []
                
                for camera in unique_cameras:
                    video_devices.append({
                        "path": camera['path'],
                        "name": camera['name'],
                        "number": camera['number'],
                        "capabilities": camera.get('capabilities', 'unknown'),
                        "is_capture_device": camera.get('is_capture_device', True)
                    })
                    self.logger.debug(
                        f"Detected unique camera: {camera['name']} at {camera['path']} "
                        f"(capabilities: {camera.get('capabilities', 'unknown')})"
                    )
                
                self.logger.info(f"Found {len(video_devices)} unique cameras (duplicates filtered)")
                
            except ImportError as e:
                self.logger.warning(f"Could not import improved camera detection: {e}")
                self.test_output.append("⚠️ Using fallback detection method...")
                
                # Simple fallback using basic v4l2-ctl --list-devices approach
                video_devices = self._fallback_camera_detection()

            # Populate camera list with enhanced information
            for camera in video_devices:
                display_text = f"{camera['name']} ({camera['path']})"
                if camera.get('capabilities') and camera['capabilities'] != 'unknown':
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
                self.update_status(StepStatus.USER_ACTION_REQUIRED)
                self.test_output.append(
                    Messages.FOUND_CAMERAS.format(count=len(video_devices))
                )
                self.logger.info(f"Found {len(video_devices)} cameras")
            else:
                self.update_status(StepStatus.FAILED)
                self.test_output.append(Messages.NO_CAMERAS_DETECTED)
                self.logger.warning("No cameras detected")
                raise FlashTVError(
                    "No cameras detected on system",
                    ErrorType.SYSTEM_ERROR,
                    recovery_action="Check camera connections and try again",
                )

        except Exception as e:
            self.logger.error(f"Error during camera detection: {e}")
            self.update_status(StepStatus.FAILED)
            self.test_output.append(Messages.ERROR_DETECTING_CAMERAS.format(error=e))
            raise

        finally:
            self.detect_button.setEnabled(True)

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

                self.test_button.setEnabled(True)
                self.logger.info(f"Selected camera: {camera_name} ({camera_path})")
            else:
                self.test_button.setEnabled(False)
                self.continue_button.setEnabled(False)
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
            if not camera_path:
                self.logger.warning("No camera selected for testing")
                return

            self.logger.info(f"Testing camera: {camera_path}")
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.test_button.setEnabled(False)
            self.test_output.clear()
            self.test_output.append(Messages.TESTING_CAMERA.format(path=camera_path))

            # Test camera with v4l2-ctl using process runner
            result = self.process_runner.run_command(
                ["v4l2-ctl", "--device", camera_path, "--list-formats-ext"],
                timeout_ms=10000,
            )

            if result and result.returncode == 0:
                self.test_output.append(Messages.CAMERA_TEST_SUCCESSFUL)
                self.test_output.append(Messages.SUPPORTED_FORMATS)
                self.test_output.append(result.stdout)
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
                    self.test_output.append(Messages.FRAME_CAPTURE_SUCCESS)

                    # Save successful test status
                    self.state.set_user_input("camera_tested", True)

                    # Persist state
                    if self.state_manager:
                        self.state_manager.save_state(self.state)

                    self.update_status(StepStatus.COMPLETED)
                    self.continue_button.setEnabled(True)
                    self.logger.info("Camera test completed successfully")
                else:
                    error_msg = test_result.stderr if test_result else "Unknown error"
                    self.test_output.append(
                        Messages.FRAME_CAPTURE_FAILED.format(error=error_msg)
                    )
                    self.update_status(StepStatus.USER_ACTION_REQUIRED)
                    self.logger.warning(f"Frame capture failed: {error_msg}")
            else:
                error_msg = result.stderr if result else "Command failed"
                self.test_output.append(
                    Messages.CAMERA_TEST_FAILED.format(error=error_msg)
                )
                self.update_status(StepStatus.FAILED)
                self.logger.error(f"Camera test failed: {error_msg}")
                raise FlashTVError(
                    f"Camera test failed: {error_msg}",
                    ErrorType.SYSTEM_ERROR,
                    recovery_action="Try a different camera or check connections",
                )

        except Exception as e:
            self.logger.error(f"Error testing camera: {e}")
            self.test_output.append(Messages.ERROR_TESTING_CAMERA.format(error=e))
            self.update_status(StepStatus.FAILED)
            raise

        finally:
            self.test_button.setEnabled(True)

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
                
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line.endswith(':'):
                        # Camera name line
                        import re
                        camera_name = re.sub(r'\s*\([^)]*\):?$', '', line).strip()
                        current_camera = camera_name
                        camera_groups[current_camera] = []
                    elif line.startswith('/dev/video') and current_camera:
                        camera_groups[current_camera].append(line)
                
                # For each camera group, keep only the first device (main capture)
                for camera_name, device_paths in camera_groups.items():
                    if device_paths:
                        # Sort and pick the first device (typically the main capture device)
                        device_path = sorted(device_paths)[0]
                        device_num = device_path.replace('/dev/video', '')
                        
                        video_devices.append({
                            "path": device_path,
                            "name": camera_name,
                            "number": device_num,
                            "capabilities": "unknown",
                            "is_capture_device": True
                        })
                        
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
                        video_devices.append({
                            "path": str(device),
                            "name": device_name,
                            "number": device_num,
                            "capabilities": "unknown",
                            "is_capture_device": True
                        })
                        self.logger.debug(f"Basic scan found: {device_name} at {device}")
                except ValueError:
                    # Skip devices with non-numeric suffixes
                    pass

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            if self.is_completed() and self.continue_button.isEnabled():
                camera_path = self.state.get_user_input("selected_camera", "")
                camera_name = self.state.get_user_input("selected_camera_name", "")

                self.logger.info(
                    f"Camera setup completed with: {camera_name} ({camera_path})"
                )

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but camera setup not completed")

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete camera setup step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Complete camera testing first",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the camera setup step with state restoration."""
        super().activate_step()

        self.logger.info("Camera setup step activated")

        # Check if already completed
        if self.state.get_user_input("camera_tested", False):
            selected_camera = self.state.get_user_input("selected_camera", "")
            if selected_camera:
                self.test_output.append(f"✅ Camera already tested: {selected_camera}")
                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)
                self.logger.info("Camera setup already completed, skipping")
                return

        # Auto-detect cameras if not done yet
        if not self.cameras_detected:
            self._detect_cameras()

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()

        # Update continue button state based on completion
        has_camera = bool(self.state.get_user_input("selected_camera"))
        camera_tested = self.state.get_user_input("camera_tested", False)
        self.continue_button.setEnabled(has_camera and camera_tested)

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Camera setup step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
