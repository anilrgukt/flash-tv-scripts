"""Efficient log file tailing using file.seek().

This module provides utilities for efficiently reading only new content
from log files without re-reading the entire file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class LogFileState:
    """State tracking for a single log file."""

    path: str
    last_position: int = 0
    last_size: int = 0
    last_inode: int = 0  # For detecting file rotation
    buffered_lines: list[str] = field(default_factory=list)


class LogTailer:
    """Efficient log file tailer that tracks file positions.

    This class tracks the read position in log files and only reads
    new content on subsequent calls, significantly reducing I/O for
    large log files.

    Usage:
        tailer = LogTailer()

        # First call reads entire file
        lines = tailer.get_new_lines("/path/to/log.txt")

        # Subsequent calls only read new content appended since last read
        new_lines = tailer.get_new_lines("/path/to/log.txt")
    """

    def __init__(self, max_buffer_lines: int = 1000):
        """Initialize the log tailer.

        Args:
            max_buffer_lines: Maximum number of lines to keep in buffer
        """
        self._file_states: dict[str, LogFileState] = {}
        self.max_buffer_lines = max_buffer_lines

    def get_new_lines(
        self,
        filepath: str,
        include_all: bool = False,
    ) -> list[str]:
        """Get new lines from a log file since last read.

        Args:
            filepath: Path to the log file
            include_all: If True, return all buffered lines plus new ones.
                        If False, return only new lines since last read.

        Returns:
            List of new lines (stripped, non-empty)
        """
        if not os.path.exists(filepath):
            return []

        try:
            state = self._get_or_create_state(filepath)

            # Check if file was rotated (inode changed or size decreased)
            stat = os.stat(filepath)
            current_inode = stat.st_ino if hasattr(stat, "st_ino") else 0
            current_size = stat.st_size

            if self._file_was_rotated(state, current_inode, current_size):
                # File was rotated - reset and read from beginning
                state.last_position = 0
                state.last_inode = current_inode
                state.buffered_lines.clear()

            # Read only new content using seek
            new_lines = self._read_from_position(filepath, state.last_position)

            # Update state
            state.last_size = current_size
            state.last_inode = current_inode

            # Add new lines to buffer
            if new_lines:
                state.buffered_lines.extend(new_lines)
                # Trim buffer to max size
                if len(state.buffered_lines) > self.max_buffer_lines:
                    state.buffered_lines = state.buffered_lines[
                        -self.max_buffer_lines :
                    ]

            if include_all:
                return state.buffered_lines.copy()
            return new_lines

        except Exception:
            return []

    def get_last_line(self, filepath: str) -> str:
        """Get the last non-empty line from a log file.

        Uses the buffer if available, otherwise reads efficiently from end.

        Args:
            filepath: Path to the log file

        Returns:
            Last non-empty, non-comment line, or empty string
        """
        state = self._file_states.get(filepath)

        # If we have buffered lines, use the last one
        if state and state.buffered_lines:
            for line in reversed(state.buffered_lines):
                if line and not line.startswith("#"):
                    return line
            return ""

        # Otherwise read efficiently from end of file
        return self._read_last_line_efficient(filepath)

    def get_all_lines(self, filepath: str) -> list[str]:
        """Get all lines from a file, using buffer if available.

        This updates the tailer state as a side effect.

        Args:
            filepath: Path to the log file

        Returns:
            List of all non-empty, non-comment lines
        """
        # Force read of any new content
        self.get_new_lines(filepath, include_all=False)

        # Return buffered lines
        state = self._file_states.get(filepath)
        if state:
            return [
                line
                for line in state.buffered_lines
                if line and not line.startswith("#")
            ]

        # Fallback to full read if no state
        return self._read_entire_file(filepath)

    def reset(self, filepath: str | None = None) -> None:
        """Reset tailer state for a file or all files.

        Args:
            filepath: If provided, reset only this file. Otherwise reset all.
        """
        if filepath:
            if filepath in self._file_states:
                del self._file_states[filepath]
        else:
            self._file_states.clear()

    def _get_or_create_state(self, filepath: str) -> LogFileState:
        """Get or create file state for tracking."""
        if filepath not in self._file_states:
            # Initial state - will read entire file on first call
            self._file_states[filepath] = LogFileState(path=filepath)
        return self._file_states[filepath]

    def _file_was_rotated(
        self,
        state: LogFileState,
        current_inode: int,
        current_size: int,
    ) -> bool:
        """Check if file was rotated or truncated."""
        # Inode changed (different file)
        if state.last_inode != 0 and current_inode != 0:
            if state.last_inode != current_inode:
                return True

        # File size decreased (truncated or rotated)
        if current_size < state.last_position:
            return True

        return False

    def _read_from_position(self, filepath: str, start_pos: int) -> list[str]:
        """Read new lines from a specific position in the file.

        Args:
            filepath: Path to the log file
            start_pos: Byte position to start reading from

        Returns:
            List of new lines (stripped, non-empty)
        """
        new_lines = []

        try:
            with open(filepath, "r", errors="ignore") as f:
                # Seek to last known position
                f.seek(start_pos)

                # Read remaining content
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        new_lines.append(stripped)

                # Update state with new position
                state = self._file_states.get(filepath)
                if state:
                    state.last_position = f.tell()

        except Exception:
            pass

        return new_lines

    def _read_last_line_efficient(self, filepath: str, buffer_size: int = 8192) -> str:
        """Read the last line of a file efficiently using seek.

        Reads from the end of the file in chunks to find the last line,
        without reading the entire file.

        Args:
            filepath: Path to the log file
            buffer_size: Size of chunks to read from end

        Returns:
            Last non-empty, non-comment line
        """
        try:
            with open(filepath, "rb") as f:
                # Seek to end to get file size
                f.seek(0, 2)  # SEEK_END
                file_size = f.tell()

                if file_size == 0:
                    return ""

                # Read from end in chunks
                read_size = min(buffer_size, file_size)
                f.seek(file_size - read_size)
                chunk = f.read(read_size).decode("utf-8", errors="ignore")

                # Find last non-empty line
                lines = chunk.splitlines()
                for line in reversed(lines):
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        return stripped

        except Exception:
            pass

        return ""

    def _read_entire_file(self, filepath: str) -> list[str]:
        """Read entire file when no buffer available."""
        lines = []
        try:
            with open(filepath, "r", errors="ignore") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        lines.append(stripped)
        except Exception:
            pass
        return lines


class StderrLogTailer(LogTailer):
    """Specialized log tailer for stderr logs with error highlighting support.

    Tracks which lines contain actual errors vs known warnings.
    """

    _is_known_safe: Callable[[str], bool]

    def __init__(
        self,
        is_error_func: Callable[[str], bool] | None = None,
        max_buffer_lines: int = 500,
    ):
        """Initialize the stderr log tailer.

        Args:
            is_error_func: Function to determine if a line is an actual error.
                          Returns True if line is a known safe warning.
            max_buffer_lines: Maximum lines to buffer
        """
        super().__init__(max_buffer_lines)
        self._is_known_safe = is_error_func or (lambda x: False)

    def get_new_content_with_errors(self, filepath: str) -> tuple[list[str], list[str]]:
        """Get new lines categorized as errors or safe warnings.

        Args:
            filepath: Path to stderr log

        Returns:
            Tuple of (all_new_lines, error_lines)
        """
        new_lines = self.get_new_lines(filepath)

        error_lines = []
        for line in new_lines:
            if not self._is_known_safe(line):
                error_lines.append(line)

        return new_lines, error_lines

    def get_all_content_with_errors(self, filepath: str) -> tuple[list[str], list[str]]:
        all_lines = self.get_all_lines(filepath)

        error_lines = []
        for line in all_lines:
            if not self._is_known_safe(line):
                error_lines.append(line)

        return all_lines, error_lines
