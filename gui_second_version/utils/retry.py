"""Retry mechanisms for flaky operations in FLASH-TV GUI Setup Wizard.

This module provides decorators and functions for retrying operations that
may fail intermittently, such as network operations, hardware detection, etc.
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable, Optional, Tuple, Type, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


def retry_on_failure(
    max_attempts: int = 3,
    delay_seconds: float = 2.0,
    backoff_multiplier: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger_instance: Optional[logging.Logger] = None,
):
    """Decorator to retry a function on failure with exponential backoff.

    This decorator catches specified exceptions and retries the function
    up to max_attempts times, with configurable delay and backoff.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        delay_seconds: Initial delay between attempts in seconds (default: 2.0)
        backoff_multiplier: Multiply delay by this after each failure (default: 1.0 = no backoff)
        exceptions: Tuple of exception types to catch (default: all exceptions)
        logger_instance: Optional logger for retry messages

    Returns:
        Decorated function that will retry on failure

    Raises:
        Last exception raised if all attempts fail

    Example:
        >>> @retry_on_failure(max_attempts=3, delay_seconds=1.0, backoff_multiplier=2.0)
        ... def flaky_network_call():
        ...     # This will be retried up to 3 times with delays of 1s, 2s, 4s
        ...     return requests.get("https://api.example.com")
        >>>
        >>> result = flaky_network_call()

    Example with specific exceptions:
        >>> @retry_on_failure(
        ...     max_attempts=5,
        ...     delay_seconds=0.5,
        ...     exceptions=(ConnectionError, TimeoutError)
        ... )
        ... def connect_to_device():
        ...     return device.connect()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            log = logger_instance or logger
            last_error = None
            current_delay = delay_seconds

            for attempt in range(1, max_attempts + 1):
                try:
                    log.debug(f"Attempt {attempt}/{max_attempts}: {func.__name__}")
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_error = e
                    log.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}"
                    )

                    if attempt < max_attempts:
                        log.info(f"Retrying in {current_delay:.1f} seconds...")
                        time.sleep(current_delay)
                        current_delay *= backoff_multiplier
                    else:
                        log.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )

            raise last_error

        return wrapper

    return decorator


def retry_with_callback(
    func: Callable[[], T],
    max_attempts: int = 3,
    delay_seconds: float = 2.0,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    on_final_failure: Optional[Callable[[Exception], None]] = None,
    logger_instance: Optional[logging.Logger] = None,
) -> T:
    """Retry a function with optional callbacks for retry events.

    This function provides more flexibility than the decorator, allowing
    you to specify callbacks for retry attempts and final failure.

    Args:
        func: Function to retry (takes no arguments)
        max_attempts: Maximum number of attempts (default: 3)
        delay_seconds: Delay between attempts in seconds (default: 2.0)
        on_retry: Callback called on each retry: (attempt_number, exception)
        on_final_failure: Callback called if all attempts fail: (exception)
        logger_instance: Optional logger for retry messages

    Returns:
        Result of successful function call

    Raises:
        Exception from last failed attempt

    Example:
        >>> def attempt_connection():
        ...     return connect_to_wifi(ssid, password)
        >>>
        >>> def on_retry_callback(attempt, error):
        ...     print(f"Retry {attempt}: {error}")
        ...     update_status_label(f"Connection attempt {attempt} failed, retrying...")
        >>>
        >>> def on_failure_callback(error):
        ...     show_error_dialog(f"Failed after all attempts: {error}")
        >>>
        >>> result = retry_with_callback(
        ...     attempt_connection,
        ...     max_attempts=3,
        ...     delay_seconds=3.0,
        ...     on_retry=on_retry_callback,
        ...     on_final_failure=on_failure_callback
        ... )
    """
    log = logger_instance or logger
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            log.debug(f"Attempt {attempt}/{max_attempts}")
            return func()

        except Exception as e:
            last_error = e
            log.warning(f"Attempt {attempt}/{max_attempts} failed: {e}")

            if attempt < max_attempts:
                # Call retry callback
                if on_retry:
                    try:
                        on_retry(attempt, e)
                    except Exception as callback_error:
                        log.error(f"Error in on_retry callback: {callback_error}")

                # Wait before next attempt
                time.sleep(delay_seconds)
            else:
                # All attempts failed
                log.error(f"All {max_attempts} attempts failed")

                # Call final failure callback
                if on_final_failure:
                    try:
                        on_final_failure(e)
                    except Exception as callback_error:
                        log.error(
                            f"Error in on_final_failure callback: {callback_error}"
                        )

    raise last_error


def retry_until_success(
    func: Callable[[], T],
    max_duration_seconds: float = 30.0,
    delay_seconds: float = 1.0,
    success_condition: Optional[Callable[[T], bool]] = None,
    logger_instance: Optional[logging.Logger] = None,
) -> Optional[T]:
    """Retry a function until it succeeds or timeout is reached.

    Unlike the other retry functions, this continues retrying for a
    specified duration rather than a fixed number of attempts.

    Args:
        func: Function to retry
        max_duration_seconds: Maximum time to retry in seconds (default: 30)
        delay_seconds: Delay between attempts in seconds (default: 1)
        success_condition: Optional function to check if result is successful
                          If None, any non-exception result is considered success
        logger_instance: Optional logger for retry messages

    Returns:
        Successful result, or None if timeout reached

    Example:
        >>> def check_service_status():
        ...     return get_service_status("flash-tv")
        >>>
        >>> # Retry for up to 60 seconds until service is running
        >>> status = retry_until_success(
        ...     check_service_status,
        ...     max_duration_seconds=60.0,
        ...     delay_seconds=2.0,
        ...     success_condition=lambda s: s == "running"
        ... )
        >>> if status == "running":
        ...     print("Service started successfully!")
    """
    log = logger_instance or logger
    start_time = time.time()
    attempt = 0

    while time.time() - start_time < max_duration_seconds:
        attempt += 1
        try:
            log.debug(f"Attempt {attempt}")
            result = func()

            # Check success condition
            if success_condition:
                if success_condition(result):
                    log.info(f"Success after {attempt} attempts")
                    return result
                else:
                    log.debug(f"Result did not meet success condition")
            else:
                # No condition specified, any result is success
                log.info(f"Success after {attempt} attempts")
                return result

        except Exception as e:
            log.debug(f"Attempt {attempt} raised exception: {e}")

        # Wait before next attempt
        time.sleep(delay_seconds)

    elapsed = time.time() - start_time
    log.warning(f"Timeout after {elapsed:.1f} seconds and {attempt} attempts")
    return None


class RetryConfig:
    """Configuration presets for common retry scenarios.

    This class provides pre-configured retry settings for common
    use cases in the FLASH-TV wizard.
    """

    # Quick operations (e.g., file checks)
    QUICK = {"max_attempts": 2, "delay_seconds": 0.5, "backoff_multiplier": 1.0}

    # Network operations (e.g., WiFi scan, API calls)
    NETWORK = {"max_attempts": 3, "delay_seconds": 2.0, "backoff_multiplier": 1.5}

    # Hardware detection (e.g., camera, USB devices)
    HARDWARE = {"max_attempts": 3, "delay_seconds": 1.0, "backoff_multiplier": 1.0}

    # Long operations (e.g., service startup)
    LONG_RUNNING = {"max_attempts": 5, "delay_seconds": 3.0, "backoff_multiplier": 1.0}

    # Critical operations (e.g., data integrity)
    CRITICAL = {"max_attempts": 5, "delay_seconds": 1.0, "backoff_multiplier": 2.0}

    @classmethod
    def for_network(cls) -> dict:
        """Get retry configuration for network operations."""
        return cls.NETWORK.copy()

    @classmethod
    def for_hardware(cls) -> dict:
        """Get retry configuration for hardware detection."""
        return cls.HARDWARE.copy()

    @classmethod
    def for_critical(cls) -> dict:
        """Get retry configuration for critical operations."""
        return cls.CRITICAL.copy()


# Convenience decorators using presets
def retry_network_operation(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for network operations using NETWORK preset.

    Example:
        >>> @retry_network_operation
        ... def scan_wifi_networks():
        ...     return nmcli_scan()
    """
    config = RetryConfig.for_network()
    return retry_on_failure(**config)(func)


def retry_hardware_detection(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for hardware detection using HARDWARE preset.

    Example:
        >>> @retry_hardware_detection
        ... def detect_cameras():
        ...     return list_cameras()
    """
    config = RetryConfig.for_hardware()
    return retry_on_failure(**config)(func)


def retry_critical_operation(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for critical operations using CRITICAL preset.

    Example:
        >>> @retry_critical_operation
        ... def save_configuration():
        ...     return write_config_file()
    """
    config = RetryConfig.for_critical()
    return retry_on_failure(**config)(func)
