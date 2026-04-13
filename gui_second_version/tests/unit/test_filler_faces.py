from __future__ import annotations

import contextlib
import importlib.util
from pathlib import Path
from pathlib import Path as RealPath
import sys
import types
from typing import Any, Iterator, cast
from unittest.mock import MagicMock


GUI_DIR = Path(__file__).resolve().parents[2]
STEP_FILE = GUI_DIR / "steps" / "gallery_creation_step.py"


class _CheckboxStub:
    def __init__(self, checked: bool):
        self._checked = checked

    def isChecked(self) -> bool:
        return self._checked


class _OutputStub:
    def __init__(self):
        self.lines: list[str] = []

    def append(self, text: str) -> None:
        self.lines.append(text)


class _StateStub:
    def __init__(self):
        self._values: dict[str, str] = {}

    def set_user_input(self, key: str, value: str) -> None:
        self._values[key] = value

    def get_user_input(self, key: str, default: str = "") -> str:
        return self._values.get(key, default)


def _load_gallery_creation_module():
    module_name = "_isolated_gallery_creation_step"

    config_module = cast(Any, types.ModuleType("config"))
    messages_module = cast(Any, types.ModuleType("config.messages"))
    setattr(messages_module, "MESSAGES", object())
    setattr(config_module, "messages", messages_module)
    core_module = cast(Any, types.ModuleType("core"))
    setattr(core_module, "WizardStep", type("WizardStep", (), {}))

    exceptions_module = cast(Any, types.ModuleType("core.exceptions"))

    class FlashTVError(Exception):
        pass

    class ErrorType:
        SYSTEM_ERROR = "system"
        PROCESS_ERROR = "process"
        CONFIGURATION_ERROR = "configuration"

    def handle_step_error(func):
        return func

    setattr(exceptions_module, "ErrorType", ErrorType)
    setattr(exceptions_module, "FlashTVError", FlashTVError)
    setattr(exceptions_module, "handle_step_error", handle_step_error)
    models_module = cast(Any, types.ModuleType("models"))
    setattr(models_module, "ProcessStatus", type("ProcessStatus", (), {}))
    setattr(models_module, "StepStatus", type("StepStatus", (), {}))

    state_keys_module = cast(Any, types.ModuleType("models.state_keys"))
    setattr(
        state_keys_module,
        "UserInputKey",
        types.SimpleNamespace(
            PARTICIPANT_ID="participant_id",
            DEVICE_ID="device_id",
            DATA_PATH="data_path",
            USERNAME="username",
        ),
    )
    pyside6_module = cast(Any, types.ModuleType("PySide6"))
    qtwidgets_module = cast(Any, types.ModuleType("PySide6.QtWidgets"))
    setattr(qtwidgets_module, "QProgressBar", type("QProgressBar", (), {}))
    setattr(qtwidgets_module, "QWidget", type("QWidget", (), {}))
    setattr(pyside6_module, "QtWidgets", qtwidgets_module)

    utils_module = cast(Any, types.ModuleType("utils"))
    ui_factory_module = cast(Any, types.ModuleType("utils.ui_factory"))
    setattr(ui_factory_module, "ButtonStyle", types.SimpleNamespace(PRIMARY="primary"))
    setattr(utils_module, "ui_factory", ui_factory_module)

    replacements = {
        "config": config_module,
        "config.messages": messages_module,
        "core": core_module,
        "core.exceptions": exceptions_module,
        "models": models_module,
        "models.state_keys": state_keys_module,
        "PySide6": pyside6_module,
        "PySide6.QtWidgets": qtwidgets_module,
        "utils": utils_module,
        "utils.ui_factory": ui_factory_module,
    }

    @contextlib.contextmanager
    def temporary_modules() -> Iterator[None]:
        original = {name: sys.modules.get(name) for name in replacements}
        try:
            sys.modules.update(replacements)
            yield
        finally:
            for name, module in original.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

    with temporary_modules():
        spec = importlib.util.spec_from_file_location(module_name, STEP_FILE)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(module_name, None)
    return module


def _build_step(
    *,
    gallery_creation_module,
    state: _StateStub,
    tc_checked: bool,
    sib_checked: bool,
    parent_checked: bool,
):
    GalleryCreationStep = gallery_creation_module.GalleryCreationStep
    step = GalleryCreationStep.__new__(GalleryCreationStep)
    step.state = state
    step.logger = MagicMock()
    step.gallery_output = _OutputStub()
    step.tc_checkbox = _CheckboxStub(tc_checked)
    step.sib_checkbox = _CheckboxStub(sib_checked)
    step.parent_checkbox = _CheckboxStub(parent_checked)
    return step


def _configure_state(
    UserInputKey, tmp_path, username: str = "testuser"
) -> tuple[_StateStub, RealPath, str]:
    state = _StateStub()
    participant_id = "P1-3999028"
    device_id = "007"
    data_path = tmp_path / "data"
    faces_folder = data_path / f"{participant_id}{device_id}_faces"
    faces_folder.mkdir(parents=True)

    state.set_user_input(UserInputKey.PARTICIPANT_ID, participant_id)
    state.set_user_input(UserInputKey.DEVICE_ID, device_id)
    state.set_user_input(UserInputKey.DATA_PATH, str(data_path))
    state.set_user_input(UserInputKey.USERNAME, username)
    return state, faces_folder, f"{participant_id}{device_id}"


class TestFillUncheckedFamilyRoles:
    def test_copies_sorted_filler_faces_for_each_unchecked_role(
        self, tmp_path, monkeypatch
    ):
        gallery_creation_module = _load_gallery_creation_module()
        UserInputKey = gallery_creation_module.UserInputKey
        state, faces_folder, combined_id = _configure_state(UserInputKey, tmp_path)
        step = _build_step(
            gallery_creation_module=gallery_creation_module,
            state=state,
            tc_checked=True,
            sib_checked=False,
            parent_checked=True,
        )

        filler_root = tmp_path / "mock_filler_root"
        sibling_dir = filler_root / "face2"
        sibling_dir.mkdir(parents=True)
        for name in [
            "img_10.png",
            "img_02.png",
            "img_01.png",
            "img_04.png",
            "img_03.png",
            "img_05.png",
        ]:
            (sibling_dir / name).write_text(name, encoding="utf-8")

        def fake_path(value: str) -> RealPath:
            if value == "/home/testuser/flash-tv-scripts/filler_faces":
                return filler_root
            return RealPath(value)

        monkeypatch.setattr(gallery_creation_module, "Path", fake_path)

        step._fill_unchecked_family_roles()

        copied = sorted(faces_folder.glob(f"{combined_id}_sib*.png"))
        assert [path.name for path in copied] == [
            f"{combined_id}_sib1.png",
            f"{combined_id}_sib2.png",
            f"{combined_id}_sib3.png",
            f"{combined_id}_sib4.png",
            f"{combined_id}_sib5.png",
        ]
        assert [path.read_text(encoding="utf-8") for path in copied] == [
            "img_01.png",
            "img_02.png",
            "img_03.png",
            "img_04.png",
            "img_05.png",
        ]
        assert "🧩 Added 5 filler face(s) for sibling." in step.gallery_output.lines

    def test_missing_filler_directory_warns_and_keeps_gallery_unchanged(
        self, tmp_path, monkeypatch
    ):
        gallery_creation_module = _load_gallery_creation_module()
        UserInputKey = gallery_creation_module.UserInputKey
        state, faces_folder, combined_id = _configure_state(UserInputKey, tmp_path)
        step = _build_step(
            gallery_creation_module=gallery_creation_module,
            state=state,
            tc_checked=False,
            sib_checked=True,
            parent_checked=True,
        )

        filler_root = tmp_path / "missing_filler_root"

        def fake_path(value: str) -> RealPath:
            if value == "/home/testuser/flash-tv-scripts/filler_faces":
                return filler_root
            return RealPath(value)

        monkeypatch.setattr(gallery_creation_module, "Path", fake_path)

        step._fill_unchecked_family_roles()

        assert list(faces_folder.glob(f"{combined_id}_tc*.png")) == []
        assert step.gallery_output.lines == [
            "⚠️  Missing filler folder for target child; continuing without automatic fill."
        ]
