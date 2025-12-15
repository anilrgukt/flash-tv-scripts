"""UI configuration constants for FLASH-TV GUI Setup Wizard.

This module contains all UI-related configuration values including dimensions,
colors, fonts, and styling constants.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class UIConfig:
    """UI configuration values - centralized and type-safe.

    This class uses frozen dataclass to ensure immutability of configuration values.
    All UI constants are defined here to maintain consistency across the application.
    """

    # Window dimensions
    MIN_WINDOW_WIDTH: int = 1200
    MIN_WINDOW_HEIGHT: int = 900

    # Font sizes (base sizes - adaptive sizing will scale up from these)
    TITLE_FONT_SIZE: int = 10
    HEADER_FONT_SIZE: int = 11
    STATUS_FONT_SIZE: int = 9
    LARGE_FONT_SIZE: int = 12
    NORMAL_FONT_SIZE: int = 10
    SMALL_FONT_SIZE: int = 9

    # Adaptive font sizing
    ADAPTIVE_FONT_ENABLED: bool = True
    MIN_FONT_SIZE: int = 9  # Minimum font size for adaptive scaling
    MAX_FONT_SIZE: int = 16  # Maximum font size for adaptive scaling
    FONT_SCALE_STEP: int = 1  # Font size increment for scaling
    TARGET_CONTENT_DENSITY: float = (
        0.65  # Target ratio of content height to container height
    )

    # Widget heights
    BUTTON_HEIGHT: int = 50
    INPUT_HEIGHT: int = 35

    # Colors
    SUCCESS_COLOR: str = "#2e7d32"
    ERROR_COLOR: str = "#c62828"
    WARNING_COLOR: str = "#f57c00"
    INFO_COLOR: str = "#1976d2"
    PENDING_COLOR: str = "#666"
    PRIMARY_COLOR: str = "#1976d2"

    # Background colors
    SUCCESS_BG: str = "#e8f5e8"
    ERROR_BG: str = "#ffebee"
    WARNING_BG: str = "#fff3e0"
    INFO_BG: str = "#e3f2fd"
    PENDING_BG: str = "#f0f0f0"
    HEADER_BG: str = "#f0f0f0"
    NAV_BG: str = "#f8f8f8"

    # Spacing
    DEFAULT_MARGIN: int = 8
    DEFAULT_PADDING: int = 6
    SECTION_SPACING: int = 4
    CONTENT_SPACING: int = 3
    DEFAULT_SPACING: int = 20
    COMPACT_SPACING: int = 10
    BORDER_RADIUS: int = 3

    # Timeouts (milliseconds)
    SHORT_TIMEOUT: int = 10000
    MEDIUM_TIMEOUT: int = 30000
    LONG_TIMEOUT: int = 60000
    EXTRA_LONG_TIMEOUT: int = 300000  # 5 minutes
    MONITOR_INTERVAL_MS: int = 1000
    AUTO_SAVE_INTERVAL_MS: int = 30000
    STATUS_UPDATE_INTERVAL_MS: int = 5000
    DEFAULT_TIMEOUT_MS: int = 120000
    MAX_TIMEOUT_MS: int = 600000

    # Process configuration
    SUDO_TIMEOUT_SECONDS: int = 300
    CLEANUP_INTERVAL_SECONDS: int = 60
    MAX_OUTPUT_LINES: int = 1000
    PROCESS_TERMINATION_TIMEOUT: int = 5

    # Network timeouts
    CONNECTION_TIMEOUT: int = 10
    WIFI_SCAN_TIMEOUT: int = 10
    WIFI_CONNECT_TIMEOUT: int = 30

    # Styling constants
    TIME_LABEL_STYLE: str = "font-size: 10px; font-weight: bold; padding: 10px;"
    SUCCESS_STYLE: str = "color: green;"
    ERROR_STYLE: str = "color: red;"


# Global singleton instance
UI_CONFIG = UIConfig()
