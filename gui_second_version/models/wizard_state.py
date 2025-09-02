"""WizardState model for FLASH-TV setup wizard."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.process_info import ProcessInfo


@dataclass
class WizardState:
    """Central state container for the FLASH-TV setup wizard."""

    current_step: int = 1
    completed_steps: set[int] = field(default_factory=set)
    user_inputs: dict[str, Any] = field(default_factory=dict)
    system_state: dict[str, Any] = field(default_factory=dict)
    process_status: dict[str, ProcessInfo] = field(default_factory=dict)

    def mark_step_completed(self, step_id: int) -> None:
        """Mark a step as completed."""
        self.completed_steps.add(step_id)

    def is_step_completed(self, step_id: int) -> bool:
        """Check if a step is completed."""
        return step_id in self.completed_steps

    def get_user_input(self, key: str, default: Any = None) -> Any:
        """Get user input value with optional default."""
        return self.user_inputs.get(key, default)

    def set_user_input(self, key: str, value: Any) -> None:
        """Set user input value."""
        self.user_inputs[key] = value

    def get_system_state(self, key: str, default: Any = None) -> Any:
        """Get system state value with optional default."""
        return self.system_state.get(key, default)

    def set_system_state(self, key: str, value: Any) -> None:
        """Set system state value."""
        self.system_state[key] = value

    def add_process(self, process_name: str, process_info: ProcessInfo) -> None:
        """Add a tracked process."""
        self.process_status[process_name] = process_info

    def remove_process(self, process_name: str) -> ProcessInfo | None:
        """Remove a tracked process and return it if it existed."""
        return self.process_status.pop(process_name, None)

    def get_process(self, process_name: str) -> ProcessInfo | None:
        """Get a tracked process."""
        return self.process_status.get(process_name)

    def get_all_processes(self) -> dict[str, ProcessInfo]:
        """Get all tracked processes."""
        return self.process_status.copy()

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "current_step": self.current_step,
            "completed_steps": list(self.completed_steps),
            "user_inputs": self.user_inputs,
            "system_state": self.system_state,
            # Note: process_status is not serialized as processes don't survive across sessions
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WizardState:
        """Create state from dictionary."""
        state = cls()
        state.current_step = data.get("current_step", 1)
        state.completed_steps = set(data.get("completed_steps", []))
        state.user_inputs = data.get("user_inputs", {})
        state.system_state = data.get("system_state", {})
        # process_status starts empty on deserialization
        return state
