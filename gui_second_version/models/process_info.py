"""ProcessInfo model for subprocess tracking."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from models.enums import ProcessStatus


@dataclass
class ProcessInfo:
    """Information about a tracked subprocess."""

    name: str
    process: subprocess.Popen
    command: list[str]
    description: str
    start_time: datetime
    expected_duration: int | None = None
    cleanup_handler: Callable[[], None] | None = None
    max_output_lines: int = 1000

    def get_status(self) -> ProcessStatus:
        """Get the current status of the process."""
        if self.process.poll() is None:
            return ProcessStatus.RUNNING
        elif self.process.returncode == 0:
            return ProcessStatus.COMPLETED
        elif self.process.returncode < 0:
            return ProcessStatus.TERMINATED
        else:
            return ProcessStatus.FAILED

    def is_running(self) -> bool:
        """Check if the process is still running."""
        return self.process.poll() is None

    def get_runtime(self) -> float:
        """Get the runtime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

    def terminate(self, timeout: int = 5) -> bool:
        """Terminate the process gracefully with timeout."""
        if not self.is_running():
            return True

        try:
            self.process.terminate()
            self.process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            # Force kill if terminate didn't work
            self.process.kill()
            try:
                self.process.wait(timeout=2)
                return True
            except subprocess.TimeoutExpired:
                return False
        except Exception:
            return False

    def kill(self) -> bool:
        """Force kill the process."""
        if not self.is_running():
            return True

        try:
            self.process.kill()
            self.process.wait(timeout=2)
            return True
        except Exception:
            return False

    def cleanup(self) -> None:
        """Run the cleanup handler and close process resources."""
        try:
            # Run custom cleanup handler first
            if self.cleanup_handler:
                self.cleanup_handler()
        except Exception as e:
            print(f"Error in cleanup handler for {self.name}: {e}")

        try:
            # Close process pipes
            if self.process.stdin and not self.process.stdin.closed:
                self.process.stdin.close()
            if self.process.stdout and not self.process.stdout.closed:
                self.process.stdout.close()
            if self.process.stderr and not self.process.stderr.closed:
                self.process.stderr.close()
        except Exception as e:
            print(f"Error closing pipes for {self.name}: {e}")

    def get_output_summary(self) -> dict[str, str]:
        """Get a summary of process output (non-blocking)."""
        summary = {
            "command": " ".join(self.command),
            "status": self.get_status().value,
            "runtime": f"{self.get_runtime():.1f}s",
            "return_code": str(self.process.returncode)
            if self.process.returncode is not None
            else "N/A",
        }

        return summary
