"""Type-safe Enum definitions for wizard state management.

This module defines all Enums used throughout the FLASH-TV GUI wizard to replace
magic numbers and string literals, making the state system more robust and maintainable.
"""

from __future__ import annotations

from enum import IntEnum

try:
    from enum import StrEnum
except ImportError:
    from backports.strenum import StrEnum


class WizardStep(IntEnum):
    """Wizard step identifiers replacing magic number step IDs.

    Each step represents a distinct phase in the FLASH-TV setup process.
    The numeric values match the original step numbering for compatibility.
    """

    PARTICIPANT_SETUP = 1
    WIFI_CONNECTION = 2
    TIME_SYNC = 3
    SMART_PLUG_PHYSICAL = 4
    SMART_PLUG_VERIFY = 5
    CAMERA_SETUP = 6
    GALLERY_CREATION = 7
    GAZE_DETECTION_TESTING = 8
    SERVICE_STARTUP = 9
    CORD_CHECKING = 10
    DEVICE_LOCKING = 11


class UserInputKey(StrEnum):
    """User input keys for storing participant-provided data.

    These keys are used with WizardState.get_user_input() and set_user_input()
    to access user-provided configuration and setup information.
    """

    # Participant Information (Step 1)
    PARTICIPANT_ID = "participant_id"
    DEVICE_ID = "device_id"
    USERNAME = "username"
    SUDO_PASSWORD = "sudo_password"
    DATA_PATH = "data_path"

    # WiFi Configuration (Step 2)
    WIFI_SSID = "wifi_ssid"
    WIFI_CONNECTED = "wifi_connected"

    # Camera Configuration (Step 6)
    SELECTED_CAMERA = "selected_camera"
    SELECTED_CAMERA_NAME = "selected_camera_name"
    CAMERA_TESTED = "camera_tested"
    POV_IMAGE_PATH = "pov_image_path"
    POV_PICTURE_COMPLETE = "pov_picture_complete"
    CAMERA_SETUP_NOTES = "camera_setup_notes"

    # Gallery Configuration (Step 7)
    GALLERY_PATH = "gallery_path"
    GALLERY_VALIDATED = "gallery_validated"
    GALLERY_TOTAL_IMAGES = "gallery_total_images"
    GALLERY_ROLE_TC_SELECTED = "gallery_role_tc_selected"
    GALLERY_ROLE_SIB_SELECTED = "gallery_role_sib_selected"
    GALLERY_ROLE_PARENT_SELECTED = "gallery_role_parent_selected"
    GALLERY_CONSENT_CONFIRMED = "gallery_consent_confirmed"

    # Smart Plug Configuration (Steps 4-5)
    SMART_PLUG_CONFIGURED = "smart_plug_configured"
    SMART_PLUG_PHYSICAL_COMPLETE = "smart_plug_physical_complete"
    SMART_PLUG_PHYSICAL_PROGRESS = "smart_plug_physical_progress"
    SMART_PLUG_VERIFIED = "smart_plug_verified"
    SMART_PLUG_VERIFICATION_METHOD = "smart_plug_verification_method"
    TV_ON_PERIOD_START = "tv_on_period_start"
    TV_ON_PERIOD_END = "tv_on_period_end"
    TV_OFF_PERIOD_START = "tv_off_period_start"
    TV_OFF_PERIOD_END = "tv_off_period_end"

    # Time Synchronization (Step 3)
    TIME_SYNCED = "time_synced"

    # Cord Checking (Step 10)
    CORDS_VERIFIED = "cords_verified"
    CORD_CHECKING_NOTES = "cord_checking_notes"

    # Service Startup (Step 9)
    SERVICES_VERIFIED = "services_verified"

    # Gaze Detection Testing (Step 8)
    GAZE_DETECTION_VERIFIED = "gaze_detection_verified"
    GAZE_DETECTION_NOTES = "gaze_detection_notes"
    GAZE_TEST_COMPLETE = "gaze_test_complete"

    # Service Startup (Step 9)
    SERVICES_RUNNING = "services_running"

    # Device Locking (Step 11)
    DEVICE_LOCKED = "device_locked"
    SETUP_COMPLETE = "setup_complete"
    FINAL_INSTRUCTIONS = "final_instructions"


class SystemStateKey(StrEnum):
    """System state keys for internal wizard state tracking.

    These keys are used with WizardState.get_system_state() and set_system_state()
    to track internal system state that is not directly user-provided.
    """

    # Camera Detection
    DETECTED_CAMERAS = "detected_cameras"

    # Process Tracking
    BACKGROUND_PROCESSES = "background_processes"

    # Automation State
    LAST_AUTOMATION_RUN = "last_automation_run"
    AUTOMATION_RETRY_COUNT = "automation_retry_count"

    # Validation State
    LAST_VALIDATION_TIME = "last_validation_time"
    VALIDATION_ERRORS = "validation_errors"

    # Session Information
    SESSION_START_TIME = "session_start_time"
    SESSION_RESUME_COUNT = "session_resume_count"


# Mapping of step IDs to human-readable names for backwards compatibility
# This can be used to convert between enum and string representations
STEP_NAMES = {
    WizardStep.PARTICIPANT_SETUP: "Participant and Device Setup",
    WizardStep.WIFI_CONNECTION: "WiFi Connection Setup",
    WizardStep.TIME_SYNC: "Time Synchronization",
    WizardStep.SMART_PLUG_PHYSICAL: "Smart Plug Physical Setup",
    WizardStep.SMART_PLUG_VERIFY: "Smart Plug Data Verification",
    WizardStep.CAMERA_SETUP: "Camera Setup and POV Picture",
    WizardStep.GALLERY_CREATION: "Face Gallery Building",
    WizardStep.GAZE_DETECTION_TESTING: "Gaze Detection Testing",
    WizardStep.SERVICE_STARTUP: "Starting and Verifying Long Term FLASH-TV Services",
    WizardStep.CORD_CHECKING: "Cord and Connection Check",
    WizardStep.DEVICE_LOCKING: "Screen Locking and Final Setup",
}


# Step dependencies mapping using WizardStep enum
STEP_DEPENDENCIES = {
    WizardStep.PARTICIPANT_SETUP: [],
    WizardStep.WIFI_CONNECTION: [WizardStep.PARTICIPANT_SETUP],
    WizardStep.TIME_SYNC: [WizardStep.PARTICIPANT_SETUP, WizardStep.WIFI_CONNECTION],
    WizardStep.SMART_PLUG_PHYSICAL: [
        WizardStep.PARTICIPANT_SETUP,
        WizardStep.WIFI_CONNECTION,
        WizardStep.TIME_SYNC,
    ],
    WizardStep.SMART_PLUG_VERIFY: [
        WizardStep.PARTICIPANT_SETUP,
        WizardStep.WIFI_CONNECTION,
        WizardStep.TIME_SYNC,
        WizardStep.SMART_PLUG_PHYSICAL,
    ],
    WizardStep.CAMERA_SETUP: [
        WizardStep.PARTICIPANT_SETUP,
        WizardStep.WIFI_CONNECTION,
        WizardStep.TIME_SYNC,
        WizardStep.SMART_PLUG_PHYSICAL,
        WizardStep.SMART_PLUG_VERIFY,
    ],
    WizardStep.GALLERY_CREATION: [
        WizardStep.PARTICIPANT_SETUP,
        WizardStep.WIFI_CONNECTION,
        WizardStep.TIME_SYNC,
        WizardStep.SMART_PLUG_PHYSICAL,
        WizardStep.SMART_PLUG_VERIFY,
        WizardStep.CAMERA_SETUP,
    ],
    WizardStep.GAZE_DETECTION_TESTING: [
        WizardStep.PARTICIPANT_SETUP,
        WizardStep.WIFI_CONNECTION,
        WizardStep.TIME_SYNC,
        WizardStep.SMART_PLUG_PHYSICAL,
        WizardStep.SMART_PLUG_VERIFY,
        WizardStep.CAMERA_SETUP,
        WizardStep.GALLERY_CREATION,
    ],
    WizardStep.SERVICE_STARTUP: [
        WizardStep.PARTICIPANT_SETUP,
        WizardStep.WIFI_CONNECTION,
        WizardStep.TIME_SYNC,
        WizardStep.SMART_PLUG_PHYSICAL,
        WizardStep.SMART_PLUG_VERIFY,
        WizardStep.CAMERA_SETUP,
        WizardStep.GALLERY_CREATION,
        WizardStep.GAZE_DETECTION_TESTING,
    ],
    WizardStep.CORD_CHECKING: [
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
    WizardStep.DEVICE_LOCKING: [
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
}


# Step required inputs mapping using both WizardStep and UserInputKey enums
STEP_REQUIRED_INPUTS = {
    WizardStep.WIFI_CONNECTION: [
        UserInputKey.PARTICIPANT_ID,
        UserInputKey.DEVICE_ID,
        UserInputKey.USERNAME,
    ],
    WizardStep.TIME_SYNC: [
        UserInputKey.PARTICIPANT_ID,
        UserInputKey.DEVICE_ID,
        UserInputKey.USERNAME,
        UserInputKey.WIFI_SSID,
    ],
    WizardStep.SMART_PLUG_PHYSICAL: [
        UserInputKey.PARTICIPANT_ID,
        UserInputKey.DEVICE_ID,
    ],
    WizardStep.CAMERA_SETUP: [
        UserInputKey.PARTICIPANT_ID,
        UserInputKey.DEVICE_ID,
        UserInputKey.USERNAME,
        UserInputKey.DATA_PATH,
    ],
    WizardStep.GALLERY_CREATION: [
        UserInputKey.PARTICIPANT_ID,
        UserInputKey.DEVICE_ID,
        UserInputKey.USERNAME,
        UserInputKey.DATA_PATH,
        UserInputKey.SELECTED_CAMERA,
        UserInputKey.CAMERA_TESTED,
        UserInputKey.POV_PICTURE_COMPLETE,
    ],
    WizardStep.SMART_PLUG_VERIFY: [UserInputKey.PARTICIPANT_ID, UserInputKey.DEVICE_ID],
    WizardStep.GAZE_DETECTION_TESTING: [
        UserInputKey.PARTICIPANT_ID,
        UserInputKey.DEVICE_ID,
        UserInputKey.USERNAME,
        UserInputKey.DATA_PATH,
        UserInputKey.GALLERY_PATH,
        UserInputKey.GALLERY_VALIDATED,
    ],
    WizardStep.SERVICE_STARTUP: [
        UserInputKey.PARTICIPANT_ID,
        UserInputKey.DEVICE_ID,
        UserInputKey.USERNAME,
        UserInputKey.DATA_PATH,
        UserInputKey.GALLERY_PATH,
        UserInputKey.GALLERY_VALIDATED,
        UserInputKey.GAZE_DETECTION_VERIFIED,
    ],
}
