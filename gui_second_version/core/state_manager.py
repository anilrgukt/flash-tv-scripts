"""Thread-safe StateManager with improved persistence and recovery."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import QMessageBox

from .config import get_config
from .exceptions import ConfigurationError, handle_step_error
from models import WizardState


class StateManager:
    """Thread-safe state persistence with atomic operations and recovery."""

    def __init__(self, state_file_path: str | None = None):
        self.config = get_config()
        self.state_file_path = Path(state_file_path or self.config.state_file)
        self.backup_file_path = self.state_file_path.with_suffix(".backup")

        # Thread safety
        self._lock = threading.RLock()

        # Ensure directory exists
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

    @handle_step_error
    def save_state(self, state: WizardState) -> None:
        """Save the current state to disk with atomic writes and thread safety."""
        with self._lock:
            try:
                # Create backup of existing state
                if self.state_file_path.exists():
                    self._create_backup()

                # Prepare state data with metadata
                state_data = self._prepare_state_data(state)

                # Atomic write to temporary file then move
                self._atomic_write(state_data)

            except Exception as e:
                # Restore backup if write failed
                self._restore_backup()
                raise ConfigurationError(
                    f"Failed to save state: {e}",
                    recovery_action="Check file permissions and disk space",
                )

    def _create_backup(self) -> None:
        """Create backup of current state file."""
        try:
            # Create timestamped backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_with_timestamp = self.backup_file_path.with_suffix(
                f".{timestamp}.backup"
            )

            if self.state_file_path.exists():
                self.state_file_path.replace(backup_with_timestamp)
                # Keep a rolling backup
                if self.backup_file_path.exists():
                    self.backup_file_path.unlink()
                backup_with_timestamp.replace(self.backup_file_path)

        except OSError as e:
            # Log but don't fail the save operation
            print(f"Warning: Could not create backup: {e}")

    def _prepare_state_data(self, state: WizardState) -> dict[str, Any]:
        """Prepare state data with metadata."""
        state_data = state.to_dict()
        current_time = datetime.now().isoformat()
        
        # Check if this is a new state file (first save) or existing
        created_at = current_time
        if self.state_file_path.exists():
            # If file exists, try to preserve the original created_at timestamp
            try:
                with self.state_file_path.open("r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    created_at = existing_data.get("created_at", current_time)
            except (json.JSONDecodeError, OSError):
                # If we can't read the existing file, use current time
                pass
        
        state_data.update(
            {
                "created_at": created_at,
                "modified_at": current_time,
                "last_saved": current_time,
                "version": "2.0.0",  # State schema version
                "total_steps": self.config.min_window_width
                // 100,  # Avoid hardcoded value
            }
        )
        return state_data

    def _atomic_write(self, state_data: dict[str, Any]) -> None:
        """Perform atomic write of state data."""
        temp_file = self.state_file_path.with_suffix(".tmp")

        try:
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            # Atomic move
            temp_file.replace(self.state_file_path)

        except Exception:
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise

    def _restore_backup(self) -> None:
        """Restore from backup if main state file is corrupted."""
        try:
            if self.backup_file_path.exists() and not self.state_file_path.exists():
                self.backup_file_path.replace(self.state_file_path)
        except OSError:
            pass  # Best effort restore

    @handle_step_error
    def load_state(self) -> WizardState | None:
        """Load state from disk with validation and fallback to backup."""
        with self._lock:
            for file_path in [self.state_file_path, self.backup_file_path]:
                if file_path.exists():
                    try:
                        state = self._load_from_file(file_path)
                        if state:
                            return state
                    except Exception as e:
                        print(f"Error loading state from {file_path}: {e}")
                        continue

            return None

    def _load_from_file(self, file_path: Path) -> WizardState | None:
        """Load state from a specific file with validation."""
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate state data
            if not self._validate_state_data(data):
                raise ValueError("Invalid state data structure")

            # Create state object from data
            state = WizardState.from_dict(data)

            return state

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ConfigurationError(
                f"Corrupted state file {file_path}: {e}",
                recovery_action="Delete the state file to start fresh",
            )

    def _validate_state_data(self, data: dict[str, Any]) -> bool:
        """Validate the structure of loaded state data."""
        required_keys = ["current_step", "completed_steps", "user_inputs"]

        if not isinstance(data, dict):
            return False

        for key in required_keys:
            if key not in data:
                return False

        # Validate data types
        if not isinstance(data["current_step"], int):
            return False
        if not isinstance(data["completed_steps"], list):
            return False
        if not isinstance(data["user_inputs"], dict):
            return False

        return True

    @handle_step_error
    def has_existing_session(self) -> bool:
        """Check if there's an existing session to resume."""
        with self._lock:
            return self.state_file_path.exists() or self.backup_file_path.exists()

    @handle_step_error
    def prompt_for_session_recovery(self, parent=None) -> bool:
        """Prompt user whether to resume existing session."""
        if not self.has_existing_session():
            return False

        reply = QMessageBox.question(
            parent,
            "Resume Session",
            "An incomplete setup session was found. Would you like to resume where you left off?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        return reply == QMessageBox.StandardButton.Yes

    @handle_step_error
    def detect_incomplete_session(self) -> bool:
        """Detect if there's an incomplete session that can be recovered."""
        if not self.state_file_path.exists():
            return False

        try:
            with self._lock:
                state_data = json.loads(self.state_file_path.read_text())

                # Check if session was properly completed
                metadata = state_data.get("metadata", {})
                wizard_data = state_data.get("wizard_state", {})

                # Session is incomplete if:
                # 1. No completion timestamp
                # 2. Not all steps are completed
                # 3. Has active processes
                if not metadata.get("completed_at"):
                    return True

                # Check if there are active processes
                processes = wizard_data.get("processes", {})
                if processes:
                    return True

                # Check step completion status
                step_statuses = wizard_data.get("step_statuses", {})
                if step_statuses and not all(
                    status == "COMPLETED" for status in step_statuses.values()
                ):
                    return True

                return False

        except (json.JSONDecodeError, KeyError, OSError):
            # If we can't read the file, assume it's incomplete
            return True

    @handle_step_error
    def create_recovery_dialog(self, parent=None) -> bool:
        """Create a dialog asking user if they want to recover the session."""
        try:
            state_info = self.get_state_info()
            created_at = state_info.get("created_at", "Unknown")
            modified_at = state_info.get("modified_at", "Unknown")
            
            # Try to get additional information from the saved state file
            session_info = self._get_detailed_session_info()
            current_step = session_info.get("current_step", "Unknown")
            completed_steps = session_info.get("completed_steps_count", "Unknown")

            reply = QMessageBox.question(
                parent,
                "Recover Previous Session",
                f"An incomplete FLASH-TV setup session was found:\n\n"
                f"Created: {created_at}\n"
                f"Last Modified: {modified_at}\n"
                f"Current Step: {current_step}\n"
                f"Steps Completed: {completed_steps}\n\n"
                f"Would you like to continue from where you left off?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.No:
                # User chose to start fresh
                self.clear_state()
                return False

            return True

        except Exception:
            # If anything fails, don't recover
            return False

    @handle_step_error
    def clear_state(self) -> None:
        """Clear all saved state files."""
        with self._lock:
            files_to_remove = [
                self.state_file_path,
                self.backup_file_path,
                self.state_file_path.with_suffix(".tmp"),
            ]

            for file_path in files_to_remove:
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except OSError as e:
                        print(f"Warning: Could not remove {file_path}: {e}")

    def get_state_info(self) -> dict[str, Any]:
        """Get information about the current state file."""
        with self._lock:
            info = {
                "exists": self.state_file_path.exists(),
                "backup_exists": self.backup_file_path.exists(),
                "size": 0,
                "created_at": "Unknown",
                "modified_at": "Unknown",
                "last_modified": None,
            }

            if self.state_file_path.exists():
                stat = self.state_file_path.stat()
                info["size"] = stat.st_size
                info["last_modified"] = datetime.fromtimestamp(
                    stat.st_mtime
                ).isoformat()
                
                # Try to get timestamps from saved JSON data first (more accurate)
                try:
                    with self.state_file_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    created_at_json = data.get("created_at")
                    modified_at_json = data.get("modified_at")
                    
                    if created_at_json:
                        # Try to parse ISO format and reformat for display
                        try:
                            created_dt = datetime.fromisoformat(created_at_json.replace('Z', '+00:00'))
                            info["created_at"] = created_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            # If not in ISO format, assume it's already formatted
                            info["created_at"] = str(created_at_json)
                    
                    if modified_at_json:
                        try:
                            modified_dt = datetime.fromisoformat(modified_at_json.replace('Z', '+00:00'))
                            info["modified_at"] = modified_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            info["modified_at"] = str(modified_at_json)
                            
                except (json.JSONDecodeError, OSError):
                    # Fall back to file system timestamps if JSON reading fails
                    created_dt = datetime.fromtimestamp(stat.st_ctime)
                    modified_dt = datetime.fromtimestamp(stat.st_mtime)
                    
                    info["created_at"] = created_dt.strftime("%Y-%m-%d %H:%M:%S")
                    info["modified_at"] = modified_dt.strftime("%Y-%m-%d %H:%M:%S")
                
                # If we still don't have timestamps, use file system as last resort
                if info["created_at"] == "Unknown" or info["modified_at"] == "Unknown":
                    created_dt = datetime.fromtimestamp(stat.st_ctime)
                    modified_dt = datetime.fromtimestamp(stat.st_mtime)
                    
                    if info["created_at"] == "Unknown":
                        info["created_at"] = created_dt.strftime("%Y-%m-%d %H:%M:%S")
                    if info["modified_at"] == "Unknown":
                        info["modified_at"] = modified_dt.strftime("%Y-%m-%d %H:%M:%S")

            return info

    def _get_detailed_session_info(self) -> dict[str, Any]:
        """Get detailed information from the saved state data."""
        info = {
            "current_step": "Unknown",
            "completed_steps_count": "Unknown",
        }
        
        try:
            if self.state_file_path.exists():
                with self.state_file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                
                info["current_step"] = data.get("current_step", "Unknown")
                completed_steps = data.get("completed_steps", [])
                info["completed_steps_count"] = len(completed_steps) if isinstance(completed_steps, list) else "Unknown"
                
        except (json.JSONDecodeError, OSError):
            # If we can't read the file, return default values
            pass
            
        return info

    def create_state_checkpoint(self, state: WizardState, checkpoint_name: str) -> None:
        """Create a named checkpoint of the current state."""
        with self._lock:
            checkpoint_file = self.state_file_path.with_suffix(
                f".{checkpoint_name}.checkpoint"
            )

            try:
                state_data = self._prepare_state_data(state)
                state_data["checkpoint_name"] = checkpoint_name
                state_data["checkpoint_created"] = datetime.now().isoformat()

                with checkpoint_file.open("w", encoding="utf-8") as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)

            except Exception as e:
                raise ConfigurationError(
                    f"Failed to create checkpoint: {e}",
                    recovery_action="Check file permissions",
                )

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List available state checkpoints."""
        with self._lock:
            checkpoints = []
            pattern = f"{self.state_file_path.stem}.*.checkpoint"

            for checkpoint_file in self.state_file_path.parent.glob(pattern):
                try:
                    with checkpoint_file.open("r", encoding="utf-8") as f:
                        data = json.load(f)

                    checkpoints.append(
                        {
                            "name": data.get("checkpoint_name", "Unknown"),
                            "created": data.get("checkpoint_created", "Unknown"),
                            "file": checkpoint_file,
                            "step": data.get("current_step", "Unknown"),
                        }
                    )
                except Exception:
                    continue  # Skip corrupted checkpoints

            return sorted(checkpoints, key=lambda x: x["created"], reverse=True)
