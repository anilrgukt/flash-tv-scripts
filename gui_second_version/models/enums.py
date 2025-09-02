"""Enums for FLASH-TV setup wizard."""

from __future__ import annotations

from enum import StrEnum


class StepStatus(StrEnum):
    PENDING = "pending"
    USER_ACTION_REQUIRED = "user_action_required"
    AUTOMATION_RUNNING = "automation_running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepContentType(StrEnum):
    MANUAL = "manual"
    AUTOMATED = "automated"
    VALIDATION = "validation"
    MIXED = "mixed"


class ValidatorType(StrEnum):
    REGEX = "regex"
    FILE_EXISTS = "file_exists"
    DIRECTORY_EXISTS = "directory_exists"
    SUDO_AVAILABLE = "sudo_available"
    NETWORK_INTERFACE = "network_interface"
    CAMERA_AVAILABLE = "camera_available"
    SERVICE_STATUS = "service_status"
    CUSTOM = "custom"


class ProcessStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"
    NOT_FOUND = "not_found"
