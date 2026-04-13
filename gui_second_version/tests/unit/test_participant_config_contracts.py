from __future__ import annotations

import contextlib
import importlib.util
from pathlib import Path
import sys
import types
from typing import Iterator

import pytest


@contextlib.contextmanager
def _temporary_module_entry(module_name: str) -> Iterator[None]:
    original = sys.modules.get(module_name)
    try:
        yield
    finally:
        if original is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original


@contextlib.contextmanager
def _temporary_sys_path(path: Path) -> Iterator[None]:
    path_str = str(path)
    original = list(sys.path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    try:
        yield
    finally:
        sys.path[:] = original


def _load_config_support_modules(repo_root: Path) -> dict[str, object]:
    config_dir = repo_root / "config"
    config_package = types.ModuleType("config")
    config_package.__path__ = [str(config_dir)]

    loader_name = "config.install_defaults_loader"
    loader_spec = importlib.util.spec_from_file_location(
        loader_name,
        config_dir / "install_defaults_loader.py",
    )
    assert loader_spec is not None
    assert loader_spec.loader is not None
    loader_module = importlib.util.module_from_spec(loader_spec)
    sys.modules[loader_name] = loader_module
    try:
        loader_spec.loader.exec_module(loader_module)
    finally:
        sys.modules.pop(loader_name, None)

    return {
        "config": config_package,
        loader_name: loader_module,
    }


def _load_participant_config_module():
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "config" / "participant_config.py"
    spec = importlib.util.spec_from_file_location(
        "participant_config_test_module", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    support_modules = _load_config_support_modules(repo_root)
    with (
        _temporary_sys_path(repo_root),
        _temporary_module_entry(spec.name),
        _temporary_module_entry("config"),
        _temporary_module_entry("config.install_defaults_loader"),
        _temporary_module_entry("flash_tv_install_defaults"),
    ):
        sys.modules.update(support_modules)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return module


def test_build_participant_config_normalizes_whitespace_and_path_contracts():
    module = _load_participant_config_module()

    config = module.build_participant_config(
        participant_id="  P1-1234 ",
        device_id=" 007 ",
        username=" flashsys007 ",
        smart_plug_switch_entity_id=" switch.office_tv ",
        smart_plug_power_sensor_entity_id=" sensor.office_tv_power ",
        bluetooth_beacon_mac_address=" AA:BB:CC:DD:EE:FF ",
    )

    assert config.participant_id == "P1-1234"
    assert config.device_id == "007"
    assert config.username == "flashsys007"
    assert config.full_id == "P1-1234007"
    assert config.data_dir == Path("/home/flashsys007/data/P1-1234007_data")
    assert config.tv_power_csv_path == config.data_dir / "P1-1234007_tv_power_5s.csv"

    values = config.template_values()
    assert values["FULL_ID"] == config.full_id
    assert values["DATA_DIR"] == str(config.data_dir)
    assert values["TV_POWER_CSV_PATH"] == str(config.tv_power_csv_path)
    assert (
        values["TV_POWER_CSV_CONTAINER_PATH"]
        == "/P1-1234007_data/P1-1234007_tv_power_5s.csv"
    )
    assert values["DATA_DIR_CONTAINER_PATH"] == "/P1-1234007_data"


def test_template_values_keep_csv_contracts_across_multiple_valid_inputs():
    module = _load_participant_config_module()

    participant_ids = ["P1-0001", "ES-9999"]
    valid_identity_pairs = [
        ("000", "flashsys000"),
        ("007", "flashsys007"),
        ("123", "flash.sys-123"),
    ]

    for participant_id in participant_ids:
        for device_id, username in valid_identity_pairs:
            config = module.build_participant_config(
                participant_id=participant_id,
                device_id=device_id,
                username=username,
            )
            values = config.template_values()
            expected_full_id = f"{participant_id}{device_id}"
            expected_data_dir = (
                Path("/home") / username / "data" / f"{expected_full_id}_data"
            )
            expected_csv_name = f"{expected_full_id}_tv_power_5s.csv"

            assert config.full_id == expected_full_id
            assert config.data_dir == expected_data_dir
            assert config.tv_power_csv_path.parent == config.data_dir
            assert config.tv_power_csv_path.name == expected_csv_name
            assert values["FULL_ID"] == expected_full_id
            assert values["DATA_DIR"] == str(expected_data_dir)
            assert values["TV_POWER_CSV_PATH"] == str(
                expected_data_dir / expected_csv_name
            )
            assert values["DATA_DIR_CONTAINER_PATH"] == f"/{expected_full_id}_data"
            assert values["TV_POWER_CSV_CONTAINER_PATH"] == (
                f"/{expected_full_id}_data/{expected_csv_name}"
            )


def test_build_participant_config_rejects_username_device_id_mismatch():
    module = _load_participant_config_module()

    with pytest.raises(module.ParticipantConfigError) as exc_info:
        module.build_participant_config(
            participant_id="P1-1234",
            device_id="007",
            username="flashsys999",
        )

    assert "Device ID must match the last 3 digits of the username." in str(
        exc_info.value
    )


@pytest.mark.parametrize(
    ("field_name", "overrides", "message_fragment"),
    [
        (
            "participant_id",
            {"participant_id": "P2-1234"},
            "Participant ID must look like P1-1234 or ES-1234.",
        ),
        (
            "participant_id",
            {"participant_id": "ES-12A4"},
            "Participant ID must look like P1-1234 or ES-1234.",
        ),
        (
            "device_id",
            {"device_id": "12"},
            "Device ID must be the 3 digits at the end of the username.",
        ),
        (
            "device_id",
            {"device_id": "A07"},
            "Device ID must be the 3 digits at the end of the username.",
        ),
        (
            "username",
            {"username": "flash sys007"},
            "Username contains unsupported characters.",
        ),
        (
            "username",
            {"username": "flash/sys007"},
            "Username contains unsupported characters.",
        ),
        (
            "smart_plug_switch_entity_id",
            {"smart_plug_switch_entity_id": "   "},
            "Smart plug switch ID is missing.",
        ),
        (
            "smart_plug_power_sensor_entity_id",
            {"smart_plug_power_sensor_entity_id": "   "},
            "Smart plug power sensor ID is missing.",
        ),
    ],
)
def test_build_participant_config_rejects_invalid_contract_values(
    field_name, overrides, message_fragment
):
    module = _load_participant_config_module()
    kwargs = {
        "participant_id": "P1-1234",
        "device_id": "007",
        "username": "flashsys007",
    }
    kwargs.update(overrides)

    with pytest.raises(module.ParticipantConfigError) as exc_info:
        module.build_participant_config(**kwargs)

    assert field_name in overrides
    assert message_fragment in str(exc_info.value)
