from __future__ import annotations

from pathlib import Path


def build_participant_full_id(participant_id: str, device_id: str = "") -> str:
    return f"{participant_id}{device_id}" if device_id else participant_id


def get_participant_data_dir(
    username: str, participant_id: str, device_id: str = ""
) -> Path:
    full_id = build_participant_full_id(participant_id, device_id)
    return Path("/home") / username / "data" / f"{full_id}_data"


def get_gallery_dir(username: str, participant_id: str, device_id: str = "") -> Path:
    full_id = build_participant_full_id(participant_id, device_id)
    return get_participant_data_dir(username, participant_id, device_id) / f"{full_id}_faces"


def get_tv_power_csv_path(
    username: str, participant_id: str, device_id: str = ""
) -> Path:
    full_id = build_participant_full_id(participant_id, device_id)
    return get_participant_data_dir(username, participant_id, device_id) / f"{full_id}_tv_power_5s.csv"
