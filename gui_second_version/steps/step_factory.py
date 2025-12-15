"""Factory for creating step instances with their definitions."""

from __future__ import annotations

from core import WizardStep as WizardStepBase
from models import (
    StepContentType,
    StepDefinition,
    ValidationRule,
    WizardState,
)
from models.state_keys import WizardStep
from steps.camera_setup_step import CameraSetupStep
from steps.cord_checking_step import CordCheckingStep
from steps.device_locking_step import DeviceLockingStep
from steps.gallery_creation_step import GalleryCreationStep
from steps.gaze_detection_testing_step import GazeDetectionTestingStep
from steps.participant_setup_step import ParticipantSetupStep
from steps.service_startup_step import ServiceStartupStep
from steps.smart_plug_physical_step import SmartPlugPhysicalStep
from steps.smart_plug_verify_step import SmartPlugVerifyStep
from steps.time_sync_step import TimeSyncStep
from steps.wifi_connection_step import WiFiConnectionStep


class StepFactory:
    """Factory for creating wizard steps with their configurations."""

    @staticmethod
    def create_step_definitions() -> list[StepDefinition]:
        """Create all step definitions for the FLASH-TV setup wizard using type-safe WizardStep enums."""
        return [
            # Step 1: Participant Setup
            StepDefinition(
                step_id=WizardStep.PARTICIPANT_SETUP,
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
                step_id=WizardStep.WIFI_CONNECTION,
                title="WiFi Connection Setup",
                description="Configure WiFi connection for network connectivity.",
                content_type=StepContentType.MIXED,
                prerequisites=[WizardStep.PARTICIPANT_SETUP],
                validation_rules=[],
            ),
            # Step 3: Time Synchronization
            StepDefinition(
                step_id=WizardStep.TIME_SYNC,
                title="Time Synchronization",
                description="Synchronize system time with network time servers.",
                content_type=StepContentType.AUTOMATED,
                prerequisites=[
                    WizardStep.PARTICIPANT_SETUP,
                    WizardStep.WIFI_CONNECTION,
                ],
                validation_rules=[],
            ),
            # Step 4: Smart Plug Physical Setup
            StepDefinition(
                step_id=WizardStep.SMART_PLUG_PHYSICAL,
                title="Smart Plug Physical Setup",
                description="Connect and configure the smart plug hardware.",
                content_type=StepContentType.MANUAL,
                prerequisites=[
                    WizardStep.PARTICIPANT_SETUP,
                    WizardStep.WIFI_CONNECTION,
                    WizardStep.TIME_SYNC,
                ],
                validation_rules=[],
            ),
            # Step 5: Smart Plug Data Verification
            StepDefinition(
                step_id=WizardStep.SMART_PLUG_VERIFY,
                title="Smart Plug Data Verification",
                description="Verify smart plug data collection and Home Assistant integration.",
                content_type=StepContentType.MIXED,
                prerequisites=[
                    WizardStep.PARTICIPANT_SETUP,
                    WizardStep.WIFI_CONNECTION,
                    WizardStep.TIME_SYNC,
                    WizardStep.SMART_PLUG_PHYSICAL,
                ],
                validation_rules=[],
            ),
            # Step 6: Camera Setup (includes POV picture)
            StepDefinition(
                step_id=WizardStep.CAMERA_SETUP,
                title="Camera Setup and POV Picture",
                description="Position camera, verify connection, and capture POV baseline picture.",
                content_type=StepContentType.MANUAL,
                prerequisites=[
                    WizardStep.PARTICIPANT_SETUP,
                    WizardStep.WIFI_CONNECTION,
                    WizardStep.TIME_SYNC,
                    WizardStep.SMART_PLUG_PHYSICAL,
                    WizardStep.SMART_PLUG_VERIFY,
                ],
                validation_rules=[],
            ),
            # Step 7: Face Gallery Building
            StepDefinition(
                step_id=WizardStep.GALLERY_CREATION,
                title="Face Gallery Building",
                description="Create face gallery for family member recognition.",
                content_type=StepContentType.MIXED,
                prerequisites=[
                    WizardStep.PARTICIPANT_SETUP,
                    WizardStep.WIFI_CONNECTION,
                    WizardStep.TIME_SYNC,
                    WizardStep.SMART_PLUG_PHYSICAL,
                    WizardStep.SMART_PLUG_VERIFY,
                    WizardStep.CAMERA_SETUP,
                ],
                validation_rules=[],
            ),
            # Step 8: Gaze Detection Testing
            StepDefinition(
                step_id=WizardStep.GAZE_DETECTION_TESTING,
                title="Gaze Detection Testing",
                description="Test gaze detection system functionality.",
                content_type=StepContentType.MIXED,
                prerequisites=[
                    WizardStep.PARTICIPANT_SETUP,
                    WizardStep.WIFI_CONNECTION,
                    WizardStep.TIME_SYNC,
                    WizardStep.SMART_PLUG_PHYSICAL,
                    WizardStep.SMART_PLUG_VERIFY,
                    WizardStep.CAMERA_SETUP,
                    WizardStep.GALLERY_CREATION,
                ],
                validation_rules=[],
            ),
            # Step 9: Starting and Verifying Long Term FLASH-TV Services
            StepDefinition(
                step_id=WizardStep.SERVICE_STARTUP,
                title="Starting and Verifying Long Term FLASH-TV Services",
                description="Start and verify FLASH-TV services for long-term data collection.",
                content_type=StepContentType.AUTOMATED,
                prerequisites=[
                    WizardStep.PARTICIPANT_SETUP,
                    WizardStep.WIFI_CONNECTION,
                    WizardStep.TIME_SYNC,
                    WizardStep.SMART_PLUG_PHYSICAL,
                    WizardStep.SMART_PLUG_VERIFY,
                    WizardStep.CAMERA_SETUP,
                    WizardStep.GALLERY_CREATION,
                    WizardStep.GAZE_DETECTION_TESTING,
                ],
                validation_rules=[],
            ),
            # Step 10: Cord Checking
            StepDefinition(
                step_id=WizardStep.CORD_CHECKING,
                title="Cord and Connection Check",
                description="Verify all power cords and cable connections are secure.",
                content_type=StepContentType.MANUAL,
                prerequisites=[
                    WizardStep.PARTICIPANT_SETUP,
                    WizardStep.WIFI_CONNECTION,
                    WizardStep.TIME_SYNC,
                    WizardStep.SMART_PLUG_PHYSICAL,
                    WizardStep.SMART_PLUG_VERIFY,
                    WizardStep.CAMERA_SETUP,
                    WizardStep.GALLERY_CREATION,
                    WizardStep.GAZE_DETECTION_TESTING,
                    WizardStep.SERVICE_STARTUP,
                ],
                validation_rules=[],
            ),
            # Step 11: Screen Locking
            StepDefinition(
                step_id=WizardStep.DEVICE_LOCKING,
                title="Screen Locking and Final Setup",
                description="Lock the screen and prepare system for autonomous operation.",
                content_type=StepContentType.MANUAL,
                prerequisites=[
                    WizardStep.PARTICIPANT_SETUP,
                    WizardStep.WIFI_CONNECTION,
                    WizardStep.TIME_SYNC,
                    WizardStep.SMART_PLUG_PHYSICAL,
                    WizardStep.SMART_PLUG_VERIFY,
                    WizardStep.CAMERA_SETUP,
                    WizardStep.GALLERY_CREATION,
                    WizardStep.GAZE_DETECTION_TESTING,
                    WizardStep.SERVICE_STARTUP,
                    WizardStep.CORD_CHECKING,
                ],
                validation_rules=[],
            ),
        ]

    @staticmethod
    def create_step_instance(
        step_definition: StepDefinition,
        state: WizardState,
        process_runner,
        state_manager=None,
        parent=None,
    ) -> WizardStepBase:
        """Create a step instance based on the step definition using type-safe WizardStep enum mapping."""

        # Convert step_id to int for mapping (supports both enum and int)
        step_id_int = (
            int(step_definition.step_id)
            if isinstance(step_definition.step_id, WizardStep)
            else step_definition.step_id
        )

        # Map step IDs to their implementation classes using WizardStep enum for clarity
        step_classes = {
            WizardStep.PARTICIPANT_SETUP: ParticipantSetupStep,
            WizardStep.WIFI_CONNECTION: WiFiConnectionStep,
            WizardStep.TIME_SYNC: TimeSyncStep,
            WizardStep.SMART_PLUG_PHYSICAL: SmartPlugPhysicalStep,
            WizardStep.SMART_PLUG_VERIFY: SmartPlugVerifyStep,
            WizardStep.CAMERA_SETUP: CameraSetupStep,
            WizardStep.GALLERY_CREATION: GalleryCreationStep,
            WizardStep.GAZE_DETECTION_TESTING: GazeDetectionTestingStep,
            WizardStep.SERVICE_STARTUP: ServiceStartupStep,
            WizardStep.CORD_CHECKING: CordCheckingStep,
            WizardStep.DEVICE_LOCKING: DeviceLockingStep,
        }

        # Try enum lookup first, then fall back to int lookup
        step_class = None
        if isinstance(step_definition.step_id, WizardStep):
            step_class = step_classes.get(step_definition.step_id)
        else:
            # Look up by int value
            try:
                step_enum = WizardStep(step_id_int)
                step_class = step_classes.get(step_enum)
            except ValueError:
                pass

        if step_class:
            return step_class(
                step_definition, state, process_runner, state_manager, parent
            )
        else:
            # Return a generic step for unimplemented steps
            return GenericWizardStep(
                step_definition, state, process_runner, state_manager, parent
            )


class GenericWizardStep(WizardStepBase):
    """Generic step implementation for steps that don't have custom implementations yet."""

    def create_content_widget(self):
        """Create a placeholder content widget."""
        from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

        content = QWidget()
        layout = QVBoxLayout(content)

        # Placeholder message with proper step ID display
        step_id_display = (
            int(self.step_definition.step_id)
            if isinstance(self.step_definition.step_id, WizardStep)
            else self.step_definition.step_id
        )
        message = QLabel(f"Step {step_id_display} implementation is in progress.")
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
