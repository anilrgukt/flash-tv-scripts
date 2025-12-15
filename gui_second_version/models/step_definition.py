"""StepDefinition model for wizard step configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.enums import StepContentType
from models.state_keys import WizardStep
from models.validation_rule import ValidationRule


@dataclass
class AutomationConfig:
    """Configuration for automated step execution."""

    script_path: str
    script_args: list[str] = field(default_factory=list)
    working_directory: str | None = None
    environment: dict[str, str] = field(default_factory=dict)
    expected_duration: int | None = None
    success_indicators: list[str] = field(default_factory=list)
    failure_indicators: list[str] = field(default_factory=list)


@dataclass
class StepDefinition:
    """Configuration and behavior definition for a wizard step.

    Uses WizardStep enum for type-safe step identification while maintaining
    backwards compatibility with integer step IDs.
    """

    step_id: WizardStep | int
    title: str
    description: str
    content_type: StepContentType
    prerequisites: list[WizardStep | int] = field(default_factory=list)
    validation_rules: list[ValidationRule] = field(default_factory=list)
    automation_config: AutomationConfig | None = None
    ui_config: dict[str, Any] = field(default_factory=dict)

    def has_prerequisites_met(self, completed_steps: set[int]) -> bool:
        """Check if all prerequisites are met.

        Args:
            completed_steps: Set of completed step IDs (as integers)

        Returns:
            True if all prerequisites are completed, False otherwise
        """
        for prereq in self.prerequisites:
            prereq_num = int(prereq) if isinstance(prereq, WizardStep) else prereq
            if prereq_num not in completed_steps:
                return False
        return True

    def validate_inputs(self, inputs: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate inputs against all validation rules.

        Returns:
            Tuple of (all_valid, error_messages)
        """
        errors = []
        for rule in self.validation_rules:
            if rule.field_name in inputs:
                is_valid, error_msg = rule.validate(inputs[rule.field_name])
                if not is_valid:
                    errors.append(error_msg)

        return len(errors) == 0, errors

    def is_automated(self) -> bool:
        """Check if this step has automation configured."""
        return self.automation_config is not None

    def get_script_command(self, user_inputs: dict[str, Any]) -> list[str] | None:
        """Get the script command with user inputs substituted."""
        if not self.automation_config:
            return None

        command = [self.automation_config.script_path]

        for arg in self.automation_config.script_args:
            # Simple template substitution
            formatted_arg = arg
            for key, value in user_inputs.items():
                formatted_arg = formatted_arg.replace(f"{{{key}}}", str(value))
            command.append(formatted_arg)

        return command
