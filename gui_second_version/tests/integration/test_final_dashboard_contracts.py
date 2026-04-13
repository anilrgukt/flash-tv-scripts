from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from core import ProcessRunner, StateManager
from models import StepDefinition, WizardState
from models.enums import StepContentType
from models.state_keys import WizardStep
from steps import StepFactory


@pytest.fixture
def step_definition_device_locking() -> StepDefinition:
    return StepDefinition(
        step_id=WizardStep.DEVICE_LOCKING,
        title="Screen Locking and Final Setup",
        description="Lock the screen and prepare system for autonomous operation.",
        content_type=StepContentType.MANUAL,
        prerequisites=[],
        validation_rules=[],
    )


@pytest.fixture
def mock_process_runner(fully_completed_state: WizardState) -> ProcessRunner:
    return ProcessRunner(fully_completed_state)


class TestFinalDashboardContracts:
    def test_flash_error_dashboard_reads_current_stderr_log_name(
        self,
        qtbot,
        tmp_path,
        fully_completed_state: WizardState,
        mock_process_runner: ProcessRunner,
        step_definition_device_locking: StepDefinition,
        state_manager: StateManager,
        monkeypatch,
    ):
        data_path = tmp_path / "P1-3999028007_data"
        data_path.mkdir()
        stderr_log = data_path / "P1-3999028007_flash_logstderr.log"
        stderr_log.write_text("real stderr line\n", encoding="utf-8")
        legacy_log = data_path / "P1-3999028007_stderr_log.txt"
        legacy_log.write_text("legacy stderr line\n", encoding="utf-8")

        monkeypatch.setattr(
            "steps.device_locking_step.get_participant_data_dir",
            lambda username, participant_id, device_id="": data_path,
        )

        step = StepFactory.create_step_instance(
            step_definition_device_locking,
            fully_completed_state,
            mock_process_runner,
            state_manager,
        )
        qtbot.addWidget(step)
        step.stderr_tailer.get_all_content_with_errors = MagicMock(
            return_value=(["stderr"], ["actual dashboard error"])
        )

        rendered = step._get_last_flash_error()

        step.stderr_tailer.get_all_content_with_errors.assert_called_once_with(
            str(stderr_log)
        )
        assert "actual dashboard error" in rendered

    def test_dashboard_uses_latest_main_flash_log_timestamp_and_ignores_rot_reg(
        self,
        qtbot,
        tmp_path,
        fully_completed_state: WizardState,
        mock_process_runner: ProcessRunner,
        step_definition_device_locking: StepDefinition,
        state_manager: StateManager,
        monkeypatch,
    ):
        data_path = tmp_path / "P1-3999028007_data"
        data_path.mkdir()

        main_old = data_path / "P1-3999028007_flash_log_2025-01-01_12-00-00.txt"
        main_old.write_text("older main line\n", encoding="utf-8")

        main_latest = data_path / "P1-3999028007_flash_log_2025-01-01_12-05-00.txt"
        main_latest.write_text("latest main line\n", encoding="utf-8")

        rot_latest = data_path / "P1-3999028007_flash_log_2025-01-01_12-06-00_rot.txt"
        rot_latest.write_text("rotation line\n", encoding="utf-8")

        reg_latest = data_path / "P1-3999028007_flash_log_2025-01-01_12-07-00_reg.txt"
        reg_latest.write_text("secondary line\n", encoding="utf-8")

        os.utime(main_old, (20, 20))
        os.utime(main_latest, (10, 10))
        os.utime(rot_latest, (3, 3))
        os.utime(reg_latest, (4, 4))

        monkeypatch.setattr(
            "steps.device_locking_step.get_participant_data_dir",
            lambda username, participant_id, device_id="": data_path,
        )

        step = StepFactory.create_step_instance(
            step_definition_device_locking,
            fully_completed_state,
            mock_process_runner,
            state_manager,
        )
        qtbot.addWidget(step)

        assert step._get_last_gaze_log_line() == "latest main line"
