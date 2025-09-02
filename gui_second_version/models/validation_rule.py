"""ValidationRule model for input validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from models.enums import ValidatorType


@dataclass
class ValidationRule:
    """A validation rule for user inputs or system state."""

    field_name: str
    validator_type: ValidatorType
    validator_config: dict[str, Any]
    error_message: str
    custom_validator: Callable[[Any], bool] | None = None

    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate a value against this rule.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.validator_type == ValidatorType.REGEX:
            import re

            pattern = self.validator_config.get("pattern", "")
            if not re.match(pattern, str(value)):
                return False, self.error_message

        elif self.validator_type == ValidatorType.FILE_EXISTS:
            import os

            if not os.path.isfile(str(value)):
                return False, self.error_message

        elif self.validator_type == ValidatorType.DIRECTORY_EXISTS:
            import os

            if not os.path.isdir(str(value)):
                return False, self.error_message

        elif self.validator_type == ValidatorType.CUSTOM:
            if self.custom_validator and not self.custom_validator(value):
                return False, self.error_message

        return True, ""

    @classmethod
    def participant_id_rule(cls) -> ValidationRule:
        """Create a participant ID validation rule."""
        return cls(
            field_name="participant_id",
            validator_type=ValidatorType.REGEX,
            validator_config={"pattern": r"^(P1|ES)-\d{4}$"},
            error_message="Participant ID must be in format P1-XXXX or ES-XXXX",
        )

    @classmethod
    def directory_exists_rule(cls, field_name: str) -> ValidationRule:
        """Create a directory exists validation rule."""
        return cls(
            field_name=field_name,
            validator_type=ValidatorType.DIRECTORY_EXISTS,
            validator_config={},
            error_message=f"Directory for {field_name} does not exist",
        )

    @classmethod
    def custom_rule(
        cls, field_name: str, validator: Callable[[Any], bool], error_message: str
    ) -> ValidationRule:
        """Create a custom validation rule."""
        return cls(
            field_name=field_name,
            validator_type=ValidatorType.CUSTOM,
            validator_config={},
            error_message=error_message,
            custom_validator=validator,
        )
