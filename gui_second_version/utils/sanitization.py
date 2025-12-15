"""Input sanitization and validation utilities for FLASH-TV GUI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from core.exceptions import ValidationError


class InputSanitizer:
    """Sanitize and validate user inputs to prevent security issues and ensure data integrity."""

    # Participant ID pattern: P1-XXXX or ES-XXXX
    PARTICIPANT_ID_PATTERN = re.compile(r"^(P1|ES)-\d{4}$")

    # Device ID pattern: -A, -B, -C, -D
    DEVICE_ID_PATTERN = re.compile(r"^-[A-D]$")

    # Family ID pattern: 3-digit number (legacy support)
    FAMILY_ID_PATTERN = re.compile(r"^\d{3}$")

    @staticmethod
    def sanitize_participant_id(participant_id: str) -> str:
        """
        Sanitize and validate participant ID.

        Args:
            participant_id: Raw participant ID from user input

        Returns:
            Validated participant ID in uppercase

        Raises:
            ValidationError: If participant ID is invalid or contains unsafe characters
        """
        if not participant_id:
            raise ValidationError(
                "Participant ID cannot be empty", field="participant_id"
            )

        participant_id = participant_id.strip().upper()

        if "/" in participant_id or "\\" in participant_id:
            raise ValidationError(
                "Participant ID cannot contain path separators",
                field="participant_id",
                recovery_action="Remove any forward or back slashes from the ID",
            )

        dangerous_chars = [
            "..",
            "~",
            "$",
            "`",
            ";",
            "&",
            "|",
            "<",
            ">",
            '"',
            "'",
            "\x00",
        ]
        for char in dangerous_chars:
            if char in participant_id:
                raise ValidationError(
                    f"Participant ID contains invalid character: {char}",
                    field="participant_id",
                    recovery_action="Remove special characters from the ID",
                )

        if not InputSanitizer.PARTICIPANT_ID_PATTERN.match(participant_id):
            raise ValidationError(
                "Invalid participant ID format. Expected: P1-XXXX or ES-XXXX (where X is a digit)",
                field="participant_id",
                recovery_action="Use format P1-0001 through P1-9999 or ES-0001 through ES-9999",
            )

        return participant_id

    @staticmethod
    def sanitize_device_id(device_id: str) -> str:
        """
        Sanitize and validate device ID.

        Args:
            device_id: Raw device ID from user input

        Returns:
            Validated device ID in uppercase

        Raises:
            ValidationError: If device ID is invalid
        """
        if not device_id:
            raise ValidationError("Device ID cannot be empty", field="device_id")

        device_id = device_id.strip().upper()

        if not InputSanitizer.DEVICE_ID_PATTERN.match(device_id):
            raise ValidationError(
                "Invalid device ID format. Expected: -A, -B, -C, or -D",
                field="device_id",
                recovery_action="Select a valid device ID from the dropdown",
            )

        return device_id

    @staticmethod
    def sanitize_family_id(family_id: str) -> str:
        """
        Sanitize and validate family ID (legacy 3-digit format).

        Args:
            family_id: Raw family ID from user input

        Returns:
            Validated family ID (3 digits)

        Raises:
            ValidationError: If family ID is invalid
        """
        if not family_id:
            raise ValidationError("Family ID cannot be empty", field="family_id")

        family_id = family_id.strip()

        if not InputSanitizer.FAMILY_ID_PATTERN.match(family_id):
            raise ValidationError(
                "Invalid family ID format. Expected: 3-digit number (e.g., 001, 123)",
                field="family_id",
                recovery_action="Enter a 3-digit number",
            )

        return family_id

    @staticmethod
    def sanitize_file_path(
        path: str,
        base_dir: Optional[str] = None,
        must_exist: bool = False,
        must_be_dir: bool = False,
    ) -> Path:
        """
        Sanitize file path and optionally ensure it's within base directory.

        Args:
            path: Raw file path from user input
            base_dir: Base directory to constrain path to (prevents traversal attacks)
            must_exist: Whether path must exist
            must_be_dir: Whether path must be a directory

        Returns:
            Validated Path object (resolved to absolute path)

        Raises:
            ValidationError: If path is invalid, outside base_dir, or doesn't meet requirements
        """
        if not path:
            raise ValidationError("Path cannot be empty", field="path")

        # Remove null bytes
        if "\x00" in path:
            raise ValidationError("Path contains null bytes", field="path")

        try:
            path_obj = Path(path).resolve()
        except (ValueError, OSError) as e:
            raise ValidationError(
                f"Invalid path: {e}",
                field="path",
                recovery_action="Check that the path is valid and accessible",
            )

        if base_dir:
            try:
                base = Path(base_dir).resolve()
                path_obj.relative_to(base)
            except ValueError:
                raise ValidationError(
                    f"Path '{path}' is outside allowed directory '{base_dir}'",
                    field="path",
                    recovery_action="Select a path within the allowed directory",
                )

        if must_exist and not path_obj.exists():
            raise ValidationError(
                f"Path does not exist: {path}",
                field="path",
                recovery_action="Check that the path exists and is accessible",
            )

        if must_be_dir and path_obj.exists() and not path_obj.is_dir():
            raise ValidationError(
                f"Path is not a directory: {path}",
                field="path",
                recovery_action="Select a directory, not a file",
            )

        return path_obj

    @staticmethod
    def sanitize_text(
        text: str,
        max_length: int = 50000,
        allow_newlines: bool = True,
        field_name: str = "text",
    ) -> str:
        """
        Sanitize text input by removing control characters and enforcing length limits.

        Args:
            text: Raw text from user input
            max_length: Maximum allowed length
            allow_newlines: Whether to allow newline characters
            field_name: Name of field for error messages

        Returns:
            Sanitized text

        Raises:
            ValidationError: If text is too long
        """
        text = text.replace("\x00", "")

        if not allow_newlines:
            text = "".join(c for c in text if c.isprintable() or c in " \t")
        else:
            text = "".join(c for c in text if c.isprintable() or c in " \t\n\r")

        if len(text) > max_length:
            raise ValidationError(
                f"Text too long (max {max_length} characters, got {len(text)})",
                field=field_name,
                recovery_action=f"Reduce text to {max_length} characters or fewer",
            )

        return text

    @staticmethod
    def sanitize_ssid(ssid: str) -> str:
        """
        Sanitize WiFi SSID.

        Args:
            ssid: Raw SSID from user input

        Returns:
            Validated SSID

        Raises:
            ValidationError: If SSID is invalid
        """
        if not ssid:
            raise ValidationError("SSID cannot be empty", field="ssid")

        ssid = ssid.strip()

        if len(ssid) > 32:
            raise ValidationError(
                "SSID too long (max 32 characters)",
                field="ssid",
                recovery_action="WiFi SSIDs must be 32 characters or fewer",
            )

        if "\x00" in ssid:
            raise ValidationError(
                "SSID contains invalid characters (null bytes)", field="ssid"
            )

        return ssid

    @staticmethod
    def sanitize_password(password: str, min_length: int = 1) -> str:
        """
        Sanitize password input.

        Note: We don't enforce complexity requirements as this is for
        system passwords (WiFi, sudo) which may have varying requirements.

        Args:
            password: Raw password from user input
            min_length: Minimum password length

        Returns:
            Password (unchanged but validated)

        Raises:
            ValidationError: If password doesn't meet requirements
        """
        if len(password) < min_length:
            raise ValidationError(
                f"Password too short (minimum {min_length} characters)",
                field="password",
                recovery_action=f"Enter a password with at least {min_length} characters",
            )

        if "\x00" in password:
            raise ValidationError(
                "Password contains invalid characters", field="password"
            )

        return password

    @staticmethod
    def sanitize_camera_index(index: str | int) -> int:
        """
        Sanitize camera index.

        Args:
            index: Raw camera index from user input (string or int)

        Returns:
            Validated camera index (integer)

        Raises:
            ValidationError: If index is invalid
        """
        try:
            if isinstance(index, str):
                idx = int(index.strip())
            else:
                idx = int(index)
        except (ValueError, AttributeError):
            raise ValidationError(
                f"Invalid camera index: {index}",
                field="camera_index",
                recovery_action="Enter a valid number for camera index",
            )

        if idx < 0 or idx > 99:
            raise ValidationError(
                f"Camera index out of range: {idx} (must be 0-99)",
                field="camera_index",
                recovery_action="Select a camera index between 0 and 99",
            )

        return idx

    @staticmethod
    def sanitize_port_number(port: str | int) -> int:
        """
        Sanitize network port number.

        Args:
            port: Raw port number from user input

        Returns:
            Validated port number

        Raises:
            ValidationError: If port is invalid
        """
        try:
            if isinstance(port, str):
                port_num = int(port.strip())
            else:
                port_num = int(port)
        except (ValueError, AttributeError):
            raise ValidationError(
                f"Invalid port number: {port}",
                field="port",
                recovery_action="Enter a valid number for port",
            )

        if port_num < 1 or port_num > 65535:
            raise ValidationError(
                f"Port number out of range: {port_num} (must be 1-65535)",
                field="port",
                recovery_action="Enter a port number between 1 and 65535",
            )

        return port_num

    @staticmethod
    def sanitize_ip_address(ip: str) -> str:
        """
        Sanitize and validate IP address.

        Args:
            ip: Raw IP address from user input

        Returns:
            Validated IP address

        Raises:
            ValidationError: If IP address is invalid
        """
        ip = ip.strip()

        parts = ip.split(".")
        if len(parts) != 4:
            raise ValidationError(
                f"Invalid IP address format: {ip}",
                field="ip_address",
                recovery_action="Use format: XXX.XXX.XXX.XXX",
            )

        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    raise ValueError()
        except ValueError:
            raise ValidationError(
                f"Invalid IP address: {ip}",
                field="ip_address",
                recovery_action="Each octet must be 0-255",
            )

        return ip

    @staticmethod
    def sanitize_filename(filename: str, allow_path: bool = False) -> str:
        """
        Sanitize filename to prevent directory traversal and invalid characters.

        Args:
            filename: Raw filename from user input
            allow_path: Whether to allow path separators (/)

        Returns:
            Validated filename

        Raises:
            ValidationError: If filename contains invalid characters
        """
        if not filename:
            raise ValidationError("Filename cannot be empty", field="filename")

        filename = filename.strip()

        if "\x00" in filename:
            raise ValidationError(
                "Filename contains invalid characters", field="filename"
            )

        if not allow_path:
            if "/" in filename or "\\" in filename:
                raise ValidationError(
                    "Filename cannot contain path separators",
                    field="filename",
                    recovery_action="Use only the filename without directory path",
                )

            if filename in [".", ".."]:
                raise ValidationError("Invalid filename", field="filename")

        invalid_chars = ["<", ">", ":", '"', "|", "?", "*"]
        for char in invalid_chars:
            if char in filename:
                raise ValidationError(
                    f"Filename contains invalid character: {char}",
                    field="filename",
                    recovery_action="Remove special characters from filename",
                )

        return filename
