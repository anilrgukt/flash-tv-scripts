"""ProcessInfo model for subprocess tracking."""

from __future__ import annotations

import subprocess
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from models.enums import ProcessStatus


@dataclass
class ProcessInfo:
    """Information about a tracked subprocess."""

    name: str
    process: subprocess.Popen[str]
    command: list[str]
    description: str
    start_time: datetime
    expected_duration: int | None = None
    cleanup_handler: Callable[[], None] | None = None
    max_output_lines: int = 1000
    stdout_lines: deque[str] = field(default_factory=lambda: deque(maxlen=100))
    stderr_lines: deque[str] = field(default_factory=lambda: deque(maxlen=100))
    _stdout_thread: threading.Thread | None = field(
        default=None, init=False, repr=False
    )
    _stderr_thread: threading.Thread | None = field(
        default=None, init=False, repr=False
    )
    _cleanup_done: bool = field(default=False, init=False, repr=False)
    _threads_stopped: threading.Event = field(
        default_factory=threading.Event, init=False, repr=False
    )

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

    def cleanup(self, timeout: float = 5.0) -> None:
        """
        Clean up process and threads properly.

        Args:
            timeout: Maximum time to wait for threads to finish (seconds)
        """
        if self._cleanup_done:
            return

        try:
            # Terminate process if still running
            if self.process and self.process.poll() is None:
                self.terminate()
                try:
                    self.process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass

            # Close pipes to signal threads to stop
            try:
                if self.process.stdin and not self.process.stdin.closed:
                    self.process.stdin.close()
                if self.process.stdout and not self.process.stdout.closed:
                    self.process.stdout.close()
                if self.process.stderr and not self.process.stderr.closed:
                    self.process.stderr.close()
            except Exception as e:
                print(f"Error closing pipes for {self.name}: {e}")

            # Join output capture threads with timeout
            if self._stdout_thread and self._stdout_thread.is_alive():
                self._stdout_thread.join(timeout=timeout)
                if self._stdout_thread.is_alive():
                    print(
                        f"Warning: stdout thread for {self.name} did not finish in time"
                    )

            if self._stderr_thread and self._stderr_thread.is_alive():
                self._stderr_thread.join(timeout=timeout)
                if self._stderr_thread.is_alive():
                    print(
                        f"Warning: stderr thread for {self.name} did not finish in time"
                    )

            # Run custom cleanup handler
            if self.cleanup_handler:
                try:
                    self.cleanup_handler()
                except Exception as e:
                    print(f"Error in cleanup handler for {self.name}: {e}")

        finally:
            self._cleanup_done = True

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

    def start_output_capture(self) -> None:
        """Start threads to capture stdout and stderr."""

        def read_stdout():
            try:
                if self.process.stdout:
                    for line in iter(self.process.stdout.readline, ""):
                        if not line:  # Empty string means pipe closed
                            break
                        self.stdout_lines.append(line.strip())
                        print(f"[{self.name}] STDOUT: {line.strip()}")
            except ValueError:
                # Pipe closed
                pass
            except Exception as e:
                print(f"Error reading stdout for {self.name}: {e}")

        def read_stderr():
            try:
                if self.process.stderr:
                    for line in iter(self.process.stderr.readline, ""):
                        if not line:  # Empty string means pipe closed
                            break
                        self.stderr_lines.append(line.strip())
                        print(f"[{self.name}] STDERR: {line.strip()}")
            except ValueError:
                # Pipe closed
                pass
            except Exception as e:
                print(f"Error reading stderr for {self.name}: {e}")

        if self.process.stdout:
            # NOT daemon - will be joined properly in cleanup()
            self._stdout_thread = threading.Thread(
                target=read_stdout, daemon=False, name=f"{self.name}-stdout"
            )
            self._stdout_thread.start()

        if self.process.stderr:
            # NOT daemon - will be joined properly in cleanup()
            self._stderr_thread = threading.Thread(
                target=read_stderr, daemon=False, name=f"{self.name}-stderr"
            )
            self._stderr_thread.start()

    def get_output(self) -> tuple[list[str], list[str]]:
        """Get captured stdout and stderr lines."""
        return list(self.stdout_lines), list(self.stderr_lines)

    def __del__(self):
        """Ensure cleanup on deletion."""
        if not self._cleanup_done:
            self.cleanup(timeout=1.0)
