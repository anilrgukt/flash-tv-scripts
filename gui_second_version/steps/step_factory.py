"""Factory for creating step instances with their definitions."""

from __future__ import annotations

from core import WizardStep
from models import (
    StepDefinition,
    StepContentType,
    ValidationRule,
    WizardState,
)
from steps.participant_setup_step import ParticipantSetupStep
from steps.wifi_connection_step import WiFiConnectionStep
from steps.time_sync_step import TimeSyncStep
from steps.smart_plug_physical_step import SmartPlugPhysicalStep
from steps.smart_plug_verify_step import SmartPlugVerifyStep
from steps.camera_setup_step import CameraSetupStep
from steps.pov_picture_step import POVPictureStep
from steps.gallery_creation_step import GalleryCreationStep
from steps.gaze_detection_testing_step import GazeDetectionTestingStep
from steps.log_file_verification_step import LogFileVerificationStep
from steps.cord_checking_step import CordCheckingStep
from steps.screen_locking_step import ScreenLockingStep


class StepFactory:
    """Factory for creating wizard steps with their configurations."""

    @staticmethod
    def create_step_definitions() -> list[StepDefinition]:
        """Create all step definitions for the FLASH-TV setup wizard."""
        return [
            # Step 1: Participant Setup
            StepDefinition(
                step_id=1,
                title="Participant and Device Setup",
                description="Enter participant information and configure device settings.",
                content_type=StepContentType.MANUAL,
                prerequisites=[],
                validation_rules=[
                    ValidationRule.participant_id_rule(),
                    ValidationRule.custom_rule(
                        "device_id",
                        lambda x: len(str(x).strip()) > 0,
                        "Device ID cannot be empty",
                    ),
                    ValidationRule.custom_rule(
                        "username",
                        lambda x: len(str(x).strip()) > 0,
                        "Username cannot be empty",
                    ),
                    ValidationRule.directory_exists_rule("data_path"),
                ],
            ),
            # Step 2: WiFi Connection
            StepDefinition(
                step_id=2,
                title="WiFi Connection Setup",
                description="Configure WiFi connection for network connectivity.",
                content_type=StepContentType.MIXED,
                prerequisites=[1],
                validation_rules=[],
            ),
            # Step 3: Time Synchronization
            StepDefinition(
                step_id=3,
                title="Time Synchronization",
                description="Synchronize system time with network time servers.",
                content_type=StepContentType.AUTOMATED,
                prerequisites=[1, 2],
                validation_rules=[],
            ),
            # Step 4: Smart Plug Physical Setup
            StepDefinition(
                step_id=4,
                title="Smart Plug Physical Setup",
                description="Connect and configure the smart plug hardware.",
                content_type=StepContentType.MANUAL,
                prerequisites=[1, 2, 3],
                validation_rules=[],
            ),
            # Step 5: Smart Plug Data Verification
            StepDefinition(
                step_id=5,
                title="Smart Plug Data Verification",
                description="Verify smart plug data collection and Home Assistant integration.",
                content_type=StepContentType.MIXED,
                prerequisites=[1, 2, 3, 4],
                validation_rules=[],
            ),
            # Step 6: Camera Setup
            StepDefinition(
                step_id=6,
                title="Camera Detection and Setup",
                description="Detect camera devices and configure camera settings.",
                content_type=StepContentType.MANUAL,
                prerequisites=[1, 2, 3, 4, 5],
                validation_rules=[],
            ),
            # Step 7: POV Picture
            StepDefinition(
                step_id=7,
                title="Point of View Picture",
                description="Capture POV picture documenting camera perspective.",
                content_type=StepContentType.MANUAL,
                prerequisites=[1, 2, 3, 4, 5, 6],
                validation_rules=[],
            ),
            # Step 8: Face Gallery Building
            StepDefinition(
                step_id=8,
                title="Face Gallery Building",
                description="Create face gallery for family member recognition.",
                content_type=StepContentType.MIXED,
                prerequisites=[1, 2, 3, 4, 5, 6, 7],
                validation_rules=[],
            ),
            # Step 9: Gaze Detection Testing
            StepDefinition(
                step_id=9,
                title="Gaze Detection Testing",
                description="Test gaze detection system functionality.",
                content_type=StepContentType.MIXED,
                prerequisites=[1, 2, 3, 4, 5, 6, 7, 8],
                validation_rules=[],
            ),
            # Step 10: Log File Verification
            StepDefinition(
                step_id=10,
                title="Log File Verification",
                description="Verify log file generation and data collection.",
                content_type=StepContentType.AUTOMATED,
                prerequisites=[1, 2, 3, 4, 5, 6, 7, 8, 9],
                validation_rules=[],
            ),
            # Step 11: Cord Checking
            StepDefinition(
                step_id=11,
                title="Cord and Connection Check",
                description="Verify all power cords and cable connections are secure.",
                content_type=StepContentType.MANUAL,
                prerequisites=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                validation_rules=[],
            ),
            # Step 12: Screen Locking
            StepDefinition(
                step_id=12,
                title="Screen Locking and Final Setup",
                description="Lock the screen and prepare system for autonomous operation.",
                content_type=StepContentType.MANUAL,
                prerequisites=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                validation_rules=[],
            ),
        ]

    @staticmethod
    def create_step_instance(
        step_definition: StepDefinition, state: WizardState, process_runner, 
        state_manager=None, parent=None
    ) -> WizardStep:
        """Create a step instance based on the step definition."""

        # Map step IDs to their implementation classes
        step_classes = {
            1: ParticipantSetupStep,
            2: WiFiConnectionStep,
            3: TimeSyncStep,
            4: SmartPlugPhysicalStep,
            5: SmartPlugVerifyStep,
            6: CameraSetupStep,
            7: POVPictureStep,
            8: GalleryCreationStep,
            9: GazeDetectionTestingStep,
            10: LogFileVerificationStep,
            11: CordCheckingStep,
            12: ScreenLockingStep,
        }

        step_class = step_classes.get(step_definition.step_id)

        if step_class:
            return step_class(step_definition, state, process_runner, state_manager, parent)
        else:
            # Return a generic step for unimplemented steps
            return GenericWizardStep(step_definition, state, process_runner, state_manager, parent)


class GenericWizardStep(WizardStep):
    """Generic step implementation for steps that don't have custom implementations yet."""

    def create_content_widget(self):
        """Create a placeholder content widget."""
        from PyQt6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget

        content = QWidget()
        layout = QVBoxLayout(content)

        # Placeholder message
        message = QLabel(
            f"Step {self.step_definition.step_id} implementation is in progress."
        )
        message.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
        layout.addWidget(message)

        # Skip button for testing
        skip_button = QPushButton("Skip This Step (Development Mode)")
        skip_button.clicked.connect(self._skip_step)
        layout.addWidget(skip_button)

        return content

    def _skip_step(self):
        """Skip this step for development purposes."""
        from models import StepStatus

        self.update_status(StepStatus.COMPLETED)
        self.request_next_step.emit()

    def activate_step(self):
        """Activate the generic step."""
        from models import StepStatus

        super().activate_step()
        self.update_status(StepStatus.USER_ACTION_REQUIRED)
