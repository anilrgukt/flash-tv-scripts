"""Shared pytest fixtures for FLASH-TV GUI tests.

This module provides common fixtures for unit, integration, and e2e tests.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

# Add the gui_second_version directory to Python path
GUI_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(GUI_DIR))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

# Import after path setup
from core import ProcessRunner, StateManager  # noqa: E402
from models import StepDefinition, WizardState  # noqa: E402
from models.enums import StepContentType  # noqa: E402
from models.state_keys import UserInputKey, WizardStep  # noqa: E402


# ============================================================================
# Application Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Create a QApplication instance for the test session.

    This is required for any Qt widget tests.
    """
    # Check if QApplication already exists
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app as pytest-qt handles cleanup


# ============================================================================
# State Fixtures
# ============================================================================


@pytest.fixture
def wizard_state() -> WizardState:
    """Create a fresh WizardState instance."""
    return WizardState()


@pytest.fixture
def populated_state() -> WizardState:
    """Create a WizardState with common test data populated."""
    state = WizardState()
    state.set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
    state.set_user_input(UserInputKey.DEVICE_ID, "007")
    state.set_user_input(UserInputKey.USERNAME, "flashsys007")
    state.set_user_input(UserInputKey.DATA_PATH, "/home/flashsys007/data/P1-3999028007_data")
    state.set_user_input(UserInputKey.SUDO_PASSWORD, "testpass")
    return state


@pytest.fixture
def completed_steps_state() -> WizardState:
    """Create a WizardState with several steps marked completed."""
    state = WizardState()
    state.set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
    state.set_user_input(UserInputKey.DEVICE_ID, "007")
    state.set_user_input(UserInputKey.USERNAME, "flashsys007")
    state.set_user_input(UserInputKey.DATA_PATH, "/home/flashsys007/data/P1-3999028007_data")
    state.set_user_input(UserInputKey.WIFI_CONNECTED, True)
    state.set_user_input(UserInputKey.WIFI_SSID, "TestNetwork")

    # Mark first few steps as completed
    for step in [
        WizardStep.PARTICIPANT_SETUP,
        WizardStep.WIFI_CONNECTION,
        WizardStep.TIME_SYNC,
    ]:
        state.mark_step_completed(step)

    return state


@pytest.fixture
def fully_completed_state() -> WizardState:
    """Create a WizardState with all steps completed (for final step tests)."""
    state = WizardState()
    state.set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
    state.set_user_input(UserInputKey.DEVICE_ID, "007")
    state.set_user_input(UserInputKey.USERNAME, "flashsys007")
    state.set_user_input(UserInputKey.DATA_PATH, "/home/flashsys007/data/P1-3999028007_data")
    state.set_user_input(UserInputKey.SUDO_PASSWORD, "testpass")
    state.set_user_input(UserInputKey.WIFI_CONNECTED, True)
    state.set_user_input(UserInputKey.WIFI_SSID, "TestNetwork")
    state.set_user_input(UserInputKey.SELECTED_CAMERA, "/dev/video0")
    state.set_user_input(UserInputKey.SELECTED_CAMERA_NAME, "Test Camera")
    state.set_user_input(UserInputKey.CAMERA_TESTED, True)
    state.set_user_input(UserInputKey.POV_PICTURE_COMPLETE, True)
    state.set_user_input(UserInputKey.TIME_SYNCED, True)
    state.set_user_input(UserInputKey.SMART_PLUG_VERIFIED, True)
    state.set_user_input(
        UserInputKey.GALLERY_PATH,
        "/home/flashsys007/data/P1-3999028007_data/P1-3999028007_faces",
    )
    state.set_user_input(UserInputKey.GALLERY_VALIDATED, True)
    state.set_user_input(UserInputKey.GALLERY_TOTAL_IMAGES, 15)
    state.set_user_input(UserInputKey.GAZE_TEST_COMPLETE, True)
    state.set_user_input(UserInputKey.GAZE_DETECTION_VERIFIED, True)
    state.set_user_input(UserInputKey.SERVICES_VERIFIED, True)

    # Mark all steps as completed
    for step in WizardStep:
        state.mark_step_completed(step)

    return state


# ============================================================================
# State Manager Fixtures
# ============================================================================


@pytest.fixture
def temp_state_file(tmp_path: Path) -> Path:
    """Create a temporary state file path."""
    return tmp_path / "wizard_state.json"


@pytest.fixture
def state_manager(temp_state_file: Path) -> StateManager:
    """Create a StateManager with a temporary state file."""
    return StateManager(state_file_path=str(temp_state_file))


@pytest.fixture
def state_manager_with_data(
    state_manager: StateManager, populated_state: WizardState
) -> StateManager:
    """Create a StateManager with pre-saved state data."""
    state_manager.save_state(populated_state, force=True)
    return state_manager


# ============================================================================
# Process Runner Fixtures
# ============================================================================


@pytest.fixture
def mock_process_runner(wizard_state: WizardState) -> ProcessRunner:
    """Create a ProcessRunner with mocked subprocess calls."""
    runner = ProcessRunner(wizard_state)
    return runner


@pytest.fixture
def mock_subprocess() -> Generator[MagicMock, None, None]:
    """Mock subprocess module for testing command execution."""
    with patch("subprocess.Popen") as mock_popen, patch("subprocess.run") as mock_run:
        # Configure mock Popen
        mock_process = MagicMock()
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline.return_value = b""
        mock_process.communicate.return_value = (b"success", b"")
        mock_popen.return_value = mock_process

        # Configure mock run
        mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")

        yield {"popen": mock_popen, "run": mock_run, "process": mock_process}


# ============================================================================
# Step Definition Fixtures
# ============================================================================


@pytest.fixture
def sample_step_definition() -> StepDefinition:
    """Create a sample step definition for testing."""
    return StepDefinition(
        step_id=WizardStep.PARTICIPANT_SETUP,
        title="Test Step",
        description="A test step for unit testing",
        content_type=StepContentType.MANUAL,
        prerequisites=[],
        validation_rules=[],
    )


@pytest.fixture
def all_step_definitions() -> list[StepDefinition]:
    """Get all step definitions from the factory."""
    from steps import StepFactory

    return StepFactory.create_step_definitions()


# ============================================================================
# Mock External Dependencies
# ============================================================================


@pytest.fixture
def mock_network() -> Generator[dict[str, MagicMock], None, None]:
    """Mock network-related operations."""
    with (
        patch("socket.socket") as mock_socket,
        patch("urllib.request.urlopen") as mock_urlopen,
    ):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Connection successful
        mock_socket.return_value.__enter__.return_value = mock_sock

        mock_response = MagicMock()
        mock_response.read.return_value = b"OK"
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        yield {"socket": mock_socket, "urlopen": mock_urlopen}


@pytest.fixture
def mock_camera() -> Generator[MagicMock, None, None]:
    """Mock OpenCV camera operations."""
    with patch("cv2.VideoCapture") as mock_cap:
        mock_camera = MagicMock()
        mock_camera.isOpened.return_value = True
        mock_camera.read.return_value = (True, MagicMock())
        mock_camera.get.return_value = 640  # Width
        mock_cap.return_value = mock_camera

        yield mock_cap


@pytest.fixture
def mock_file_system(tmp_path: Path) -> dict[str, Path]:
    """Create a mock file system structure for testing."""
    # Create directory structure
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    participant_data = data_dir / "P1-3999028007_data"
    participant_data.mkdir()

    faces_dir = participant_data / "P1-3999028007_faces"
    faces_dir.mkdir()

    # Create some test files
    log_file = participant_data / "P1-3999028007_flash_log_2025-01-01_12-00-00.txt"
    log_file.write_text(
        "2025-01-01 12:00:00.000 1 1 1 0.1 0.2 0.9 0.0 10 20 50 80 Gaze-det\n"
    )

    stderr_log = participant_data / "P1-3999028007_flash_logstderr.log"
    stderr_log.write_text("Loading model...\nModel loaded successfully\n")

    return {
        "root": tmp_path,
        "data_dir": data_dir,
        "participant_data": participant_data,
        "faces_dir": faces_dir,
        "log_file": log_file,
        "stderr_log": stderr_log,
    }


# ============================================================================
# Gaze Data Fixtures
# ============================================================================


@pytest.fixture
def sample_gaze_log_content() -> str:
    """Sample gaze log file content for testing."""
    return """2025-01-01 12:00:00.000000 1 1 1 0.1 0.2 0.9 0.0 10 20 50 80 Gaze-det
2025-01-01 12:00:01.000000 2 1 1 0.15 0.25 0.85 0.0 15 25 55 85 Gaze-det
2025-01-01 12:00:02.000000 3 0 0 None None None None None None None None No-face-detected
2025-01-01 12:00:03.000000 4 2 1 None None None None 20 30 60 90 Gaze-no-det
2025-01-01 12:00:04.000000 5 1 1 -0.1 -0.15 0.95 0.0 12 22 52 82 Gaze-det
"""


@pytest.fixture
def sample_gaze_log_file(tmp_path: Path, sample_gaze_log_content: str) -> Path:
    """Create a sample gaze log file for testing."""
    log_file = tmp_path / "test_gaze_log.txt"
    log_file.write_text(sample_gaze_log_content)
    return log_file


# ============================================================================
# Widget Test Helpers
# ============================================================================


@pytest.fixture
def wait_signal(qtbot):
    """Helper to wait for Qt signals with timeout."""

    def _wait_signal(signal, timeout=1000):
        with qtbot.waitSignal(signal, timeout=timeout):
            pass

    return _wait_signal


@pytest.fixture
def click_button(qtbot):
    """Helper to click buttons in tests."""

    def _click(button):
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

    return _click


@pytest.fixture
def type_text(qtbot):
    """Helper to type text into widgets."""

    def _type(widget, text):
        widget.clear()
        qtbot.keyClicks(widget, text)

    return _type


# ============================================================================
# Happy Path Test Data
# ============================================================================


@pytest.fixture
def happy_path_inputs() -> dict[str, Any]:
    """Input data for happy path e2e test."""
    return {
        "participant_id": "P1-3999028",
        "device_id": "007",
        "username": "flashsys007",
        "data_path": "/home/flashsys007/data",
        "sudo_password": "testpass123",
        "wifi_ssid": "FlashTV-Network",
        "camera_index": 0,
        "num_faces": 3,
    }


# ============================================================================
# Adaptive Font Scaling Fixture
# ============================================================================


@pytest.fixture(autouse=True)
def disable_adaptive_font_scaling():
    """Disable adaptive font scaling during tests to avoid timer issues."""
    with patch("utils.adaptive_font.AdaptiveFontScaler.apply_adaptive_scaling"):
        yield


# ============================================================================
# Dialog Mocking Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def mock_dialogs():
    """Mock all dialog boxes to prevent them from appearing during tests."""
    with (
        patch("PySide6.QtWidgets.QMessageBox.information") as mock_info,
        patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning,
        patch("PySide6.QtWidgets.QMessageBox.critical") as mock_critical,
        patch("PySide6.QtWidgets.QMessageBox.question") as mock_question,
        patch("PySide6.QtWidgets.QFileDialog.getOpenFileName") as mock_open,
        patch("PySide6.QtWidgets.QFileDialog.getSaveFileName") as mock_save,
        patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory") as mock_dir,
        patch("PySide6.QtWidgets.QInputDialog.getText") as mock_text,
    ):
        # Configure default return values
        from PySide6.QtWidgets import QMessageBox

        mock_info.return_value = QMessageBox.StandardButton.Ok
        mock_warning.return_value = QMessageBox.StandardButton.Ok
        mock_critical.return_value = QMessageBox.StandardButton.Ok
        mock_question.return_value = QMessageBox.StandardButton.Yes
        mock_open.return_value = ("", "")
        mock_save.return_value = ("", "")
        mock_dir.return_value = ""
        mock_text.return_value = ("", False)

        yield {
            "information": mock_info,
            "warning": mock_warning,
            "critical": mock_critical,
            "question": mock_question,
            "open_file": mock_open,
            "save_file": mock_save,
            "get_dir": mock_dir,
            "get_text": mock_text,
        }


# ============================================================================
# Cleanup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Clean up any singleton instances between tests."""
    yield
    # Add any singleton cleanup here if needed


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables between tests."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)
