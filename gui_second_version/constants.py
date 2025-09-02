"""Constants for FLASH-TV GUI setup wizard.

This module contains all hardcoded strings, numbers, and configuration values
used throughout the application to improve maintainability and consistency.
"""

from __future__ import annotations


# Application Information
class AppInfo:
    NAME = "FLASH-TV Setup Wizard"
    VERSION = "2.0.0"
    ORGANIZATION = "FLASH-TV Project"


# UI Constants
class UI:
    MIN_WINDOW_WIDTH = 1200
    MIN_WINDOW_HEIGHT = 900

    # Font sizes
    TITLE_FONT_SIZE = 14
    HEADER_FONT_SIZE = 16
    STATUS_FONT_SIZE = 12

    # Colors
    SUCCESS_COLOR = "#2e7d32"
    ERROR_COLOR = "#c62828"
    WARNING_COLOR = "#f57c00"
    INFO_COLOR = "#1976d2"
    PENDING_COLOR = "#666"

    # Background colors
    SUCCESS_BG = "#e8f5e8"
    ERROR_BG = "#ffebee"
    WARNING_BG = "#fff3e0"
    INFO_BG = "#e3f2fd"
    PENDING_BG = "#f0f0f0"
    HEADER_BG = "#f0f0f0"
    NAV_BG = "#f8f8f8"

    # Spacing
    DEFAULT_MARGIN = 8
    DEFAULT_PADDING = 6
    SECTION_SPACING = 4
    CONTENT_SPACING = 3
    BORDER_RADIUS = 3

    # Button Text
    CONTINUE_TO_NEXT_STEP = "Continue to Next Step"
    CONTINUE_BUTTON_TEXT = "Continue"
    BROWSE_BUTTON_TEXT = "Browse..."
    SCAN_FOR_NETWORKS = "Scan for Networks"
    CONNECT_TO_SELECTED_NETWORK = "Connect to Selected Network"
    SKIP_WIFI_SETUP = "Skip WiFi Setup"
    DETECT_AVAILABLE_CAMERAS = "Detect Available Cameras"
    TEST_SELECTED_CAMERA = "Test Selected Camera"
    SYNCHRONIZE_SYSTEM_TIME = "🔄 Synchronize System Time"
    MANUALLY_SET_TIME = "📅 Manually Set Time"
    TIME_IS_CORRECT_CONTINUE = "Time is Correct - Continue"
    CANCEL = "Cancel"
    CONNECT = "Connect"
    SCANNING = "Scanning..."
    OK = "Ok"
    YES = "Yes"
    NO = "No"
    SUCCESS = "Success"
    ERROR = "Error"
    BROWSE = "Browse..."
    TEST_CONNECTION = "Test Connection"
    INSTALL_HOME_ASSISTANT_INTEGRATION = "Install Home Assistant Integration"
    SKIP_HOME_ASSISTANT_SETUP = "Skip Home Assistant Setup"
    BROWSE_EXISTING_GALLERY = "Browse Existing Gallery..."
    CREATE_GALLERY_FROM_CAPTURES = "Create Gallery from Camera Captures"
    VALIDATE_GALLERY = "Validate Gallery"

    # Labels
    WIFI_CONNECTION = "WiFi Connection"
    HOME_ASSISTANT_INTEGRATION = "Home Assistant Integration"
    HOME_ASSISTANT_CONFIGURATION = "Home Assistant Configuration"
    HOME_ASSISTANT_URL = "Home Assistant URL:"
    INTEGRATION_SETUP = "Integration Setup"
    SETUP_PROGRESS = "Setup Progress"
    FACE_GALLERY_SETUP = "Face Gallery Setup"
    CREATE_NEW_GALLERY = "Create New Gallery"
    GALLERY_VALIDATION = "Gallery Validation"
    AVAILABLE_NETWORKS = "Available Networks (double-click to connect):"
    CAMERA_DETECTION = "Camera Detection"
    AVAILABLE_CAMERAS = "Available Cameras:"
    CAMERA_TEST = "Camera Test"
    TEST_OUTPUT = "Test Output:"
    SYSTEM_TIME_INFORMATION = "System Time Information"
    TIME_CONFIGURATION_DETAILS = "Time Configuration Details"
    TIME_SYNCHRONIZATION_ACTIONS = "Time Synchronization Actions"
    NETWORK_LABEL = "Network: {ssid}"
    PASSWORD_LABEL = "Password:"
    CONNECT_TO_NETWORK = "Connect to: {ssid}"
    DATA_PATH_LABEL = "Data Path:"

    # Styling
    TIME_LABEL_STYLE = "font-size: 14px; font-weight: bold; padding: 10px;"
    SUCCESS_STYLE = "color: green;"
    ERROR_STYLE = "color: red;"


# Status Messages
class StatusMessages:
    PENDING = "⚪ PENDING"
    USER_ACTION_REQUIRED = "🔵 USER ACTION REQUIRED"
    AUTOMATION_RUNNING = "🔄 AUTOMATION RUNNING"
    COMPLETED = "✅ COMPLETED"
    FAILED = "❌ FAILED"


# File System Paths
class Paths:
    # Directory patterns
    DEFAULT_DATA_DIR = "/home/{username}/data"
    DEFAULT_PYTHON_ENV = "/home/{username}/py38/bin/python"

    # Configuration files
    DEFAULT_CONFIG_FILE = "config.json"
    STATE_FILE = "flash_setup_state.json"
    BACKUP_SUFFIX = ".backup"
    TEMP_SUFFIX = ".tmp"
    CHECKPOINT_SUFFIX = ".checkpoint"

    # Script directories
    PYTHON_SCRIPTS_DIR = "../python_scripts"
    INSTALL_SCRIPTS_DIR = "../install_scripts"
    RUNTIME_SCRIPTS_DIR = "../runtime_scripts"
    SETUP_SCRIPTS_DIR = "../setup_scripts"
    SERVICES_DIR = "../services"

    # Model paths
    INSIGHTFACE_MODEL = "/home/{username}/insightface/models/buffalo_l/det_10g.onnx"
    ADAFACE_MODEL = "/home/{username}/Desktop/FLASH_TV_v3/AdaFace/pretrained/adaface_ir101_webface12m.ckpt"
    GAZE_MODEL1 = "/home/{username}/gaze_models/model1.pth"
    GAZE_MODEL2 = "/home/{username}/gaze_models/model2.pth"

    # System services
    FLASH_RUN_ON_BOOT_SERVICE = "/etc/systemd/system/flash-run-on-boot.service"
    FLASH_PERIODIC_RESTART_SERVICE = (
        "/etc/systemd/system/flash-periodic-restart.service"
    )


# Scripts
class Scripts:
    # Python scripts
    CV2_CAPTURE = "cv2_capture_automate.py"
    FLASH_DEMO = "run_flash_demo_live.py"
    FLASH_DATA_COLLECTION = "run_flash_data_collection.py"

    # Install scripts
    FLASH_INSTALL = "flash_install.sh"
    HOMEASSISTANT_INSTALL = "homeassistant_install.sh"

    # Runtime scripts
    RUN_FLASHTV = "run_flashtv_system.sh"
    BUILD_GALLERY = "build_gallery.sh"
    CREATE_FACES = "create_faces.sh"

    # Setup scripts
    SERVICE_SETUP = "service_setup.sh"

    # Service scripts
    START_SERVICES = "start_services.sh"
    STOP_SERVICES = "stop_services.sh"
    RESTART_SERVICES = "restart_services.sh"


# Network Configuration
class Network:
    DEFAULT_HA_PORT = "8123"
    DEFAULT_HA_URL = "http://192.168.1.100:8123"
    CONNECTION_TIMEOUT = 10
    WIFI_SCAN_TIMEOUT = 10
    WIFI_CONNECT_TIMEOUT = 30


# Process Configuration
class Process:
    SUDO_TIMEOUT_SECONDS = 300
    MONITOR_INTERVAL_MS = 1000
    AUTO_SAVE_INTERVAL_MS = 30000
    STATUS_UPDATE_INTERVAL_MS = 5000
    DEFAULT_TIMEOUT_MS = 120000
    MAX_TIMEOUT_MS = 600000

    # Process cleanup settings
    CLEANUP_INTERVAL_SECONDS = 60
    MAX_OUTPUT_LINES = 1000
    PROCESS_TERMINATION_TIMEOUT = 5


# Testing Constants
class Testing:
    LOG_TEST_DURATION_SECONDS = 30
    CLEANUP_FOLDERS = ["test_res", "test_frames", "temp_images"]
    MIN_GALLERY_IMAGES = 5
    EXPECTED_TOTAL_IMAGES = 15

    # Validation timeouts
    SUDO_VERIFICATION_TIMEOUT = 10
    NETWORK_TEST_TIMEOUT = 5
    SERVICE_CHECK_TIMEOUT = 3


# System Services
class Services:
    FLASH_RUN_ON_BOOT = "flash-run-on-boot.service"
    FLASH_PERIODIC_RESTART = "flash-periodic-restart.service"
    SYSTEMD_TIMESYNCD = "systemd-timesyncd.service"


# Gallery Configuration
class Gallery:
    ROLES = ["tc", "sib", "parent", "extra"]
    MIN_IMAGES_PER_ROLE = 5
    FOLDER_SUFFIX = "_faces"
    SELECTED_SUFFIX = "_selected"


# Messages
class Messages:
    # Error messages
    MISSING_PARTICIPANT_ID = "Participant ID and username are required."
    MISSING_USERNAME = "Username not found. Please complete participant setup first."
    NO_CAMERA_SELECTED = "No camera was selected in the camera setup step."
    PASSWORD_CANCELLED = "Password input cancelled"
    INVALID_PASSWORD = "Invalid password"
    CONNECTION_TIMEOUT = "Connection timeout - check URL and network"
    CONNECTION_ERROR = "Connection error - Home Assistant may not be running"
    FILL_ALL_FIELDS = "Please fill in all required fields."
    SELECT_DATA_DIRECTORY = "Select Data Directory"

    # Success messages
    PASSWORD_VERIFIED = "Password verified successfully"
    CONNECTION_ESTABLISHED = "Connection established successfully"
    INSTALLATION_COMPLETE = "Installation completed successfully"
    CONFIGURATION_SAVED = "Configuration saved successfully"

    # WiFi messages
    CHECKING_WIFI_CONNECTION = "Checking current WiFi connection..."
    NO_WIFI_CONNECTION = "❌ No WiFi connection detected"
    WIFI_SETUP_SKIPPED = "⚠️ WiFi setup skipped"
    WIFI_CONNECTION_SUCCESS = '✅ Connected to: "{ssid}"'
    NO_NETWORK_SELECTED = "No Network Selected"
    SELECT_NETWORK_FIRST = "Please select a network first."
    CONNECTION_FAILED = "Connection Failed"
    CONNECTED_SUCCESS = "Connected"
    SUCCESSFULLY_CONNECTED = "Successfully connected to {ssid}"
    FAILED_TO_CONNECT = "Failed to connect to {ssid}"
    SKIP_WIFI_SETUP = "Skip WiFi Setup"
    SKIP_WIFI_CONFIRMATION = "Are you sure you want to skip WiFi configuration?\n\nThe device will not have internet connectivity until WiFi is configured manually."
    NETWORK_REQUIRES_PASSWORD = "This network requires a password"

    # Camera messages
    FOUND_CAMERAS = "Found {count} camera(s)"
    NO_CAMERAS_DETECTED = "No cameras detected. Please check connections."
    ERROR_DETECTING_CAMERAS = "Error detecting cameras: {error}"
    TESTING_CAMERA = "Testing camera: {path}"
    CAMERA_TEST_SUCCESSFUL = "Camera test successful!"
    SUPPORTED_FORMATS = "Supported formats:"
    FRAME_CAPTURE_SUCCESS = "\nFrame capture test: SUCCESS"
    FRAME_CAPTURE_FAILED = "\nFrame capture test failed: {error}"
    CAMERA_TEST_FAILED = "Camera test failed: {error}"
    CAMERA_TEST_TIMEOUT = "Camera test timed out"
    ERROR_TESTING_CAMERA = "Error testing camera: {error}"
    UNKNOWN_CAMERA = "Unknown Camera"
    CAMERA_NUMBER = "Camera {number}"

    # Time sync messages
    CURRENT_SYSTEM_TIME = "Current System Time: Loading..."
    TIME_SYNCHRONIZATION_CHECKING = "Time Synchronization: Checking..."
    TIME_SYNCHRONIZED = "Time Synchronization: ✅ Synchronized"
    TIME_NOT_SYNCHRONIZED = "Time Synchronization: ❌ Not Synchronized"
    NTP_SERVICE_ACTIVE = "\n✅ NTP service is active"
    NTP_SERVICE_INACTIVE = "\n⚠️ NTP service is not active"
    ERROR_CHECKING_TIME_STATUS = "Error checking time status:\n{error}"
    SYNCHRONIZE_TIME = "Synchronize Time"
    ENABLE_NTP_CONFIRMATION = "This will enable NTP time synchronization.\n\nContinue?"
    FAILED_TO_ENABLE_NTP = "Failed to enable NTP: {error}"
    FAILED_TO_RESTART_SERVICE = "Failed to restart service: {error}"
    TIME_SYNC_SUCCESSFUL = "Time synchronization successful!"
    SYNC_PENDING = "Sync Pending"
    NTP_ENABLED_PENDING = "NTP is enabled but synchronization may take a moment.\nPlease check status again in a few seconds."
    TIME_SYNC_FAILED = "Time sync failed: {error}"
    SET_SYSTEM_TIME_MANUALLY = "Set System Time Manually"
    SET_CORRECT_DATE_TIME = "Set the correct date and time:"
    FAILED_TO_SET_TIME = "Failed to set time: {error}"
    TIME_SET_SUCCESSFULLY = "Time set successfully!"

    # Home Assistant messages
    HOME_ASSISTANT_OVERVIEW = """Home Assistant integration allows FLASH-TV to:

• Monitor smart plug power consumption data
• Track TV on/off states automatically  
• Integrate with home automation workflows
• Provide real-time viewing behavior insights

Enter your Home Assistant URL to configure integration."""
    TESTING_CONNECTION_TO = "🔍 Testing connection to: {url}"
    HOME_ASSISTANT_REACHABLE = "✅ Home Assistant is reachable"
    HOME_ASSISTANT_API_AVAILABLE = "✅ Home Assistant API is available"
    READY_TO_INSTALL_INTEGRATION = "Ready to install integration"
    API_STATUS_WARNING = "⚠️ API returned status: {status}"
    CONNECTION_FAILED_HTTP = "❌ Connection failed: HTTP {status}"
    CONNECTION_TIMEOUT_HA = "❌ Connection timeout - check URL and network"
    CONNECTION_ERROR_HA = "❌ Connection error - Home Assistant may not be running"
    TEST_FAILED = "❌ Test failed: {error}"
    INSTALLING_HA_INTEGRATION = "🚀 Installing Home Assistant integration..."
    INTEGRATION_INSTALLATION_STARTED = "Integration installation started..."
    FAILED_TO_START_INSTALLATION = "❌ Failed to start installation process"
    SKIP_HA_SETUP = "Skip Home Assistant Setup"
    SKIP_HA_CONFIRMATION = "Are you sure you want to skip Home Assistant integration?\n\nYou will need to configure smart plug monitoring manually later."
    HA_INTEGRATION_SKIPPED = "⚠️ Home Assistant integration skipped"
    HA_ALREADY_CONFIGURED = "✅ Home Assistant already configured"
    HA_INTEGRATION_COMPLETED = "\n✅ Home Assistant integration completed!"
    INTEGRATION_READY = "Integration is ready for smart plug monitoring."
    INTEGRATION_INSTALLATION_FAILED = "\n❌ Integration installation failed"
    EXIT_CODE = "Exit code: {code}"

    # Gallery creation messages
    GALLERY_INSTRUCTIONS = (
        "The face gallery contains reference images for family members. "
        "You can either create a new gallery from captured faces or "
        "use an existing gallery directory."
    )
    NO_GALLERY_PATH_SELECTED = "No gallery path selected"
    GALLERY_PATH_LABEL = "Gallery Path:"
    SELECTED_GALLERY_PATH = "Selected gallery path: {path}"
    CREATION_PROGRESS = "Creation Progress:"
    VALIDATION_RESULTS = "Validation Results:"
    SELECT_FACE_GALLERY_DIRECTORY = "Select Face Gallery Directory"
    ERROR_MISSING_GALLERY_INFO = (
        "Error: Missing required information for gallery creation"
    )
    CREATING_GALLERY_FOR_PARTICIPANT = (
        "Creating gallery for participant: {participant_id}"
    )
    GALLERY_LOCATION = "Gallery location: {path}"
    GALLERY_CREATION_STARTED = "Gallery creation started..."
    FAILED_TO_START_GALLERY_CREATION = "Failed to start gallery creation process"
    VALIDATING_GALLERY = "Validating gallery: {path}"
    GALLERY_DIRECTORY_NOT_EXIST = "❌ Gallery directory does not exist"
    FOUND_IMAGES_FOR_TYPE = "✅ Found {count} images for {type}"
    MISSING_IMAGES_FOR_TYPE = "❌ Missing images for {type}"
    GALLERY_VALIDATION_SUCCESSFUL = "\n✅ Gallery validation successful!"
    GALLERY_VALIDATION_FAILED = (
        "\n❌ Gallery validation failed - missing required face images"
    )
    GALLERY_CREATION_COMPLETED = "\nGallery creation completed successfully!"
    GALLERY_CREATION_FAILED_STATUS = "\nGallery creation failed with status: {status}"


# Validation Patterns
class Patterns:
    PARTICIPANT_ID = r"^(P1|ES)-\d{4}$"
    IPV4_ADDRESS = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"


# File Types
class FileTypes:
    IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".bmp"]
    IMAGE_FILTER = "Image Files (*.png *.jpg *.jpeg *.bmp)"


# Logging
class Logging:
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    MAIN_LOG_FILE = "flash_setup_wizard.log"
    ERROR_LOG_FILE = "flash_setup_errors.log"

    # Log rotation settings
    MAX_LOG_SIZE_MB = 10
    LOG_BACKUP_COUNT = 5
    LOG_DIRECTORY = "logs"


# Step Information
class Steps:
    TOTAL = 12
    TITLES = {
        1: "Participant Setup",
        2: "WiFi Connection",
        3: "Time Synchronization",
        4: "Smart Plug Physical Setup",
        5: "Smart Plug Data Verification",
        6: "Camera Positioning and Setup",
        7: "Point of View Picture",
        8: "Face Gallery Building",
        9: "Gaze Detection Testing",
        10: "Log File Verification",
        11: "Cord and Connection Check",
        12: "Screen Locking and Final Setup",
    }


# Hardware
class Hardware:
    CAMERA_RESOLUTION = "1920x1080"
    FRAME_RATE = 30
    USB_CAMERA_PREFIX = "/dev/video"
    CAMERA_APPS = ["cheese"]


# Templates
class Templates:
    PARTICIPANT_ID_PLACEHOLDER = "P1-XXXX or ES-XXXX"
    DEVICE_ID_PLACEHOLDER = "0XX"
    USERNAME_PLACEHOLDER = "flashsysXXX"
    DATA_PATH_PLACEHOLDER = "/home/flashsysXXX/data"
    POV_PICTURE_NAME = "{participant_id}_camera_pov_picture.jpg"
    DATA_DIR_NAME = "{participant_id}_data"
    FACES_DIR_NAME = "{participant_id}_faces"


# Development
class Development:
    PLACEHOLDER_VALUE = "XXX"


def get_path_for_user(path_template: str, username: str) -> str:
    """Format a path template with the given username."""
    return path_template.format(username=username)


def get_data_path(participant_id: str, username: str) -> str:
    """Get the data path for a specific participant."""
    return f"/home/{username}/data/{participant_id}_data"


def get_faces_path(participant_id: str, username: str) -> str:
    """Get the faces directory path for a specific participant."""
    return f"/home/{username}/data/{participant_id}_faces"


def get_python_path(username: str) -> str:
    """Get the Python virtual environment path for a user."""
    return f"/home/{username}/py38/bin/python"
