"""Screenshot capture script for visual testing of FLASH-TV GUI.

This script launches the wizard, navigates through all steps, and captures
screenshots of each view for visual review.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the gui_second_version directory to Python path
GUI_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(GUI_DIR))

from PySide6.QtWidgets import QApplication


def create_mock_dependencies():
    """Create mock patches for external dependencies."""
    patches = []

    # Mock subprocess to prevent actual shell commands
    mock_subprocess = patch("subprocess.Popen")
    mock_popen = mock_subprocess.start()
    mock_process = MagicMock()
    mock_process.poll.return_value = 0
    mock_process.returncode = 0
    mock_process.stdout.readline.return_value = b""
    mock_process.communicate.return_value = (b"mock output", b"")
    mock_popen.return_value = mock_process
    patches.append(mock_subprocess)

    # Mock subprocess.run
    mock_run = patch("subprocess.run")
    mock_run_result = mock_run.start()
    mock_run_result.return_value = MagicMock(
        returncode=0, stdout="mock output", stderr=""
    )
    patches.append(mock_run)

    # Mock socket for network checks
    mock_socket = patch("socket.socket")
    mock_sock = mock_socket.start()
    mock_sock_instance = MagicMock()
    mock_sock_instance.connect_ex.return_value = 0
    mock_sock.return_value.__enter__.return_value = mock_sock_instance
    patches.append(mock_socket)

    # Mock cv2 for camera operations
    mock_cv2 = patch.dict("sys.modules", {"cv2": MagicMock()})
    mock_cv2.start()
    patches.append(mock_cv2)

    # Mock os.path.exists to return True for common paths
    original_exists = Path.exists

    def mock_exists(self):
        path_str = str(self)
        # Return True for data directories and common paths
        if any(
            x in path_str
            for x in ["flashsys", "data", "faces", "gallery", ".csv", ".log"]
        ):
            return True
        return original_exists(self)

    mock_path_exists = patch.object(Path, "exists", mock_exists)
    mock_path_exists.start()
    patches.append(mock_path_exists)

    # Mock QMessageBox dialogs
    mock_msgbox_info = patch("PySide6.QtWidgets.QMessageBox.information")
    mock_msgbox_info.start()
    patches.append(mock_msgbox_info)

    mock_msgbox_warning = patch("PySide6.QtWidgets.QMessageBox.warning")
    mock_msgbox_warning.start()
    patches.append(mock_msgbox_warning)

    mock_msgbox_question = patch("PySide6.QtWidgets.QMessageBox.question")
    mock_q = mock_msgbox_question.start()
    from PySide6.QtWidgets import QMessageBox

    mock_q.return_value = QMessageBox.StandardButton.No  # Don't recover session
    patches.append(mock_msgbox_question)

    return patches


def capture_screenshots():
    """Main function to capture screenshots of all wizard steps."""
    # Create output directory
    output_dir = GUI_DIR / "tests" / "visual" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Screenshots will be saved to: {output_dir}")

    # Create mocks before importing the main module
    patches = create_mock_dependencies()

    try:
        # Import after mocks are in place
        from config.messages import MESSAGES
        from main import FlashTVSetupWizard
        from models.state_keys import UserInputKey

        # Create application
        app = QApplication(sys.argv)

        # Create wizard
        wizard = FlashTVSetupWizard()
        wizard.resize(1400, 900)
        wizard.show()

        # Pre-populate state with test data so steps render properly
        wizard.state.set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        wizard.state.set_user_input(UserInputKey.DEVICE_ID, "007")
        wizard.state.set_user_input(UserInputKey.USERNAME, "flashsys007")
        wizard.state.set_user_input(
            UserInputKey.DATA_PATH, "/home/flashsys007/data/P1-3999028007_data"
        )
        wizard.state.set_user_input(UserInputKey.WIFI_SSID, "FLASH-Network")
        wizard.state.set_user_input(UserInputKey.WIFI_CONNECTED, True)
        wizard.state.set_user_input(UserInputKey.SELECTED_CAMERA, "/dev/video0")
        wizard.state.set_user_input(
            UserInputKey.SELECTED_CAMERA_NAME, "Screenshot Camera"
        )
        wizard.state.set_user_input(UserInputKey.CAMERA_TESTED, True)
        wizard.state.set_user_input(UserInputKey.POV_PICTURE_COMPLETE, True)
        wizard.state.set_user_input(
            UserInputKey.GALLERY_PATH,
            "/home/flashsys007/data/P1-3999028007_data/P1-3999028007_faces",
        )
        wizard.state.set_user_input(UserInputKey.GALLERY_VALIDATED, True)

        # Process events to render
        app.processEvents()
        time.sleep(0.3)

        screenshots_captured = []

        # Capture each step
        for step_id in range(1, MESSAGES.TOTAL_STEPS + 1):
            step_title = MESSAGES.STEP_TITLES.get(step_id, f"Step {step_id}")
            print(f"Capturing Step {step_id}: {step_title}")

            # Navigate to step
            wizard.navigate_to_step(step_id)

            # Process events and wait for rendering
            app.processEvents()
            time.sleep(0.5)  # Allow time for UI to fully render
            app.processEvents()

            # Capture screenshot
            screenshot = wizard.grab()
            filename = f"step_{step_id:02d}_{step_title.lower().replace(' ', '_').replace('/', '_')}.png"
            filepath = output_dir / filename
            screenshot.save(str(filepath))

            screenshots_captured.append(filepath)
            print(f"  Saved: {filename}")

        # Close wizard
        wizard.close()
        app.processEvents()

        print(f"\nCaptured {len(screenshots_captured)} screenshots!")
        print(f"Location: {output_dir}")

        return screenshots_captured

    finally:
        # Stop all patches
        for p in patches:
            try:
                p.stop()
            except Exception:
                pass


if __name__ == "__main__":
    captured = capture_screenshots()
    print("\nScreenshots captured:")
    for path in captured:
        print(f"  - {path.name}")
