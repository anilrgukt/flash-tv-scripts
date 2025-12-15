"""Validation patterns and rules for FLASH-TV GUI Setup Wizard.

This module contains regex patterns and validation functions for input validation
throughout the application.
"""

import re
from typing import Pattern, Tuple


class ValidationPatterns:
    """Regex patterns and validation methods for input validation.

    This class centralizes all validation logic to ensure consistency across
    the application and make validation rules easy to maintain and test.
    """

    # Compiled regex patterns
    PARTICIPANT_ID: Pattern[str] = re.compile(r"^(P1|ES)-\d{4}$")
    DEVICE_ID: Pattern[str] = re.compile(r"^-[A-D]$")
    IPV4_ADDRESS: Pattern[str] = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
    MAC_ADDRESS: Pattern[str] = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

    @classmethod
    def validate_participant_id(cls, value: str) -> Tuple[bool, str]:
        """Validate participant ID format.

        Participant IDs must be in the format: P1-XXXX or ES-XXXX where XXXX is a 4-digit number.

        Args:
            value: Input value to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> ValidationPatterns.validate_participant_id("P1-0001")
            (True, "")
            >>> ValidationPatterns.validate_participant_id("P1-123")
            (False, "Invalid format. Expected: P1-XXXX or ES-XXXX (4 digits)")
        """
        if not value:
            return False, "Participant ID is required"

        normalized = value.strip().upper()
        if cls.PARTICIPANT_ID.match(normalized):
            return True, ""

        return False, "Invalid format. Expected: P1-XXXX or ES-XXXX (4 digits)"

    @classmethod
    def validate_device_id(cls, value: str) -> Tuple[bool, str]:
        """Validate device ID format.

        Device IDs must be in the format: -A, -B, -C, or -D

        Args:
            value: Input value to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> ValidationPatterns.validate_device_id("-A")
            (True, "")
            >>> ValidationPatterns.validate_device_id("-E")
            (False, "Invalid format. Expected: -A, -B, -C, or -D")
        """
        if not value:
            return False, "Device ID is required"

        normalized = value.strip().upper()
        if cls.DEVICE_ID.match(normalized):
            return True, ""

        return False, "Invalid format. Expected: -A, -B, -C, or -D"

    @classmethod
    def validate_ipv4(cls, value: str) -> Tuple[bool, str]:
        """Validate IPv4 address format.

        Args:
            value: Input value to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> ValidationPatterns.validate_ipv4("192.168.1.1")
            (True, "")
            >>> ValidationPatterns.validate_ipv4("999.999.999.999")
            (False, "Invalid IPv4 address format")
        """
        if not value:
            return False, "IP address is required"

        if cls.IPV4_ADDRESS.match(value.strip()):
            return True, ""

        return False, "Invalid IPv4 address format"

    @classmethod
    def validate_mac_address(cls, value: str) -> Tuple[bool, str]:
        """Validate MAC address format.

        Args:
            value: Input value to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> ValidationPatterns.validate_mac_address("00:1A:2B:3C:4D:5E")
            (True, "")
            >>> ValidationPatterns.validate_mac_address("invalid")
            (False, "Invalid MAC address format")
        """
        if not value:
            return False, "MAC address is required"

        if cls.MAC_ADDRESS.match(value.strip()):
            return True, ""

        return False, "Invalid MAC address format. Expected: XX:XX:XX:XX:XX:XX"

    @classmethod
    def validate_non_empty(
        cls, value: str, field_name: str = "Field"
    ) -> Tuple[bool, str]:
        """Validate that a field is not empty.

        Args:
            value: Input value to validate
            field_name: Name of the field for error message

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> ValidationPatterns.validate_non_empty("test", "Username")
            (True, "")
            >>> ValidationPatterns.validate_non_empty("", "Username")
            (False, "Username is required")
        """
        if value and value.strip():
            return True, ""

        return False, f"{field_name} is required"

    @classmethod
    def validate_path(cls, value: str) -> Tuple[bool, str]:
        """Validate file/directory path format.

        Args:
            value: Input value to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> ValidationPatterns.validate_path("/home/user/data")
            (True, "")
            >>> ValidationPatterns.validate_path("")
            (False, "Path is required")
        """
        if not value:
            return False, "Path is required"

        if value.strip():
            return True, ""

        return False, "Invalid path format"

    @classmethod
    def validate_url(cls, value: str) -> Tuple[bool, str]:
        """Validate URL format (basic validation).

        Args:
            value: Input value to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> ValidationPatterns.validate_url("http://192.168.1.1:8123")
            (True, "")
            >>> ValidationPatterns.validate_url("not a url")
            (False, "URL must start with http:// or https://")
        """
        if not value:
            return False, "URL is required"

        value = value.strip()
        if value.startswith(("http://", "https://")):
            return True, ""

        return False, "URL must start with http:// or https://"

    @classmethod
    def validate_ssid(cls, value: str) -> Tuple[bool, str]:
        """Validate WiFi SSID.

        Args:
            value: Input value to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> ValidationPatterns.validate_ssid("MyNetwork")
            (True, "")
            >>> ValidationPatterns.validate_ssid("")
            (False, "SSID is required")
        """
        if not value:
            return False, "SSID is required"

        value = value.strip()
        if len(value) == 0:
            return False, "SSID cannot be empty"

        if len(value) > 32:
            return False, "SSID cannot exceed 32 characters"

        return True, ""

    @classmethod
    def validate_port(cls, value: str) -> Tuple[bool, str]:
        """Validate network port number.

        Args:
            value: Input value to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> ValidationPatterns.validate_port("8123")
            (True, "")
            >>> ValidationPatterns.validate_port("99999")
            (False, "Port must be between 1 and 65535")
        """
        if not value:
            return False, "Port is required"

        try:
            port = int(value.strip())
            if 1 <= port <= 65535:
                return True, ""
            return False, "Port must be between 1 and 65535"
        except ValueError:
            return False, "Port must be a number"


# Global singleton instance
VALIDATION = ValidationPatterns()
