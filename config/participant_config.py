from __future__ import annotations

import importlib
from pathlib import Path
import re
from typing import Any


from config.install_defaults_loader import load_install_defaults_module


install_defaults_module = load_install_defaults_module()
HOME_ASSISTANT_IMAGE = str(getattr(install_defaults_module, "HOME_ASSISTANT_IMAGE"))
DEFAULT_SMART_PLUG_SWITCH = str(
    getattr(install_defaults_module, "DEFAULT_SMART_PLUG_SWITCH_ENTITY_ID")
)
DEFAULT_SMART_PLUG_POWER_SENSOR = str(
    getattr(install_defaults_module, "DEFAULT_SMART_PLUG_POWER_SENSOR_ENTITY_ID")
)

pydantic_module = importlib.import_module("pydantic")
BaseModel = getattr(pydantic_module, "BaseModel")
ValidationError = getattr(pydantic_module, "ValidationError")
field_validator = getattr(pydantic_module, "field_validator", None)
supports_pydantic_v2 = field_validator is not None

if supports_pydantic_v2:
    ConfigDict = getattr(pydantic_module, "ConfigDict")
    validator_decorator = field_validator
else:
    field_validator = getattr(pydantic_module, "validator")
    ConfigDict = None
    validator_decorator = field_validator


PARTICIPANT_ID_PATTERN = re.compile(r"^(P1-\d{4}|ES-\d{4})$")
DEVICE_ID_PATTERN = re.compile(r"^\d{3}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")

DEFAULT_BLUETOOTH_MAC = "Not Needed for this Visit"


class ParticipantConfigError(ValueError):
    pass


class ParticipantConfig(BaseModel):
    participant_id: str
    device_id: str
    username: str
    smart_plug_switch_entity_id: str = DEFAULT_SMART_PLUG_SWITCH
    smart_plug_power_sensor_entity_id: str = DEFAULT_SMART_PLUG_POWER_SENSOR
    bluetooth_beacon_mac_address: str = DEFAULT_BLUETOOTH_MAC

    if supports_pydantic_v2 and ConfigDict is not None:
        model_config = ConfigDict(frozen=True)
    else:

        class Config:
            allow_mutation = False

    if supports_pydantic_v2 and field_validator is not None:

        @validator_decorator(
            "participant_id",
            "device_id",
            "username",
            "smart_plug_switch_entity_id",
            "smart_plug_power_sensor_entity_id",
            "bluetooth_beacon_mac_address",
            mode="before",
        )
        @classmethod
        def _normalize_strings(cls, value: Any) -> str:
            return str(value).strip()

    elif field_validator is not None:

        @validator_decorator(
            "participant_id",
            "device_id",
            "username",
            "smart_plug_switch_entity_id",
            "smart_plug_power_sensor_entity_id",
            "bluetooth_beacon_mac_address",
            pre=True,
        )
        def _normalize_strings(cls, value: Any) -> str:
            return str(value).strip()

    @validator_decorator("participant_id")
    @classmethod
    def _validate_participant_id(cls, value: str) -> str:
        if not PARTICIPANT_ID_PATTERN.fullmatch(value):
            raise ValueError("Participant ID must look like P1-1234 or ES-1234.")
        return value

    @validator_decorator("device_id")
    @classmethod
    def _validate_device_id(cls, value: str) -> str:
        if not DEVICE_ID_PATTERN.fullmatch(value):
            raise ValueError(
                "Device ID must be the 3 digits at the end of the username."
            )
        return value

    @validator_decorator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("Username contains unsupported characters.")
        return value

    @validator_decorator("smart_plug_switch_entity_id")
    @classmethod
    def _validate_smart_plug_switch_entity_id(cls, value: str) -> str:
        if not value:
            raise ValueError("Smart plug switch ID is missing.")
        return value

    @validator_decorator("smart_plug_power_sensor_entity_id")
    @classmethod
    def _validate_smart_plug_power_sensor_entity_id(cls, value: str) -> str:
        if not value:
            raise ValueError("Smart plug power sensor ID is missing.")
        return value

    @property
    def full_id(self) -> str:
        return f"{self.participant_id}{self.device_id}"

    @property
    def home_dir(self) -> Path:
        return Path("/home") / self.username

    @property
    def repo_root(self) -> Path:
        return self.home_dir / "flash-tv-scripts"

    @property
    def data_root(self) -> Path:
        return self.home_dir / "data"

    @property
    def data_dir(self) -> Path:
        return self.data_root / f"{self.full_id}_data"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def homeassistant_root(self) -> Path:
        return self.home_dir / "homeassistant-compose"

    @property
    def homeassistant_config_dir(self) -> Path:
        return self.homeassistant_root / "config"

    @property
    def homeassistant_archive_dir(self) -> Path:
        return self.homeassistant_root / "archived_participants"

    @property
    def tv_power_csv_path(self) -> Path:
        return self.data_dir / f"{self.full_id}_tv_power_5s.csv"

    @property
    def git_config_copy_path(self) -> Path:
        return self.data_dir / "git_config.txt"

    @property
    def backup_readiness_path(self) -> Path:
        return self.data_dir / "participant_change_backup_readiness.txt"

    def template_values(self) -> dict[str, str]:
        return {
            "PARTICIPANT_ID": self.participant_id,
            "DEVICE_ID": self.device_id,
            "USERNAME": self.username,
            "FULL_ID": self.full_id,
            "HOME_DIR": str(self.home_dir),
            "DATA_DIR": str(self.data_dir),
            "LOGS_DIR": str(self.logs_dir),
            "HOMEASSISTANT_DIR": str(self.homeassistant_root),
            "HOMEASSISTANT_CONFIG_DIR": str(self.homeassistant_config_dir),
            "HOME_ASSISTANT_IMAGE": HOME_ASSISTANT_IMAGE,
            "SMART_PLUG_SWITCH_ENTITY_ID": self.smart_plug_switch_entity_id,
            "SMART_PLUG_POWER_SENSOR_ENTITY_ID": self.smart_plug_power_sensor_entity_id,
            "TV_POWER_CSV_PATH": str(self.tv_power_csv_path),
            "TV_POWER_CSV_CONTAINER_PATH": f"/{self.full_id}_data/{self.full_id}_tv_power_5s.csv",
            "DATA_DIR_CONTAINER_PATH": f"/{self.full_id}_data",
            "BLUETOOTH_BEACON_MAC_ADDRESS": self.bluetooth_beacon_mac_address,
        }


def build_participant_config(
    *,
    participant_id: str,
    device_id: str,
    username: str,
    smart_plug_switch_entity_id: str = DEFAULT_SMART_PLUG_SWITCH,
    smart_plug_power_sensor_entity_id: str = DEFAULT_SMART_PLUG_POWER_SENSOR,
    bluetooth_beacon_mac_address: str = DEFAULT_BLUETOOTH_MAC,
) -> ParticipantConfig:
    try:
        config = ParticipantConfig(
            participant_id=participant_id,
            device_id=device_id,
            username=username,
            smart_plug_switch_entity_id=smart_plug_switch_entity_id,
            smart_plug_power_sensor_entity_id=smart_plug_power_sensor_entity_id,
            bluetooth_beacon_mac_address=bluetooth_beacon_mac_address,
        )

        if not config.username.endswith(config.device_id):
            raise ParticipantConfigError(
                "Device ID must match the last 3 digits of the username."
            )

        return config
    except ValidationError as exc:
        messages = [error["msg"] for error in exc.errors()]
        raise ParticipantConfigError(" ".join(messages)) from exc
