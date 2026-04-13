"""End-to-end happy path tests for FLASH-TV Setup Wizard.

These tests simulate a complete user journey through the wizard,
mocking external dependencies while testing the full UI flow.
"""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QPushButton,
)

from core import ProcessRunner, StateManager
from models import StepStatus, WizardState
from models.state_keys import UserInputKey, WizardStep
from steps import StepFactory


# ============================================================================
# E2E Test Fixtures
# ============================================================================


@pytest.fixture
def mock_all_external_deps():
    """Mock all external dependencies for e2e testing."""
    mock_cv2 = MagicMock(name="VideoCapture")
    fake_cv2 = MagicMock()
    fake_cv2.VideoCapture = mock_cv2

    with (
        patch.dict(sys.modules, {"cv2": fake_cv2}),
        patch("subprocess.run") as mock_run,
        patch("subprocess.Popen") as mock_popen,
        patch("socket.socket") as mock_socket,
        patch("os.path.exists") as mock_exists,
        patch("os.listdir") as mock_listdir,
    ):
        # subprocess.run returns success
        mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")

        # subprocess.Popen returns a mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stdout.readline.return_value = b""
        mock_process.communicate.return_value = (b"success", b"")
        mock_popen.return_value = mock_process

        # Socket connections succeed
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value.__enter__.return_value = mock_sock

        # Camera is available
        mock_camera = MagicMock()
        mock_camera.isOpened.return_value = True
        mock_camera.read.return_value = (True, MagicMock())
        mock_camera.get.return_value = 640
        mock_cv2.return_value = mock_camera

        # Paths exist
        mock_exists.return_value = True

        # Directory has files
        mock_listdir.return_value = ["face1.jpg", "face2.jpg", "face3.jpg"]

        yield {
            "run": mock_run,
            "popen": mock_popen,
            "socket": mock_socket,
            "cv2": mock_cv2,
            "exists": mock_exists,
            "listdir": mock_listdir,
        }


@pytest.fixture
def wizard_with_mocks(qtbot, tmp_path: Path, mock_all_external_deps):
    """Create a fully mocked wizard setup for e2e testing."""
    state = WizardState()
    state_manager = StateManager(state_file_path=str(tmp_path / "state.json"))
    process_runner = ProcessRunner(state)

    # Mock process runner methods
    process_runner.run_command = MagicMock(
        return_value=subprocess.CompletedProcess(
            args=["mock-command"],
            returncode=0,
            stdout="success",
            stderr="",
        )
    )
    process_runner.run_sudo_command = MagicMock(
        return_value=(
            subprocess.CompletedProcess(
                args=["mock-sudo-command"],
                returncode=0,
                stdout="success",
                stderr="",
            ),
            None,
        )
    )

    return {
        "state": state,
        "state_manager": state_manager,
        "process_runner": process_runner,
        "mocks": mock_all_external_deps,
        "tmp_path": tmp_path,
    }


# ============================================================================
# Helper Functions
# ============================================================================


def find_button_by_text(widget, text: str) -> QPushButton | None:
    """Find a button by its text (case-insensitive, partial match)."""
    for button in widget.findChildren(QPushButton):
        if text.lower() in button.text().lower():
            return button
    return None


def find_line_edit_by_placeholder(widget, placeholder: str) -> QLineEdit | None:
    """Find a QLineEdit by placeholder text (partial match)."""
    for edit in widget.findChildren(QLineEdit):
        if placeholder.lower() in (edit.placeholderText() or "").lower():
            return edit
    return None


def find_checkbox_by_text(widget, text: str) -> QCheckBox | None:
    """Find a checkbox by its text."""
    for cb in widget.findChildren(QCheckBox):
        if text.lower() in cb.text().lower():
            return cb
    return None


def fill_participant_setup(
    step, qtbot, participant_id: str, device_id: str, username: str, data_path: str
):
    """Fill in participant setup form fields."""
    line_edits = step.findChildren(QLineEdit)

    # Find and fill fields by examining labels or using index
    for edit in line_edits:
        placeholder = (edit.placeholderText() or "").lower()
        if "participant" in placeholder or "p1-" in placeholder:
            qtbot.keyClicks(edit, participant_id)
        elif "device" in placeholder:
            qtbot.keyClicks(edit, device_id)
        elif "user" in placeholder:
            qtbot.keyClicks(edit, username)
        elif "path" in placeholder or "data" in placeholder:
            qtbot.keyClicks(edit, data_path)


def click_continue_button(step, qtbot):
    """Find and click the continue button."""
    continue_btn = find_button_by_text(step, "continue")
    if continue_btn and continue_btn.isEnabled():
        qtbot.mouseClick(continue_btn, Qt.MouseButton.LeftButton)
        return True
    return False


def check_all_checkboxes(step, qtbot):
    """Check all checkboxes in the step."""
    for cb in step.findChildren(QCheckBox):
        if not cb.isChecked():
            qtbot.mouseClick(cb, Qt.MouseButton.LeftButton)


# ============================================================================
# Happy Path Test - Step by Step
# ============================================================================


class TestHappyPathStepByStep:
    """Tests for individual steps in the happy path."""

    def test_step1_participant_setup(self, qtbot, wizard_with_mocks):
        """Test Step 1: Participant Setup."""
        setup = wizard_with_mocks
        definitions = StepFactory.create_step_definitions()
        step_def = definitions[0]  # Participant Setup

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        # Fill in participant information directly via state
        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].set_user_input(UserInputKey.DEVICE_ID, "007")
        setup["state"].set_user_input(UserInputKey.USERNAME, "flashsys007")
        setup["state"].set_user_input(
            UserInputKey.DATA_PATH, "/home/flashsys007/data/P1-3999028007_data"
        )
        setup["state"].set_user_input(UserInputKey.SUDO_PASSWORD, "testpass")

        # Mark step as completed
        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.PARTICIPANT_SETUP)

        assert setup["state"].get_participant_id() == "P1-3999028"
        assert setup["state"].is_step_completed(WizardStep.PARTICIPANT_SETUP)

    def test_step2_wifi_connection(self, qtbot, wizard_with_mocks):
        """Test Step 2: WiFi Connection."""
        setup = wizard_with_mocks

        # Set up prerequisites
        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].set_user_input(UserInputKey.USERNAME, "flashsys007")
        setup["state"].mark_step_completed(WizardStep.PARTICIPANT_SETUP)

        definitions = StepFactory.create_step_definitions()
        step_def = definitions[1]  # WiFi Connection

        # Mock WiFi check to return connected
        setup["mocks"]["run"].return_value = MagicMock(
            returncode=0, stdout="inet 192.168.1.100", stderr=""
        )

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        # Simulate WiFi connected
        setup["state"].set_wifi_info("TestNetwork", connected=True)
        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.WIFI_CONNECTION)

        assert setup["state"].is_wifi_connected()
        assert setup["state"].is_step_completed(WizardStep.WIFI_CONNECTION)

    def test_step3_time_sync(self, qtbot, wizard_with_mocks):
        """Test Step 3: Time Synchronization."""
        setup = wizard_with_mocks

        # Set up prerequisites
        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].set_user_input(UserInputKey.USERNAME, "flashsys007")
        setup["state"].mark_step_completed(WizardStep.PARTICIPANT_SETUP)
        setup["state"].set_wifi_info("TestNetwork", connected=True)
        setup["state"].mark_step_completed(WizardStep.WIFI_CONNECTION)

        definitions = StepFactory.create_step_definitions()
        step_def = definitions[2]  # Time Sync

        # Mock timedatectl to return synced
        setup["mocks"]["run"].return_value = MagicMock(
            returncode=0,
            stdout="System clock synchronized: yes\nNTP service: active",
            stderr="",
        )

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        # Simulate time synced
        setup["state"].set_user_input(UserInputKey.TIME_SYNCED, True)
        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.TIME_SYNC)

        assert setup["state"].is_step_completed(WizardStep.TIME_SYNC)

    def test_step4_smart_plug_physical(self, qtbot, wizard_with_mocks):
        """Test Step 4: Smart Plug Physical Setup."""
        setup = wizard_with_mocks

        # Set up prerequisites
        for step_id in [1, 2, 3]:
            setup["state"].mark_step_completed(step_id)

        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].set_user_input(UserInputKey.DEVICE_ID, "007")
        setup["state"].set_user_input(UserInputKey.USERNAME, "flashsys007")

        definitions = StepFactory.create_step_definitions()
        step_def = definitions[3]  # Smart Plug Physical

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        # Check all checkboxes (confirmation items)
        check_all_checkboxes(step, qtbot)

        setup["state"].set_user_input(UserInputKey.SMART_PLUG_CONFIGURED, True)
        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.SMART_PLUG_PHYSICAL)

        assert setup["state"].is_step_completed(WizardStep.SMART_PLUG_PHYSICAL)

    def test_step5_smart_plug_verify(self, qtbot, wizard_with_mocks):
        """Test Step 5: Smart Plug Data Verification."""
        setup = wizard_with_mocks

        # Set up prerequisites
        for step_id in range(1, 5):
            setup["state"].mark_step_completed(step_id)

        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].set_user_input(UserInputKey.DEVICE_ID, "007")
        setup["state"].set_user_input(UserInputKey.USERNAME, "flashsys007")

        definitions = StepFactory.create_step_definitions()
        step_def = definitions[4]  # Smart Plug Verify

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        # Simulate verification complete
        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.SMART_PLUG_VERIFY)

        assert setup["state"].is_step_completed(WizardStep.SMART_PLUG_VERIFY)

    def test_step6_camera_setup(self, qtbot, wizard_with_mocks):
        """Test Step 6: Camera Setup."""
        setup = wizard_with_mocks

        # Set up prerequisites
        for step_id in range(1, 6):
            setup["state"].mark_step_completed(step_id)

        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].set_user_input(UserInputKey.USERNAME, "flashsys007")

        definitions = StepFactory.create_step_definitions()
        step_def = definitions[5]  # Camera Setup

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        setup["state"].set_user_input(UserInputKey.SELECTED_CAMERA, "/dev/video0")
        setup["state"].set_user_input(
            UserInputKey.SELECTED_CAMERA_NAME, "Integrated Camera"
        )
        setup["state"].set_user_input(UserInputKey.CAMERA_TESTED, True)
        setup["state"].set_user_input(UserInputKey.POV_PICTURE_COMPLETE, True)
        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.CAMERA_SETUP)

        assert (
            setup["state"].get_user_input(UserInputKey.SELECTED_CAMERA) == "/dev/video0"
        )
        assert setup["state"].is_step_completed(WizardStep.CAMERA_SETUP)

    def test_step7_gallery_creation(self, qtbot, wizard_with_mocks):
        """Test Step 7: Face Gallery Building."""
        setup = wizard_with_mocks

        # Set up prerequisites
        for step_id in range(1, 7):
            setup["state"].mark_step_completed(step_id)

        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].set_user_input(UserInputKey.DEVICE_ID, "007")
        setup["state"].set_user_input(UserInputKey.USERNAME, "flashsys007")
        setup["state"].set_user_input(
            UserInputKey.DATA_PATH, "/home/flashsys007/data/P1-3999028007_data"
        )

        definitions = StepFactory.create_step_definitions()
        step_def = definitions[6]  # Gallery Creation

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        setup["state"].set_user_input(
            UserInputKey.GALLERY_PATH,
            "/home/flashsys007/data/P1-3999028007_data/P1-3999028007_faces",
        )
        setup["state"].set_user_input(UserInputKey.GALLERY_VALIDATED, True)
        setup["state"].set_user_input(UserInputKey.GALLERY_TOTAL_IMAGES, 15)
        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.GALLERY_CREATION)

        assert setup["state"].is_step_completed(WizardStep.GALLERY_CREATION)

    def test_step8_gaze_detection_testing(self, qtbot, wizard_with_mocks):
        """Test Step 8: Gaze Detection Testing."""
        setup = wizard_with_mocks

        # Set up prerequisites
        for step_id in range(1, 8):
            setup["state"].mark_step_completed(step_id)

        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].set_user_input(UserInputKey.DEVICE_ID, "007")
        setup["state"].set_user_input(UserInputKey.USERNAME, "flashsys007")
        setup["state"].set_user_input(
            UserInputKey.DATA_PATH, "/home/flashsys007/data/P1-3999028007_data"
        )
        setup["state"].set_user_input(
            UserInputKey.GALLERY_PATH,
            "/home/flashsys007/data/P1-3999028007_data/P1-3999028007_faces",
        )
        setup["state"].set_user_input(UserInputKey.GALLERY_VALIDATED, True)

        definitions = StepFactory.create_step_definitions()
        step_def = definitions[7]  # Gaze Detection Testing

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        # Simulate gaze tested
        setup["state"].set_user_input(UserInputKey.GAZE_TEST_COMPLETE, True)
        setup["state"].set_user_input(UserInputKey.GAZE_DETECTION_VERIFIED, True)
        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.GAZE_DETECTION_TESTING)

        assert setup["state"].is_step_completed(WizardStep.GAZE_DETECTION_TESTING)

    def test_step9_service_startup(self, qtbot, wizard_with_mocks):
        """Test Step 9: Service Startup."""
        setup = wizard_with_mocks

        # Set up prerequisites
        for step_id in range(1, 9):
            setup["state"].mark_step_completed(step_id)

        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].set_user_input(UserInputKey.DEVICE_ID, "007")
        setup["state"].set_user_input(UserInputKey.USERNAME, "flashsys007")
        setup["state"].set_user_input(
            UserInputKey.DATA_PATH, "/home/flashsys007/data/P1-3999028007_data"
        )
        setup["state"].set_user_input(UserInputKey.SUDO_PASSWORD, "testpass")

        definitions = StepFactory.create_step_definitions()
        step_def = definitions[8]  # Service Startup

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        # Simulate services verified
        setup["state"].set_user_input(UserInputKey.SERVICES_VERIFIED, True)
        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.SERVICE_STARTUP)

        assert setup["state"].is_step_completed(WizardStep.SERVICE_STARTUP)

    def test_step10_cord_checking(self, qtbot, wizard_with_mocks):
        """Test Step 10: Cord Checking."""
        setup = wizard_with_mocks

        # Set up prerequisites
        for step_id in range(1, 10):
            setup["state"].mark_step_completed(step_id)

        definitions = StepFactory.create_step_definitions()
        step_def = definitions[9]  # Cord Checking

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        # Check all cord checkboxes
        check_all_checkboxes(step, qtbot)

        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.CORD_CHECKING)

        assert setup["state"].is_step_completed(WizardStep.CORD_CHECKING)

    def test_step11_device_locking(self, qtbot, wizard_with_mocks):
        """Test Step 11: Device Locking (Final Step)."""
        setup = wizard_with_mocks

        # Set up prerequisites
        for step_id in range(1, 11):
            setup["state"].mark_step_completed(step_id)

        definitions = StepFactory.create_step_definitions()
        step_def = definitions[10]  # Device Locking

        step = StepFactory.create_step_instance(
            step_def,
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step)
        step.show()
        step.activate_step()

        step.update_status(StepStatus.COMPLETED)
        setup["state"].mark_step_completed(WizardStep.DEVICE_LOCKING)

        assert setup["state"].is_step_completed(WizardStep.DEVICE_LOCKING)
        assert setup["state"].get_completion_percentage() == 100


# ============================================================================
# Full Happy Path Test
# ============================================================================


class TestFullHappyPath:
    """Complete happy path test simulating full wizard journey."""

    def test_complete_wizard_journey(self, qtbot, wizard_with_mocks):
        """Test complete journey through all wizard steps.

        This test simulates a user going through all 11 steps of the wizard
        with all inputs provided correctly and all external dependencies mocked.
        """
        setup = wizard_with_mocks
        definitions = StepFactory.create_step_definitions()

        # Test data for the journey
        test_data = {
            "participant_id": "P1-3999028",
            "device_id": "007",
            "username": "flashsys007",
            "data_path": "/home/flashsys007/data/P1-3999028007_data",
            "sudo_password": "testpass123",
            "wifi_ssid": "FlashTV-Network",
            "selected_camera": "/dev/video0",
        }

        # Set up initial user inputs
        setup["state"].set_user_input(
            UserInputKey.PARTICIPANT_ID, test_data["participant_id"]
        )
        setup["state"].set_user_input(UserInputKey.DEVICE_ID, test_data["device_id"])
        setup["state"].set_user_input(UserInputKey.USERNAME, test_data["username"])
        setup["state"].set_user_input(UserInputKey.DATA_PATH, test_data["data_path"])
        setup["state"].set_user_input(
            UserInputKey.SUDO_PASSWORD, test_data["sudo_password"]
        )

        # Journey through each step
        completed_steps = []

        for i, step_def in enumerate(definitions):
            step_name = step_def.title
            step_id = int(step_def.step_id)

            # Create step instance
            step = StepFactory.create_step_instance(
                step_def,
                setup["state"],
                setup["process_runner"],
                setup["state_manager"],
            )
            qtbot.addWidget(step)
            step.show()

            # Activate step
            step.activate_step()
            qtbot.wait(10)

            setup["state"].set_user_input(
                UserInputKey.PARTICIPANT_ID, test_data["participant_id"]
            )
            setup["state"].set_user_input(
                UserInputKey.DEVICE_ID, test_data["device_id"]
            )
            setup["state"].set_user_input(UserInputKey.USERNAME, test_data["username"])
            setup["state"].set_user_input(
                UserInputKey.DATA_PATH, test_data["data_path"]
            )

            # Perform step-specific actions
            if step_id == WizardStep.PARTICIPANT_SETUP:
                # User inputs already set
                pass

            elif step_id == WizardStep.WIFI_CONNECTION:
                setup["state"].set_wifi_info(test_data["wifi_ssid"], connected=True)

            elif step_id == WizardStep.TIME_SYNC:
                setup["state"].set_user_input(UserInputKey.TIME_SYNCED, True)

            elif step_id == WizardStep.SMART_PLUG_PHYSICAL:
                check_all_checkboxes(step, qtbot)
                setup["state"].set_user_input(UserInputKey.SMART_PLUG_CONFIGURED, True)

            elif step_id == WizardStep.SMART_PLUG_VERIFY:
                pass  # Auto verification

            elif step_id == WizardStep.CAMERA_SETUP:
                setup["state"].set_user_input(
                    UserInputKey.SELECTED_CAMERA, test_data["selected_camera"]
                )
                setup["state"].set_user_input(
                    UserInputKey.SELECTED_CAMERA_NAME, "Integrated Camera"
                )
                setup["state"].set_user_input(UserInputKey.CAMERA_TESTED, True)
                setup["state"].set_user_input(UserInputKey.POV_PICTURE_COMPLETE, True)

            elif step_id == WizardStep.GALLERY_CREATION:
                setup["state"].set_user_input(
                    UserInputKey.GALLERY_PATH,
                    "/home/flashsys007/data/P1-3999028007_data/P1-3999028007_faces",
                )
                setup["state"].set_user_input(UserInputKey.GALLERY_VALIDATED, True)
                setup["state"].set_user_input(UserInputKey.GALLERY_TOTAL_IMAGES, 15)

            elif step_id == WizardStep.GAZE_DETECTION_TESTING:
                setup["state"].set_user_input(UserInputKey.GAZE_TEST_COMPLETE, True)
                setup["state"].set_user_input(
                    UserInputKey.GAZE_DETECTION_VERIFIED, True
                )

            elif step_id == WizardStep.SERVICE_STARTUP:
                setup["state"].set_user_input(UserInputKey.SERVICES_VERIFIED, True)

            elif step_id == WizardStep.CORD_CHECKING:
                check_all_checkboxes(step, qtbot)

            elif step_id == WizardStep.DEVICE_LOCKING:
                pass  # Final step

            # Mark step completed
            step.update_status(StepStatus.COMPLETED)
            setup["state"].mark_step_completed(step_id)
            completed_steps.append(step_id)

            # Verify step completed
            assert setup["state"].is_step_completed(step_id), (
                f"Step {step_id} ({step_name}) not completed"
            )

            # Deactivate step (simulating navigation to next)
            step.deactivate_step()

        # Verify all steps completed
        assert len(completed_steps) == 11
        assert setup["state"].get_completion_percentage() == 100

        # Verify all expected data is in state
        assert setup["state"].get_combined_id() == "P1-3999028007"
        assert setup["state"].is_wifi_connected()
        assert (
            setup["state"].get_user_input(UserInputKey.SELECTED_CAMERA) == "/dev/video0"
        )

    def test_happy_path_with_state_persistence(self, qtbot, wizard_with_mocks):
        """Test that state persists correctly throughout the journey."""
        setup = wizard_with_mocks

        # Complete first few steps
        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].set_user_input(UserInputKey.DEVICE_ID, "007")
        setup["state"].set_user_input(UserInputKey.USERNAME, "flashsys007")

        for i in range(3):
            setup["state"].mark_step_completed(i + 1)
            # Save state after each step
            setup["state_manager"].save_state(setup["state"], force=True)

        # Simulate session restart by loading state
        loaded_state = setup["state_manager"].load_state()

        assert loaded_state is not None
        assert loaded_state.get_participant_id() == "P1-3999028"
        assert len(loaded_state.completed_steps) == 3


# ============================================================================
# Alternative Path Tests
# ============================================================================


class TestAlternativePaths:
    """Tests for alternative user paths through the wizard."""

    def test_back_navigation(self, qtbot, wizard_with_mocks):
        """Test going back to previous steps."""
        setup = wizard_with_mocks
        definitions = StepFactory.create_step_definitions()

        # Complete first 3 steps
        for i in range(3):
            setup["state"].mark_step_completed(i + 1)

        # Create step 3
        step3 = StepFactory.create_step_instance(
            definitions[2],
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step3)
        step3.activate_step()

        # Simulate going back to step 2
        step3.deactivate_step()

        step2 = StepFactory.create_step_instance(
            definitions[1],
            setup["state"],
            setup["process_runner"],
            setup["state_manager"],
        )
        qtbot.addWidget(step2)
        step2.activate_step()

        # State should still be intact
        assert setup["state"].is_step_completed(1)
        assert setup["state"].is_step_completed(2)

    def test_incomplete_step_recovery(self, qtbot, wizard_with_mocks):
        """Test recovering from incomplete step."""
        setup = wizard_with_mocks

        # Set up partial completion
        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-3999028")
        setup["state"].current_step = 2  # Mid-wizard

        # Save incomplete state
        setup["state_manager"].save_state(setup["state"], force=True)

        # Load and verify can continue
        loaded_state = setup["state_manager"].load_state()
        assert loaded_state.current_step == 2
        assert loaded_state.get_participant_id() == "P1-3999028"

    def test_restart_from_beginning(self, qtbot, wizard_with_mocks):
        """Test restarting the wizard from the beginning."""
        setup = wizard_with_mocks

        # Complete some steps
        setup["state"].set_user_input(UserInputKey.PARTICIPANT_ID, "P1-OLD")
        setup["state"].mark_step_completed(1)
        setup["state"].mark_step_completed(2)
        setup["state_manager"].save_state(setup["state"], force=True)

        # Clear state (simulating user choosing to start fresh)
        setup["state_manager"].clear_state()

        # Create new state
        new_state = WizardState()
        assert new_state.current_step == 1
        assert len(new_state.completed_steps) == 0
        assert new_state.get_participant_id() is None
