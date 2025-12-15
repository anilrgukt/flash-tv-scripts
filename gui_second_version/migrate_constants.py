#!/usr/bin/env python3
"""Migration script to update constants imports to new config modules."""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Mapping of old constant classes to new imports
IMPORT_MAPPING = {
    "AppInfo": "MESSAGES",
    "UI": "UI_CONFIG",
    "Messages": "MESSAGES",
    "Patterns": "VALIDATION",
    "Paths": "MESSAGES",
    "Scripts": "MESSAGES",
    "Network": "UI_CONFIG",
    "Process": "UI_CONFIG",
    "Testing": "MESSAGES",
    "Services": "MESSAGES",
    "Gallery": "MESSAGES",
    "StatusMessages": "MESSAGES",
    "Templates": "MESSAGES",
    "Logging": "MESSAGES",
    "Steps": "MESSAGES",
    "Hardware": "MESSAGES",
    "FileTypes": "MESSAGES",
    "Development": "MESSAGES",
}

# Mapping of attribute paths
ATTRIBUTE_MAPPING = {
    # AppInfo
    "AppInfo.NAME": "MESSAGES.APP_NAME",
    "AppInfo.VERSION": "MESSAGES.APP_VERSION",
    "AppInfo.ORGANIZATION": "MESSAGES.APP_ORGANIZATION",
    # UI -> UI_CONFIG
    "UI.MIN_WINDOW_WIDTH": "UI_CONFIG.MIN_WINDOW_WIDTH",
    "UI.MIN_WINDOW_HEIGHT": "UI_CONFIG.MIN_WINDOW_HEIGHT",
    "UI.TITLE_FONT_SIZE": "UI_CONFIG.TITLE_FONT_SIZE",
    "UI.HEADER_FONT_SIZE": "UI_CONFIG.HEADER_FONT_SIZE",
    "UI.STATUS_FONT_SIZE": "UI_CONFIG.STATUS_FONT_SIZE",
    "UI.SUCCESS_COLOR": "UI_CONFIG.SUCCESS_COLOR",
    "UI.ERROR_COLOR": "UI_CONFIG.ERROR_COLOR",
    "UI.WARNING_COLOR": "UI_CONFIG.WARNING_COLOR",
    "UI.INFO_COLOR": "UI_CONFIG.INFO_COLOR",
    "UI.PENDING_COLOR": "UI_CONFIG.PENDING_COLOR",
    "UI.SUCCESS_BG": "UI_CONFIG.SUCCESS_BG",
    "UI.ERROR_BG": "UI_CONFIG.ERROR_BG",
    "UI.WARNING_BG": "UI_CONFIG.WARNING_BG",
    "UI.INFO_BG": "UI_CONFIG.INFO_BG",
    "UI.PENDING_BG": "UI_CONFIG.PENDING_BG",
    "UI.HEADER_BG": "UI_CONFIG.HEADER_BG",
    "UI.NAV_BG": "UI_CONFIG.NAV_BG",
    "UI.DEFAULT_MARGIN": "UI_CONFIG.DEFAULT_MARGIN",
    "UI.DEFAULT_PADDING": "UI_CONFIG.DEFAULT_PADDING",
    "UI.SECTION_SPACING": "UI_CONFIG.SECTION_SPACING",
    "UI.CONTENT_SPACING": "UI_CONFIG.CONTENT_SPACING",
    "UI.BORDER_RADIUS": "UI_CONFIG.BORDER_RADIUS",
    "UI.TIME_LABEL_STYLE": "UI_CONFIG.TIME_LABEL_STYLE",
    "UI.SUCCESS_STYLE": "UI_CONFIG.SUCCESS_STYLE",
    "UI.ERROR_STYLE": "UI_CONFIG.ERROR_STYLE",
    # UI button text -> MESSAGES.UI
    "UI.CONTINUE_TO_NEXT_STEP": "MESSAGES.UI.CONTINUE",
    "UI.CONTINUE_BUTTON_TEXT": "MESSAGES.UI.CONTINUE_SHORT",
    "UI.BROWSE_BUTTON_TEXT": "MESSAGES.UI.BROWSE",
    "UI.SCAN_FOR_NETWORKS": "MESSAGES.UI.SCAN_NETWORKS",
    "UI.CONNECT_TO_SELECTED_NETWORK": "MESSAGES.UI.CONNECT_TO_NETWORK",
    "UI.SKIP_WIFI_SETUP": "MESSAGES.UI.SKIP_WIFI",
    "UI.DETECT_AVAILABLE_CAMERAS": "MESSAGES.UI.DETECT_CAMERAS",
    "UI.TEST_SELECTED_CAMERA": "MESSAGES.UI.TEST_CAMERA",
    "UI.SYNCHRONIZE_SYSTEM_TIME": "MESSAGES.UI.SYNC_TIME",
    "UI.MANUALLY_SET_TIME": "MESSAGES.UI.MANUAL_TIME",
    "UI.TIME_IS_CORRECT_CONTINUE": "MESSAGES.UI.TIME_CORRECT",
    "UI.CANCEL": "MESSAGES.UI.CANCEL",
    "UI.CONNECT": "MESSAGES.UI.CONNECT",
    "UI.SCANNING": "MESSAGES.UI.SCANNING",
    "UI.OK": "MESSAGES.UI.OK",
    "UI.YES": "MESSAGES.UI.YES",
    "UI.NO": "MESSAGES.UI.NO",
    "UI.SUCCESS": "MESSAGES.UI.SUCCESS",
    "UI.ERROR": "MESSAGES.UI.ERROR",
    "UI.BROWSE": "MESSAGES.UI.BROWSE",
    "UI.TEST_CONNECTION": "MESSAGES.UI.TEST_CONNECTION",
    "UI.INSTALL_HOME_ASSISTANT_INTEGRATION": "MESSAGES.UI.INSTALL_HA",
    "UI.SKIP_HOME_ASSISTANT_SETUP": "MESSAGES.UI.SKIP_HA",
    "UI.BROWSE_EXISTING_GALLERY": "MESSAGES.UI.BROWSE_GALLERY",
    "UI.CREATE_GALLERY_FROM_CAPTURES": "MESSAGES.UI.CREATE_GALLERY",
    "UI.VALIDATE_GALLERY": "MESSAGES.UI.VALIDATE_GALLERY",
    # UI labels -> MESSAGES.Labels
    "UI.WIFI_CONNECTION": "MESSAGES.Labels.WIFI_CONNECTION",
    "UI.HOME_ASSISTANT_INTEGRATION": "MESSAGES.Labels.HOME_ASSISTANT_INTEGRATION",
    "UI.AVAILABLE_NETWORKS": "MESSAGES.WiFi.AVAILABLE_NETWORKS",
    "UI.CAMERA_DETECTION": "MESSAGES.Camera.DETECTION",
    "UI.AVAILABLE_CAMERAS": "MESSAGES.Camera.AVAILABLE_CAMERAS",
    "UI.DATA_PATH_LABEL": "MESSAGES.Labels.DATA_PATH",
    # StatusMessages
    "StatusMessages.PENDING": "MESSAGES.Status.PENDING",
    "StatusMessages.USER_ACTION_REQUIRED": "MESSAGES.Status.USER_ACTION_REQUIRED",
    "StatusMessages.AUTOMATION_RUNNING": "MESSAGES.Status.AUTOMATION_RUNNING",
    "StatusMessages.COMPLETED": "MESSAGES.Status.COMPLETED",
    "StatusMessages.FAILED": "MESSAGES.Status.FAILED",
    # Messages.Errors
    "Messages.MISSING_PARTICIPANT_ID": "MESSAGES.Errors.MISSING_PARTICIPANT_ID",
    "Messages.MISSING_USERNAME": "MESSAGES.Errors.MISSING_USERNAME",
    "Messages.NO_CAMERA_SELECTED": "MESSAGES.Errors.NO_CAMERA_SELECTED",
    # Network -> UI_CONFIG
    "Network.DEFAULT_HA_PORT": "MESSAGES.HomeAssistant.DEFAULT_PORT",
    "Network.DEFAULT_HA_URL": "MESSAGES.HomeAssistant.DEFAULT_URL",
    "Network.CONNECTION_TIMEOUT": "UI_CONFIG.CONNECTION_TIMEOUT",
    "Network.WIFI_SCAN_TIMEOUT": "UI_CONFIG.WIFI_SCAN_TIMEOUT",
    "Network.WIFI_CONNECT_TIMEOUT": "UI_CONFIG.WIFI_CONNECT_TIMEOUT",
    # Process -> UI_CONFIG
    "Process.SUDO_TIMEOUT_SECONDS": "UI_CONFIG.SUDO_TIMEOUT_SECONDS",
    "Process.MONITOR_INTERVAL_MS": "UI_CONFIG.MONITOR_INTERVAL_MS",
    "Process.AUTO_SAVE_INTERVAL_MS": "UI_CONFIG.AUTO_SAVE_INTERVAL_MS",
    "Process.STATUS_UPDATE_INTERVAL_MS": "UI_CONFIG.STATUS_UPDATE_INTERVAL_MS",
    "Process.DEFAULT_TIMEOUT_MS": "UI_CONFIG.DEFAULT_TIMEOUT_MS",
    "Process.MAX_TIMEOUT_MS": "UI_CONFIG.MAX_TIMEOUT_MS",
    # Patterns -> VALIDATION
    "Patterns.PARTICIPANT_ID": "VALIDATION.PARTICIPANT_ID",
    "Patterns.IPV4_ADDRESS": "VALIDATION.IPV4_ADDRESS",
    # Templates -> MESSAGES.Placeholders or MESSAGES.Templates
    "Templates.PARTICIPANT_ID_PLACEHOLDER": "MESSAGES.Placeholders.PARTICIPANT_ID",
    "Templates.DEVICE_ID_PLACEHOLDER": "MESSAGES.Placeholders.DEVICE_ID",
    "Templates.USERNAME_PLACEHOLDER": "MESSAGES.Placeholders.USERNAME",
    "Templates.DATA_PATH_PLACEHOLDER": "MESSAGES.Placeholders.DATA_PATH",
    "Templates.POV_PICTURE_NAME": "MESSAGES.Templates.POV_PICTURE",
    "Templates.DATA_DIR_NAME": "MESSAGES.Templates.DATA_DIR",
    "Templates.FACES_DIR_NAME": "MESSAGES.Templates.FACES_DIR",
    # Gallery -> MESSAGES.Gallery
    "Gallery.ROLES": "MESSAGES.Gallery.ROLES",
    "Gallery.MIN_IMAGES_PER_ROLE": "MESSAGES.Gallery.MIN_IMAGES_PER_ROLE",
    "Gallery.FOLDER_SUFFIX": "MESSAGES.Gallery.FOLDER_SUFFIX",
    "Gallery.SELECTED_SUFFIX": "MESSAGES.Gallery.SELECTED_SUFFIX",
    # Services -> MESSAGES.Services
    "Services.FLASH_RUN_ON_BOOT": "MESSAGES.Services.FLASH_RUN_ON_BOOT",
    "Services.FLASH_PERIODIC_RESTART": "MESSAGES.Services.FLASH_PERIODIC_RESTART",
    "Services.SYSTEMD_TIMESYNCD": "MESSAGES.Services.SYSTEMD_TIMESYNCD",
    # Steps -> MESSAGES
    "Steps.TOTAL": "MESSAGES.TOTAL_STEPS",
    "Steps.TITLES": "MESSAGES.STEP_TITLES",
    # Logging -> MESSAGES.Logging
    "Logging.FORMAT": "MESSAGES.Logging.FORMAT",
    "Logging.DATE_FORMAT": "MESSAGES.Logging.DATE_FORMAT",
    "Logging.MAIN_LOG_FILE": "MESSAGES.Logging.MAIN_LOG_FILE",
    "Logging.ERROR_LOG_FILE": "MESSAGES.Logging.ERROR_LOG_FILE",
}


def update_imports_in_file(file_path: Path) -> bool:
    """Update imports in a single file."""
    print(f"Processing: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        # Find the import line
        import_match = re.search(r"^from constants import (.+)$", content, re.MULTILINE)

        if not import_match:
            print(f"  No constants import found")
            return False

        imported_names = [name.strip() for name in import_match.group(1).split(",")]
        print(f"  Found imports: {imported_names}")

        # Determine which new modules we need
        needed_modules = set()
        for name in imported_names:
            if name in IMPORT_MAPPING:
                needed_modules.add(IMPORT_MAPPING[name])

        # Build new import lines
        new_imports = []
        if "UI_CONFIG" in needed_modules:
            new_imports.append("from config.ui_config import UI_CONFIG")
        if "MESSAGES" in needed_modules:
            new_imports.append("from config.messages import MESSAGES")
        if "VALIDATION" in needed_modules:
            new_imports.append("from config.validation_patterns import VALIDATION")

        # Replace the import line
        content = re.sub(
            r"^from constants import .+$",
            "\n".join(new_imports),
            content,
            flags=re.MULTILINE,
        )

        # Now replace all attribute accesses
        # Sort by length (longest first) to avoid partial replacements
        for old_attr, new_attr in sorted(
            ATTRIBUTE_MAPPING.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if any(name in old_attr for name in imported_names):
                # Use word boundary to avoid partial matches
                pattern = r"\b" + re.escape(old_attr) + r"\b"
                content = re.sub(pattern, new_attr, content)

        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            print(f"  ✓ Updated")
            return True
        else:
            print(f"  No changes needed")
            return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Main migration function."""
    base_dir = Path(__file__).parent

    # Files to update
    files_to_update = [
        base_dir / "main.py",
        base_dir / "steps" / "wifi_connection_step.py",
        base_dir / "steps" / "camera_setup_step.py",
        base_dir / "steps" / "time_sync_step.py",
        base_dir / "steps" / "gallery_creation_step.py",
        base_dir / "core" / "process_runner_old.py",
    ]

    updated_count = 0
    for file_path in files_to_update:
        if file_path.exists():
            if update_imports_in_file(file_path):
                updated_count += 1
        else:
            print(f"File not found: {file_path}")

    print(f"\n✓ Updated {updated_count} files")
    print("\nNext steps:")
    print("1. Review the changes")
    print("2. Test the application")
    print("3. Delete constants.py when everything works")


if __name__ == "__main__":
    main()
