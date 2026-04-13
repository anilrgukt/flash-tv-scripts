from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


FLASHSYS_USERNAME_PATTERN = re.compile(r"^(flashsys)(\d+)$")


@dataclass(frozen=True)
class IdentityDetectionResult:
    username: str | None = None
    device_id: str | None = None
    reason: str = ""
    fallback_reason: str = ""
    sources: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return bool(self.username and self.device_id)


def _parse_flashsys_username(username: str | None) -> tuple[str | None, str | None]:
    if not username:
        return None, None

    match = FLASHSYS_USERNAME_PATTERN.match(username.strip())
    if not match:
        return None, None

    return username.strip(), match.group(2)


def derive_device_id_from_username(username: str | None) -> str | None:
    _, device_id = _parse_flashsys_username(username)
    return device_id


def detect_flash_tv_identity(
    env: dict[str, str] | None = None,
    home_root: Path = Path("/home"),
    current_home: Path | None = None,
) -> IdentityDetectionResult:
    env_map = env or os.environ
    reasons: list[str] = []
    candidate_usernames: list[tuple[str, str]] = []

    for env_key in ("SUDO_USER", "USER", "LOGNAME"):
        env_value = (env_map.get(env_key) or "").strip()
        username, device_id = _parse_flashsys_username(env_value)
        if username and device_id:
            home_dir = home_root / username
            if home_dir.is_dir():
                candidate_usernames.append((username, f"${env_key}"))
            else:
                reasons.append(
                    f"{env_key} suggests '{username}', but {home_dir} does not exist."
                )
        elif env_value and env_value.lower() != "root":
            reasons.append(
                f"{env_key} is '{env_value}', which does not match the expected flashsys### account format."
            )

    resolved_home = current_home or Path.home()
    home_username = resolved_home.name.strip()
    username, device_id = _parse_flashsys_username(home_username)
    if username and device_id:
        home_dir = home_root / username
        if home_dir.is_dir():
            candidate_usernames.append((username, "home directory"))
        else:
            reasons.append(
                f"Home directory name suggests '{username}', but {home_dir} does not exist."
            )
    elif home_username and home_username.lower() != "root":
        reasons.append(
            f"Home directory owner '{home_username}' does not match the expected flashsys### account format."
        )

    flashsys_dirs = sorted(
        path.name
        for path in home_root.glob("flashsys*")
        if path.is_dir() and _parse_flashsys_username(path.name)[0]
    )

    unique_candidates: list[tuple[str, str]] = []
    seen: set[str] = set()
    for username, source in candidate_usernames:
        if username not in seen:
            unique_candidates.append((username, source))
            seen.add(username)

    if unique_candidates:
        detected_username, first_source = unique_candidates[0]
        derived_device_id = derive_device_id_from_username(detected_username)
        all_sources = [
            source
            for username, source in unique_candidates
            if username == detected_username
        ]
        source_text = ", ".join(all_sources) if all_sources else first_source
        return IdentityDetectionResult(
            username=detected_username,
            device_id=derived_device_id,
            reason=(
                f"Detected username '{detected_username}' from {source_text}; "
                f"device ID '{derived_device_id}' was derived from the username suffix."
            ),
            sources=all_sources,
        )

    if len(flashsys_dirs) == 1:
        detected_username = flashsys_dirs[0]
        derived_device_id = derive_device_id_from_username(detected_username)
        return IdentityDetectionResult(
            username=detected_username,
            device_id=derived_device_id,
            reason=(
                f"Detected the only FLASH-TV home directory '{detected_username}' under {home_root}; "
                f"device ID '{derived_device_id}' was derived from the username suffix."
            ),
            sources=["/home scan"],
        )

    if len(flashsys_dirs) > 1:
        reasons.append(
            "Multiple FLASH-TV home directories were found under /home and none matched the current environment uniquely: "
            + ", ".join(flashsys_dirs)
            + "."
        )
    else:
        reasons.append("No flashsys### home directory was found under /home.")

    fallback_reason = " ".join(reason for reason in reasons if reason).strip()
    if not fallback_reason:
        fallback_reason = "The GUI could not determine the FLASH-TV username automatically from the current environment."

    return IdentityDetectionResult(
        reason="Automatic username and device ID detection did not succeed.",
        fallback_reason=fallback_reason,
    )
