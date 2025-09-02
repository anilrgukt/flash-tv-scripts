"""StateManager for persistence and recovery."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import QMessageBox

from models import WizardState


class StateManager:
    """Handles state persistence, recovery, and session management."""

    def __init__(self, state_file_path: str = "flash_setup_state.json"):
        self.state_file_path = Path(state_file_path)
        self.backup_file_path = Path(f"{state_file_path}.backup")

    def save_state(self, state: WizardState) -> None:
        """Save the current state to disk with atomic writes."""
        try:
            # Create backup of existing state
            if self.state_file_path.exists():
                self.state_file_path.replace(self.backup_file_path)

            # Prepare state data
            state_data = state.to_dict()
            state_data["last_saved"] = datetime.now().isoformat()

            # Atomic write to temporary file then move
            temp_file = Path(f"{self.state_file_path}.tmp")
            with temp_file.open("w") as f:
                json.dump(state_data, f, indent=2)

            temp_file.replace(self.state_file_path)

        except Exception as e:
            print(f"Error saving state: {e}")
            # Restore backup if write failed
            if self.backup_file_path.exists() and not self.state_file_path.exists():
                self.backup_file_path.replace(self.state_file_path)

    def load_state(self) -> WizardState | None:
        """Load state from disk, with fallback to backup."""
        for file_path in [self.state_file_path, self.backup_file_path]:
            if file_path.exists():
                try:
                    with file_path.open("r") as f:
                        data = json.load(f)
                    return WizardState.from_dict(data)
                except Exception as e:
                    print(f"Error loading state from {file_path}: {e}")
                    continue

        return None

    def detect_incomplete_session(self) -> bool:
        """Check if there's an incomplete session that can be recovered."""
        return self.state_file_path.exists()

    def get_session_info(self) -> dict[str, Any] | None:
        """Get information about the saved session."""
        if not self.state_file_path.exists():
            return None

        try:
            with self.state_file_path.open("r") as f:
                data = json.load(f)

            return {
                "current_step": data.get("current_step", 1),
                "completed_steps": len(data.get("completed_steps", [])),
                "total_steps": 12,  # FLASH-TV has 12 steps
                "last_saved": data.get("last_saved", "Unknown"),
                "participant_id": data.get("user_inputs", {}).get(
                    "participant_id", "Not set"
                ),
            }
        except Exception:
            return None

    def create_recovery_dialog(self, parent=None) -> bool:
        """Show recovery dialog and return user's choice."""
        session_info = self.get_session_info()
        if not session_info:
            return False

        msg = QMessageBox(parent)
        msg.setWindowTitle("Session Recovery")
        msg.setIcon(QMessageBox.Icon.Question)

        recovery_text = (
            f"Found incomplete setup session:\n\n"
            f"• Participant ID: {session_info['participant_id']}\n"
            f"• Current step: {session_info['current_step']}\n"
            f"• Completed steps: {session_info['completed_steps']}/{session_info['total_steps']}\n"
            f"• Last saved: {session_info['last_saved']}\n\n"
            f"Would you like to resume this session?"
        )

        msg.setText(recovery_text)
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)

        result = msg.exec()
        return result == QMessageBox.StandardButton.Yes

    def clear_state(self) -> None:
        """Clear saved state files."""
        for file_path in [self.state_file_path, self.backup_file_path]:
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"Error clearing state file {file_path}: {e}")

    def export_state(self, export_path: str, state: WizardState) -> bool:
        """Export current state to a specific file."""
        try:
            export_file = Path(export_path)
            state_data = state.to_dict()
            state_data["exported_at"] = datetime.now().isoformat()

            with export_file.open("w") as f:
                json.dump(state_data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error exporting state: {e}")
            return False

    def import_state(self, import_path: str) -> WizardState | None:
        """Import state from a specific file."""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                return None

            with import_file.open("r") as f:
                data = json.load(f)

            return WizardState.from_dict(data)
        except Exception as e:
            print(f"Error importing state: {e}")
            return None
