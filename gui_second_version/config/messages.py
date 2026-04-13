"""User-facing messages and text constants for FLASH-TV GUI Setup Wizard.

This module centralizes all user-facing text, error messages, success messages,
and UI labels to improve maintainability and enable future localization.
"""

from dataclasses import dataclass
from typing import Dict

from config.participant_contract import (
    get_gallery_dir as get_gallery_dir_path,
    get_participant_data_dir as get_participant_data_dir_path,
    get_tv_power_csv_path as get_tv_power_csv_contract_path,
)


@dataclass
class StepMessages:
    """Messages for a wizard step."""

    title: str
    description: str


class Messages:
    """Centralized message catalog for all user-facing text.

    This class organizes messages into logical groups for easy access and
    maintenance. All user-facing text should come from this class to enable
    consistent messaging and future localization support.
    """

    # Application Information
    APP_NAME: str = "FLASH-TV Setup Wizard"
    APP_VERSION: str = "2.0.0"
    APP_ORGANIZATION: str = "FLASH-TV Project"

    # Step configuration
    TOTAL_STEPS: int = 11
    STEP_TITLES: Dict[int, str] = {
        1: "Participant Setup",
        2: "WiFi Connection",
        3: "Time Synchronization",
        4: "Smart Plug Physical Setup",
        5: "Smart Plug Data Verification",
        6: "Camera Setup and POV Picture",
        7: "Face Gallery Building",
        8: "Gaze Detection Testing",
        9: "Starting and Verifying Long Term FLASH-TV Services",
        10: "Cord and Connection Check",
        11: "Screen Locking and Final Setup",
    }

    # Common UI text
    class UI:
        """Common UI element text."""

        CONTINUE = "Next"
        CONTINUE_SHORT = "Next"
        FINISH = "Finish"
        BACK = "← Back"
        CANCEL = "Cancel"
        OK = "Ok"
        YES = "Yes"
        NO = "No"
        SUCCESS = "Success"
        ERROR = "Error"
        BROWSE = "Browse..."
        LOADING = "Loading..."
        PLEASE_WAIT = "Please wait..."
        SCANNING = "Scanning..."
        CONNECT = "Connect"
        TEST_CONNECTION = "Test Connection"

        # Button text
        BROWSE_BUTTON = "Browse..."
        SCAN_NETWORKS = "Scan for Networks"
        CONNECT_TO_NETWORK = "Connect to Selected Network"
        SKIP_WIFI = "Skip WiFi Setup (If You Will Manually Set Time in the Next Step)"
        DETECT_CAMERAS = "Detect Available Cameras"
        TEST_CAMERA = "Test Selected Camera"
        SYNC_TIME = "🔄 Synchronize System Time"
        MANUAL_TIME = "📅 Manually Set Time"
        TIME_CORRECT = "Time is Correct - Continue"
        INSTALL_HA = "Install Home Assistant Integration"
        SKIP_HA = "Skip Home Assistant Setup"
        BROWSE_GALLERY = "Browse Existing Gallery..."
        CREATE_GALLERY = "Create Gallery from Camera Captures"
        VALIDATE_GALLERY = "Validate Gallery"

    # Status messages
    class Status:
        """Status indicator messages."""

        PENDING = "⚪ PENDING"
        USER_ACTION_REQUIRED = "🔵 USER ACTION REQUIRED"
        AUTOMATION_RUNNING = "🔄 AUTOMATION RUNNING"
        COMPLETED = "✅ COMPLETED"
        FAILED = "❌ FAILED"

    # Error messages
    class Errors:
        """Error messages shown to users."""

        MISSING_PARTICIPANT_ID = "Participant ID and username are required."
        MISSING_USERNAME = (
            "Username not found. Please complete participant setup first."
        )
        NO_CAMERA_SELECTED = "No camera was selected in the camera setup step."
        PASSWORD_CANCELLED = "Password input cancelled"
        INVALID_PASSWORD = "Invalid password"
        CONNECTION_TIMEOUT = "Connection timeout - check URL and network"
        CONNECTION_ERROR = "Connection error - Home Assistant may not be running"
        FILL_ALL_FIELDS = "Please fill in all required fields."
        NETWORK_SCAN_FAILED = "Failed to scan for networks"
        NETWORK_CONNECTION_FAILED = "Failed to connect to network"
        CAMERA_NOT_FOUND = "No camera found at specified index"
        PROCESS_FAILED = "Process failed with errors"
        VALIDATION_FAILED = "Validation failed"
        NO_NETWORK_SELECTED = "No Network Selected"
        SELECT_NETWORK_FIRST = "Please select a network first."
        CONNECTION_FAILED = "Connection Failed"
        NO_CAMERAS_DETECTED = "No cameras detected. Please check connections."
        ERROR_DETECTING_CAMERAS = "Error detecting cameras: {error}"
        CAMERA_TEST_FAILED = "Camera test failed: {error}"
        CAMERA_TEST_TIMEOUT = "Camera test timed out"
        ERROR_TESTING_CAMERA = "Error testing camera: {error}"
        ERROR_CHECKING_TIME_STATUS = "Error checking time status:\n{error}"
        FAILED_TO_ENABLE_NTP = "Failed to enable NTP: {error}"
        FAILED_TO_RESTART_SERVICE = "Failed to restart service: {error}"
        TIME_SYNC_FAILED = "Time sync failed: {error}"
        FAILED_TO_SET_TIME = "Failed to set time: {error}"
        RTC_CHECK_FAILED = "RTC status check failed: {error}"
        EXTERNAL_RTC_SYNC_FAILED = "Failed to sync from external RTC: {error}"
        EXTERNAL_RTC_SET_FAILED = "Failed to set external RTC: {error}"
        TEST_FAILED = "❌ Test failed: {error}"
        FAILED_TO_START_INSTALLATION = "❌ Failed to start installation process"
        ERROR_MISSING_GALLERY_INFO = (
            "Error: Missing required information for gallery creation"
        )
        FAILED_TO_START_GALLERY_CREATION = "Failed to start gallery creation process"

    # Success messages
    class Success:
        """Success messages shown to users."""

        NETWORK_CONNECTED = "Successfully connected to network"
        GALLERY_CREATED = "Face gallery created successfully"
        SERVICES_STARTED = "Services started successfully"
        TEST_PASSED = "Test completed successfully"
        PASSWORD_VERIFIED = "Password verified successfully"
        CONNECTION_ESTABLISHED = "Connection established successfully"
        INSTALLATION_COMPLETE = "Installation completed successfully"
        CONFIGURATION_SAVED = "Configuration saved successfully"
        CONNECTED_SUCCESS = "Connected"
        SUCCESSFULLY_CONNECTED = "Successfully connected to {ssid}"
        CAMERA_TEST_SUCCESSFUL = "Camera test successful!"
        TIME_SYNC_SUCCESSFUL = "Time synchronization successful!"
        TIME_SET_SUCCESSFULLY = "Time set successfully!"
        RTC_CHECK_SUCCESSFUL = "RTC status check completed successfully"
        EXTERNAL_RTC_SYNC_SUCCESS = "System time synchronized from external RTC!"
        EXTERNAL_RTC_SET_SUCCESS = "External RTC has been set to current system time!"
        GALLERY_VALIDATION_SUCCESSFUL = "\n✅ Gallery validation successful!"
        GALLERY_CREATION_COMPLETED = "\nGallery creation completed successfully!"

    # Confirmation messages
    class Confirmations:
        """Confirmation dialog messages."""

        DELETE_GALLERY = "Are you sure you want to delete the existing gallery?"
        RESTART_SERVICES = "Are you sure you want to restart services?"
        OVERWRITE_DATA = "This will overwrite existing data. Continue?"
        SKIP_WIFI = "Are you sure you want to skip WiFi configuration?\n\nThe device will not be able to sync the time automatically.\nYou will need to set the time manually in the next step."
        ENABLE_NTP = "This will enable NTP time synchronization.\n\nContinue?"
        NTP_REQUIRES_INTERNET = "This will enable NTP time synchronization (requires internet connection).\n\nContinue?"
        SET_TIME_MANUALLY = "Set the correct date and time:"
        SYNC_FROM_RTC = (
            "This will set the system time from the external RTC (DS3231).\n\nContinue?"
        )
        SET_EXTERNAL_RTC = "This will set the external RTC (DS3231) to the current system time.\n\nContinue?"
        SKIP_HA = "Are you sure you want to skip Home Assistant integration?\n\nYou will need to configure smart plug monitoring manually later."

    # WiFi messages
    class WiFi:
        """WiFi-related messages."""

        CHECKING_CONNECTION = "Checking current WiFi connection..."
        NO_CONNECTION = "❌ No WiFi connection detected"
        SETUP_SKIPPED = "⚠️ WiFi setup skipped"
        CONNECTION_SUCCESS = '✅ Connected to: "{ssid}"'
        FAILED_TO_CONNECT = "Failed to connect to {ssid}"
        NETWORK_REQUIRES_PASSWORD = "This network requires a password"
        AVAILABLE_NETWORKS = "Available Networks (double-click to connect):"

    # Camera messages
    class Camera:
        """Camera-related messages."""

        FOUND_CAMERAS = "Found {count} camera(s)"
        TESTING_CAMERA = "Testing camera: {path}"
        SUPPORTED_FORMATS = "Supported formats:"
        FRAME_CAPTURE_SUCCESS = "\nFrame capture test: SUCCESS"
        FRAME_CAPTURE_FAILED = "\nFrame capture test failed: {error}"
        UNKNOWN_CAMERA = "Unknown Camera"
        CAMERA_NUMBER = "Camera {number}"
        DETECTION = "Camera Detection"
        AVAILABLE_CAMERAS = "Available Cameras:"
        TEST = "Camera Test"
        TEST_OUTPUT = "Test Output:"

    # Time sync messages
    class Time:
        """Time synchronization messages."""

        CURRENT_SYSTEM_TIME = "Current System Time: Loading..."
        SYNC_CHECKING = "Time Synchronization: Checking..."
        SYNCHRONIZED = "Time Synchronization: ✅ Synchronized"
        NOT_SYNCHRONIZED = "Time Synchronization: ❌ Not Synchronized"
        NTP_ACTIVE = "\n✅ NTP service is active"
        NTP_INACTIVE = "\n⚠️ NTP service is not active"
        SYNC_PENDING = "Sync Pending"
        NTP_ENABLED_PENDING = "NTP is enabled but synchronization may take a moment.\nPlease check status again in a few seconds."
        SYSTEM_INFO = "System Time Information"
        CONFIG_DETAILS = "Time Configuration Details"
        SYNC_ACTIONS = "Time Synchronization Actions"
        RTC_CHECKING = "Checking RTC status..."
        EXTERNAL_RTC_CHECKING = "External RTC (DS3231): Checking..."
        INTERNAL_RTC0_CHECKING = "Internal RTC rtc0 (PSEQ_RTC): Checking..."
        INTERNAL_RTC1_CHECKING = "Internal RTC rtc1 (tegra-RTC): Checking..."
        RTC_AVAILABLE = "Time Status: ✅ RTC time available"
        RTC_SYNC_RECOMMENDED = "Time Status: ⚠️ RTC synchronization recommended"

    # Home Assistant messages
    class HomeAssistant:
        """Home Assistant integration messages."""

        OVERVIEW = """Home Assistant integration allows FLASH-TV to:

Monitor smart plug power consumption data
Track TV on/off states with a plot

Enter your Home Assistant URL to configure integration."""
        TESTING_CONNECTION = "🔍 Testing connection to: {url}"
        REACHABLE = "✅ Home Assistant is reachable"
        API_AVAILABLE = "✅ Home Assistant API is available"
        READY_TO_INSTALL = "Ready to install integration"
        API_STATUS_WARNING = "⚠️ API returned status: {status}"
        CONNECTION_FAILED_HTTP = "❌ Connection failed: HTTP {status}"
        CONNECTION_TIMEOUT = "❌ Connection timeout - check URL and network"
        CONNECTION_ERROR = "❌ Connection error - Home Assistant may not be running"
        INSTALLING = "🚀 Installing Home Assistant integration..."
        INSTALLATION_STARTED = "Integration installation started..."
        INTEGRATION_SKIPPED = "⚠️ Home Assistant integration skipped"
        ALREADY_CONFIGURED = "✅ Home Assistant already configured"
        INTEGRATION_COMPLETED = "\n✅ Home Assistant integration completed!"
        INTEGRATION_READY = "Integration is ready for smart plug monitoring."
        INSTALLATION_FAILED = "\n❌ Integration installation failed"
        EXIT_CODE = "Exit code: {code}"
        URL_LABEL = "Home Assistant URL:"
        DEFAULT_URL = "http://192.168.1.100:8123"
        DEFAULT_PORT = "8123"

    # Gallery messages
    class Gallery:
        """Face gallery messages."""

        INSTRUCTIONS = (
            "The face gallery contains reference images for family members. "
            "You can either create a new gallery from captured faces or "
            "use an existing gallery directory."
        )
        NO_PATH_SELECTED = "No gallery path selected"
        PATH_LABEL = "Gallery Path:"
        SELECTED_PATH = "Selected gallery path: {path}"
        CREATION_PROGRESS = "Creation Progress:"
        VALIDATION_RESULTS = "Validation Results:"
        CREATING_FOR_PARTICIPANT = "Creating gallery for participant: {participant_id}"
        LOCATION = "Gallery location: {path}"
        CREATION_STARTED = "Gallery creation started..."
        VALIDATING = "Validating gallery: {path}"
        DIR_NOT_EXIST = "❌ Gallery directory does not exist"
        FOUND_IMAGES = "✅ Found {count} images for {type}"
        MISSING_IMAGES = "❌ Missing images for {type}"
        VALIDATION_FAILED = (
            "\n❌ Gallery validation failed - missing required face images"
        )
        CREATION_FAILED = "\nGallery creation failed with status: {status}"
        MIN_IMAGES_PER_ROLE = 5
        ROLES = ["tc", "sib", "parent", "extra"]
        FOLDER_SUFFIX = "_faces"
        SELECTED_SUFFIX = "_selected"

    # Labels
    class Labels:
        """UI labels for forms and sections."""

        WIFI_CONNECTION = "WiFi Connection"
        HOME_ASSISTANT_INTEGRATION = "Home Assistant Integration"
        HOME_ASSISTANT_CONFIGURATION = "Home Assistant Configuration"
        INTEGRATION_SETUP = "Integration Setup"
        SETUP_PROGRESS = "Setup Progress"
        FACE_GALLERY_SETUP = "Face Gallery Setup"
        CREATE_NEW_GALLERY = "Create New Gallery"
        GALLERY_VALIDATION = "Gallery Validation"
        NETWORK = "Network: {ssid}"
        PASSWORD = "Password:"
        CONNECT_TO_NETWORK = "Connect to: {ssid}"
        DATA_PATH = "Data Path:"
        SELECT_DATA_DIR = "Select Data Directory"
        SELECT_GALLERY_DIR = "Select Face Gallery Directory"

    # Placeholders
    class Placeholders:
        """Input field placeholders."""

        PARTICIPANT_ID = "P1-XXXX or ES-XXXX"
        DEVICE_ID = "007"
        USERNAME = "flashsysXXX"
        DATA_PATH = "/home/flashsysXXX/data"

    # Templates
    class Templates:
        """Template strings for formatting."""

        POV_PICTURE = "{participant_id}_camera_pov_picture.jpg"
        DATA_DIR = "{participant_id}_data"
        FACES_DIR = "{participant_id}_faces"

    # Scripts and paths
    class Scripts:
        """Script names and paths."""

        CV2_CAPTURE = "cv2_capture_automate.py"
        FLASH_DEMO = "run_flash_demo_live.py"
        FLASH_DATA_COLLECTION = "run_flash_data_collection.py"
        FLASH_INSTALL = "flash_install.sh"
        HOMEASSISTANT_INSTALL = "homeassistant_install.sh"
        RUN_FLASHTV = "run_flashtv_system.sh"
        BUILD_GALLERY = "build_gallery.sh"
        CREATE_FACES = "create_faces.sh"
        SERVICE_SETUP = "service_setup.sh"
        START_SERVICES = "start_services.sh"
        STOP_SERVICES = "stop_services.sh"
        RESTART_SERVICES = "restart_services.sh"

    # Services
    class Services:
        """System service names."""

        FLASH_RUN_ON_BOOT = "flash-run-on-boot.service"
        FLASH_PERIODIC_RESTART = "flash-periodic-restart.service"
        SYSTEMD_TIMESYNCD = "systemd-timesyncd.service"

    # Testing
    class Testing:
        """Testing-related constants."""

        LOG_DURATION_SECONDS = 30
        CLEANUP_FOLDERS = ["test_res", "test_frames", "temp_images"]
        EXPECTED_TOTAL_IMAGES = 15
        SUDO_VERIFICATION_TIMEOUT = 10
        NETWORK_TEST_TIMEOUT = 5
        SERVICE_CHECK_TIMEOUT = 3

    # Hardware
    class Hardware:
        """Hardware configuration."""

        CAMERA_RESOLUTION = "1920x1080"
        FRAME_RATE = 30
        USB_CAMERA_PREFIX = "/dev/video"
        CAMERA_APPS = ["cheese"]

    # File types
    class FileTypes:
        """File type filters and extensions."""

        IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".bmp"]
        IMAGE_FILTER = "Image Files (*.png *.jpg *.jpeg *.bmp)"

    # Logging
    class Logging:
        """Logging configuration."""

        FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
        MAIN_LOG_FILE = "flash_setup_wizard.log"
        ERROR_LOG_FILE = "flash_setup_errors.log"
        MAX_LOG_SIZE_MB = 10
        LOG_BACKUP_COUNT = 5
        LOG_DIRECTORY = "logs"

    # Development
    class Development:
        """Development-related constants."""

        PLACEHOLDER_VALUE = "XXX"


# Helper functions for path formatting
def get_path_for_user(path_template: str, username: str) -> str:
    """Format a path template with the given username.

    Args:
        path_template: Path template with {username} placeholder
        username: System username to substitute

    Returns:
        Formatted path string

    Example:
        >>> get_path_for_user("/home/{username}/data", "flashsys028")
        '/home/flashsys028/data'
    """
    return path_template.format(username=username)


def get_data_path(participant_id: str, username: str, device_id: str = "") -> str:
    """Get the data path for a specific participant.

    Args:
        participant_id: Participant ID (e.g., 'P1-3999')
        username: System username (e.g., 'flashsys028')
        device_id: Optional device ID to append (e.g., '028')

    Returns:
        Data path in format: /home/{username}/data/{participant_id}{device_id}_data

    Example:
        >>> get_data_path("P1-3999", "flashsys028", "007")
        '/home/flashsys028/data/P1-3999007_data'
    """
    return str(get_participant_data_dir_path(username, participant_id, device_id))


def get_faces_path(participant_id: str, username: str, device_id: str = "") -> str:
    """Get the faces directory path for a specific participant.

    Args:
        participant_id: Participant ID (e.g., 'P1-3999')
        username: System username (e.g., 'flashsys028')
        device_id: Optional device ID to append (e.g., '028')

    Returns:
        Faces path in format: /home/{username}/data/{participant_id}{device_id}_data/{participant_id}{device_id}_faces

    Example:
        >>> get_faces_path("P1-3999", "flashsys028", "007")
        '/home/flashsys028/data/P1-3999007_data/P1-3999007_faces'
    """
    return str(get_gallery_dir_path(username, participant_id, device_id))


def get_tv_power_csv_path(participant_id: str, username: str, device_id: str = "") -> str:
    return str(get_tv_power_csv_contract_path(username, participant_id, device_id))


def get_python_path(username: str) -> str:
    """Get the Python virtual environment path for a user.

    Args:
        username: System username

    Returns:
        Path to Python interpreter in virtual environment

    Example:
        >>> get_python_path("flashsys028")
        '/home/flashsys028/py312/bin/python'
    """
    return f"/home/{username}/py312/bin/python"


# Global singleton instance
MESSAGES = Messages()
