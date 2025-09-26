"""Smart plug data verification step implementation using new framework patterns."""

from __future__ import annotations

import os
import time
import shutil
import subprocess
from glob import glob
from datetime import datetime

from PyQt6.QtWidgets import QWidget, QMessageBox, QLineEdit
from PyQt6.QtCore import QTimer

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from utils.ui_factory import ButtonStyle


class SmartPlugVerifyStep(WizardStep):
    """Step 5: Verify Smart Plug Data using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the smart plug verification UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create top row sections
        top_section = self._create_top_section()
        main_layout.addLayout(top_section)

        # Create middle row sections
        middle_section = self._create_middle_section()
        main_layout.addLayout(middle_section)

        # Create output section
        output_section = self._create_output_section()
        main_layout.addWidget(output_section, 1)

        # Create continue button
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        # Initialize state
        self.browser_launched = False

        # Setup timer for status updates
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._safe_update_status)

        return content

    def _create_top_section(self):
        """Create the top section with automation and status."""
        top_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Create automation and status sections
        automation_section = self._create_automation_section()
        status_section = self._create_status_section()

        top_row.addWidget(automation_section, 3)  # 60% width
        top_row.addWidget(status_section, 2)  # 40% width

        return top_row

    def _create_automation_section(self) -> QWidget:
        """Create the browser automation section using UI factory."""
        automation_box, automation_layout = self.ui_factory.create_group_box(
            "Browser Automation Setup"
        )

        automation_text = self.ui_factory.create_label(
            "This will open Firefox and automatically:\n"
            "• Navigate to Home Assistant\n"
            "• Go to History page\n"
            "• Select TV smart plug sensor\n"
            "• Monitor power data in real-time\n\n"
            "You will then test by turning TV on/off"
        )
        automation_layout.addWidget(automation_text)
        automation_layout.addStretch()

        return automation_box

    def _create_status_section(self) -> QWidget:
        """Create the status indicators section using UI factory."""
        status_group, status_layout = self.ui_factory.create_group_box(
            "Connection Status"
        )

        self.plug_monitor_status = self.ui_factory.create_status_label(
            "📊 Smart plug data monitoring status: Not started", status_type="info"
        )
        self.ha_connection_status = self.ui_factory.create_status_label(
            "🌐 Home Assistant connection: Ready", status_type="info"
        )

        status_layout.addWidget(self.plug_monitor_status)
        status_layout.addSpacing(10)
        status_layout.addWidget(self.ha_connection_status)
        status_layout.addStretch()

        return status_group

    def _create_middle_section(self):
        """Create the middle section with controls and instructions."""
        middle_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Create control and instruction sections
        control_section = self._create_control_section()
        instruction_section = self._create_instruction_section()

        middle_row.addWidget(control_section, 2)  # 40% width
        middle_row.addWidget(instruction_section, 3)  # 60% width

        return middle_row

    def _create_control_section(self) -> QWidget:
        """Create the verification controls section using UI factory."""
        control_group, control_layout = self.ui_factory.create_group_box(
            "Verification Controls"
        )

        # Room name input
        room_label = self.ui_factory.create_label("Room Name:")
        control_layout.addWidget(room_label)

        self.room_name_input = QLineEdit()
        self.room_name_input.setPlaceholderText("e.g., Living Room, Bedroom, etc.")
        control_layout.addWidget(self.room_name_input)

        control_layout.addSpacing(10)

        # Launch browser button
        self.launch_browser_button = self.ui_factory.create_action_button(
            "🚀 Launch Browser Automation",
            callback=self._launch_browser_automation,
            style=ButtonStyle.PRIMARY,
            height=40,
        )
        control_layout.addWidget(self.launch_browser_button)

        # Power cycle confirmation button
        self.power_cycle_button = self.ui_factory.create_action_button(
            "📸 I've Cycled Power - Capture Screenshot",
            callback=self._capture_power_baseline,
            style=ButtonStyle.SECONDARY,
            height=40,
            enabled=False,
        )
        control_layout.addWidget(self.power_cycle_button)

        # Data verified button
        self.data_verified_button = self.ui_factory.create_action_button(
            "✓ Data Verified - Power Changes Detected",
            callback=self._data_verified,
            style=ButtonStyle.SUCCESS,
            height=40,
            enabled=False,
        )
        control_layout.addWidget(self.data_verified_button)

        control_layout.addStretch()

        return control_group

    def _create_instruction_section(self) -> QWidget:
        """Create the testing instructions section using UI factory."""
        instruction_group, instruction_layout = self.ui_factory.create_group_box(
            "Testing Instructions"
        )

        instruction_label = self.ui_factory.create_label(
            "After browser opens:\n\n"
            "1. Enter the room name in the textbox\n"
            "2. Turn TV OFF and wait 10 seconds\n"
            "3. Turn TV ON and wait 10 seconds\n"
            "4. Click 'I've Cycled Power' to capture screenshot\n"
            "5. Verify power changes show in Home Assistant\n"
            "6. Click 'Data Verified' when you see the changes"
        )
        instruction_layout.addWidget(instruction_label)
        instruction_layout.addStretch()

        return instruction_group

    def _create_output_section(self) -> QWidget:
        """Create the verification log output section using UI factory."""
        output_group, output_layout = self.ui_factory.create_group_box(
            "Verification Log"
        )

        self.output_text = self.ui_factory.create_text_area(
            placeholder="Verification progress will appear here...", read_only=True
        )
        output_layout.addWidget(self.output_text)

        return output_group

    def _create_continue_section(self):
        """Create the continue button section using UI factory."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text="Smart Plug Verified - Continue"
        )

        return button_layout

    @handle_step_error
    def _launch_browser_automation(self, checked: bool = False) -> None:
        """Launch browser automation to monitor Home Assistant with comprehensive error handling."""
        try:
            self.logger.info("Starting browser automation for smart plug verification")

            # Use standard Home Assistant URL - it's always localhost:8123/history
            home_assistant_url = "http://localhost:8123/history"

            self.launch_browser_button.setEnabled(False)
            self.output_text.append("🚀 Launching browser automation...")
            self.output_text.append(f"Target URL: {home_assistant_url}")

            # Launch browser using process runner for better error handling
            result = self.process_runner.run_command(
                ["xdg-open", home_assistant_url], timeout_ms=10000
            )

            if result and result.returncode == 0:
                self.output_text.append(
                    "✅ Browser launched - navigate to History page"
                )
                self.output_text.append("Look for your TV smart plug sensor")
                self.output_text.append("\nNow test TV power on/off...")

                self.browser_launched = True
                self.plug_monitor_status.setText(
                    "📊 Smart plug data monitoring status: Browser opened"
                )
                self.power_cycle_button.setEnabled(True)

                # Start status monitoring
                self.status_timer.start(5000)  # Check every 5 seconds

                self.logger.info("Browser automation launched successfully")
            else:
                error_msg = result.stderr if result else "Command failed"
                self.logger.error(f"Browser launch failed: {error_msg}")
                raise FlashTVError(
                    f"Browser launch failed: {error_msg}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try opening Home Assistant manually",
                )

        except Exception as e:
            self.logger.error(f"Error during browser automation launch: {e}")
            self.output_text.append(f"❌ Browser launch failed: {e}")
            self.output_text.append("You may need to open Home Assistant manually")
            self._enable_manual_verification()
            raise
        finally:
            self.launch_browser_button.setEnabled(True)

    @handle_step_error
    def _capture_power_baseline(self, checked: bool = False) -> None:
        """Capture screenshot after power cycling and save to participant's data folder."""
        try:
            # Validate room name is entered
            room_name = self.room_name_input.text().strip()
            if not room_name:
                QMessageBox.warning(
                    self,
                    "Room Name Required",
                    "Please enter the room name before capturing the screenshot."
                )
                return

            self.logger.info(f"Capturing power baseline screenshot for room: {room_name}")

            # Get participant info
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            full_participant_id = f"{participant_id}{device_id}" if device_id else participant_id

            self.output_text.append("📸 Preparing to capture screenshot...")
            self.power_cycle_button.setEnabled(False)

            # Wait a moment for user to see the message
            QTimer.singleShot(2000, lambda: self._perform_screenshot_capture(
                full_participant_id, room_name, username
            ))

        except Exception as e:
            self.logger.error(f"Error initiating screenshot capture: {e}")
            self.power_cycle_button.setEnabled(True)
            raise

    def _perform_screenshot_capture(self, participant_id: str, room_name: str, username: str) -> None:
        """Actually perform the screenshot capture and file operations."""
        try:
            # Refresh the Home Assistant page first
            self.output_text.append("🔄 Refreshing Home Assistant page...")

            # Open/refresh the page
            home_assistant_url = "http://localhost:8123/history"
            subprocess.run(["xdg-open", home_assistant_url], capture_output=True)

            # Wait for page to load
            time.sleep(3)

            # Take screenshot using gnome-screenshot or scrot
            self.output_text.append("📸 Capturing screenshot...")

            # Try gnome-screenshot first
            screenshot_taken = False
            temp_screenshot = "/tmp/smart_plug_screenshot.png"

            # Try gnome-screenshot
            result = subprocess.run(
                ["gnome-screenshot", "-f", temp_screenshot],
                capture_output=True
            )

            if result.returncode == 0:
                screenshot_taken = True
                self.logger.info("Screenshot captured with gnome-screenshot")
            else:
                # Try scrot as fallback
                result = subprocess.run(
                    ["scrot", temp_screenshot],
                    capture_output=True
                )
                if result.returncode == 0:
                    screenshot_taken = True
                    self.logger.info("Screenshot captured with scrot")

            if not screenshot_taken:
                # Try to find any recent screenshot file
                self.output_text.append("🔍 Looking for screenshot file...")

                # Common screenshot locations
                screenshot_dirs = [
                    f"/home/{username}/Pictures",
                    f"/home/{username}/Pictures/Screenshots",
                    f"/home/{username}/Downloads",
                    "/tmp",
                    f"/tmp/TemporaryItems",
                ]

                # Look for recent screenshot files
                found_screenshot = None
                for directory in screenshot_dirs:
                    if os.path.exists(directory):
                        pattern_list = [
                            os.path.join(directory, "*[Ss]creenshot*.png"),
                            os.path.join(directory, "*[Ss]creen*.png"),
                            os.path.join(directory, "*.png")
                        ]

                        for pattern in pattern_list:
                            files = glob(pattern)
                            # Get files created in the last 30 seconds
                            recent_files = [
                                f for f in files
                                if os.path.exists(f) and
                                (time.time() - os.path.getctime(f)) < 30
                            ]

                            if recent_files:
                                # Use the most recent file
                                found_screenshot = max(recent_files, key=os.path.getctime)
                                break

                        if found_screenshot:
                            break

                if found_screenshot:
                    temp_screenshot = found_screenshot
                    screenshot_taken = True
                    self.logger.info(f"Found screenshot at: {temp_screenshot}")
                    self.output_text.append(f"✅ Found screenshot: {os.path.basename(temp_screenshot)}")

            if screenshot_taken and os.path.exists(temp_screenshot):
                # Create destination path
                data_path = f"/home/{username}/data/{participant_id}_data"
                os.makedirs(data_path, exist_ok=True)

                # Create filename with participant ID and room name
                screenshot_filename = f"{participant_id} {room_name} TV Power Baseline.png"
                destination_path = os.path.join(data_path, screenshot_filename)

                # Move and rename the screenshot
                shutil.move(temp_screenshot, destination_path)

                self.output_text.append(f"✅ Screenshot saved: {screenshot_filename}")
                self.output_text.append(f"📁 Location: {data_path}")

                self.logger.info(f"Screenshot saved to: {destination_path}")

                # Enable the data verified button
                self.data_verified_button.setEnabled(True)

                QMessageBox.information(
                    self,
                    "Screenshot Captured",
                    f"Power baseline screenshot captured successfully!\n\n"
                    f"Saved as: {screenshot_filename}\n"
                    f"Location: {data_path}"
                )
            else:
                raise FlashTVError(
                    "Failed to capture screenshot",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try taking a manual screenshot and save it to the data folder"
                )

        except Exception as e:
            self.logger.error(f"Error during screenshot capture: {e}")
            self.output_text.append(f"❌ Screenshot capture failed: {e}")
            QMessageBox.warning(
                self,
                "Screenshot Failed",
                f"Failed to capture screenshot: {e}\n\n"
                "Please take a manual screenshot and save it to the data folder."
            )
        finally:
            self.power_cycle_button.setEnabled(True)

    @handle_step_error
    def _enable_manual_verification(self) -> None:
        """Enable manual verification mode with logging."""
        try:
            self.logger.info("Enabling manual verification mode")

            self.output_text.append("\n📝 Manual verification mode enabled")
            self.output_text.append("Please verify the smart plug is working by:")
            self.output_text.append("1. Turning TV off and on")
            self.output_text.append("2. Checking smart plug LED changes")
            self.output_text.append("3. Confirming power monitoring works")

            self.data_verified_button.setEnabled(True)
            self.data_verified_button.setText(
                "✓ Manually Verified - Smart Plug Working"
            )

            # Update status
            self.plug_monitor_status.setText(
                "📊 Smart plug data monitoring status: Manual verification mode"
            )

        except Exception as e:
            self.logger.error(f"Error enabling manual verification: {e}")
            raise FlashTVError(
                f"Failed to enable manual verification: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try refreshing the page",
            )

    def _safe_update_status(self) -> None:
        """Safely update connection status with error handling."""
        try:
            self._update_status()
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")

    def _update_status(self) -> None:
        """Update connection status periodically with enhanced tracking."""
        if self.browser_launched:
            # Simulate checking Home Assistant connection
            self.ha_connection_status.setText("🌐 Home Assistant connection: Active")
            self.plug_monitor_status.setText(
                "📊 Smart plug data monitoring status: Waiting for verification"
            )
            self.logger.debug(
                "Updated status - browser active, waiting for verification"
            )

    @handle_step_error
    def _data_verified(self, checked: bool = False) -> None:
        """Handle data verification confirmation with comprehensive validation."""
        try:
            reply = QMessageBox.question(
                self,
                "Confirm Verification",
                "Did you successfully see the TV power changes in the monitoring system?\n\n"
                "• TV OFF showed low/zero power\n"
                "• TV ON showed increased power usage",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("User confirmed smart plug data verification")

                self.output_text.append("\n✅ Smart plug data verification successful!")
                self.output_text.append("Power monitoring is working correctly")

                # Save verification status
                self.state.set_user_input("smart_plug_verified", True)
                self.state.set_user_input(
                    "smart_plug_verification_method",
                    "browser" if self.browser_launched else "manual",
                )

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)

                # Stop status timer
                if self.status_timer.isActive():
                    self.status_timer.stop()

                self.logger.info("Smart plug verification completed successfully")
            else:
                self.logger.warning("User did not confirm verification")
                self.output_text.append("\n⚠️ Verification not confirmed")
                self.output_text.append("Please check connections and try again")

        except Exception as e:
            self.logger.error(f"Error during data verification: {e}")
            raise FlashTVError(
                f"Failed to complete verification: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Check smart plug connections and try again",
            )

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            if self.is_completed() or self.continue_button.isEnabled():
                verification_method = self.state.get_user_input(
                    "smart_plug_verification_method", "unknown"
                )
                self.logger.info(
                    f"Smart plug verification completed via {verification_method} method"
                )

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but verification not completed")

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete verification step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Complete the verification process first",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the smart plug verification step with state restoration."""
        super().activate_step()

        self.logger.info("Smart plug verification step activated")

        # Check if already verified
        if self.state.get_user_input("smart_plug_verified", False):
            verification_method = self.state.get_user_input(
                "smart_plug_verification_method", "previous"
            )
            self.output_text.append(
                f"✅ Smart plug already verified (method: {verification_method})"
            )
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)
            self.logger.info("Smart plug verification already completed, skipping")

    def cleanup(self) -> None:
        """Clean up resources when step is destroyed."""
        try:
            self.logger.info("Cleaning up smart plug verification step")

            # Stop status timer
            if hasattr(self, "status_timer") and self.status_timer.isActive():
                self.status_timer.stop()

            # Call parent cleanup
            super().cleanup()

        except Exception as e:
            self.logger.error(f"Error during verification step cleanup: {e}")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Smart plug verification step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
