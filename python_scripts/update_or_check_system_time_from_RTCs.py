from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime as datetime_class
from pathlib import Path
from typing import Callable

from smbus2 import SMBus


def stderr_print(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def retry_function(function: Callable, max_retries: int, sleep_interval: int, error_message: str, *args, **kwargs) -> bool | None:
    for attempt in range(1, max_retries + 1):
        try:
            function(*args, **kwargs)
        except Exception as e:
            stderr_print(f"{error_message} (attempt {attempt}/{max_retries}): {e!s}")
            if attempt < max_retries:
                time.sleep(sleep_interval)
            else:
                stderr_print("Maximum retries reached. Proceeding with the next step.")
                return False
        else:
            return True
    return None


def reboot(interval: int, max_retries: int) -> None:
    def reboot_operation():
        subprocess.run(["sudo", "reboot"], check=True)

    retry_function(reboot_operation, max_retries, interval, f"{interval} interval reboot attempt failed")


def reboot_sequence(max_retries: int, intervals: list[int]) -> None:
    for interval in intervals:
        reboot(interval, max_retries)


def read_RTC_datetime(bus: SMBus) -> list[int]:
    return bus.read_i2c_block_data(RTC_ADDRESS, 0, 8)


def convert_external_RTC_datetime_to_hexadecimal_format(bus: SMBus) -> list[str]:
    return [hex(x) for x in read_RTC_datetime(bus=bus)]


def convert_external_RTC_datetime_to_decimal_format(bus: SMBus) -> list[int]:
    return [int(x.replace("0x", "")) for x in convert_external_RTC_datetime_to_hexadecimal_format(bus=bus)]


def get_start_datetime() -> datetime_class | None:
    if Path(START_DATETIME_FILE_PATH).exists():
        with Path(START_DATETIME_FILE_PATH).open() as file:
            start_datetime_str = file.read().strip()
            return datetime_class.strptime(start_datetime_str, "%Y-%m-%d %H:%M:%S")
    else:
        stderr_print(f"Start datetime file '{START_DATETIME_FILE_PATH}' not found")
        return None


def is_external_RTC_datetime_within_12_days_of_start_datetime(*, external_RTC_datetime: datetime_class | None = None) -> bool | None:
    if external_RTC_datetime:
        start_datetime = get_start_datetime()
        if start_datetime:
            datetime_difference = abs(external_RTC_datetime - start_datetime)
            if datetime_difference.days <= 12:
                return True
            else:
                stderr_print("The datetime from the external RTC was more than 12 days away from the start datetime")
                return False
        else:
            stderr_print("No start datetime provided for comparison to the external RTC datetime")
            return None
    else:
        stderr_print("No external RTC datetime provided for comparison to the start datetime")
        return None


def convert_external_RTC_datetime_format_to_timedatectl_format(bus: SMBus) -> str:
    try:
        external_RTC_datetime_decimal_array = convert_external_RTC_datetime_to_decimal_format(bus=bus)
        external_RTC_datetime_str = f"20{external_RTC_datetime_decimal_array[6]:02}-{external_RTC_datetime_decimal_array[5]:02}-{external_RTC_datetime_decimal_array[4]:02} {external_RTC_datetime_decimal_array[2]:02}:{external_RTC_datetime_decimal_array[1]:02}:{external_RTC_datetime_decimal_array[0]:02}"
        external_RTC_datetime = datetime_class.strptime(external_RTC_datetime_str, "%Y-%m-%d %H:%M:%S")

        if is_external_RTC_datetime_within_12_days_of_start_datetime(external_RTC_datetime=external_RTC_datetime):
            return external_RTC_datetime_str
        else:
            return f"The datetime from the external RTC, 20{external_RTC_datetime_decimal_array[6]:02}-{external_RTC_datetime_decimal_array[5]:02}-{external_RTC_datetime_decimal_array[4]:02} {external_RTC_datetime_decimal_array[2]:02}:{external_RTC_datetime_decimal_array[1]:02}:{external_RTC_datetime_decimal_array[0]:02}, was incomparable or incorrect"
    except Exception as e:
        return str(e)


def run_command_and_ignore_exceptions(command: list[str], error_message: str, success_message: str | None = None) -> str | None:
    try:
        result = subprocess.check_output(command)
        if success_message:
            print(success_message)
        return result.strip().decode("utf-8")
    except Exception as e:
        stderr_print(f"{error_message}: {e!s}")
        return None


def run_command_and_raise_exceptions(command: list[str], error_message: str, success_message: str | None = None) -> str | None:
    try:
        result = subprocess.check_output(command)
        if success_message:
            print(success_message)
        return result.strip().decode("utf-8")
    except Exception as e:
        stderr_print(f"{error_message}: {e!s}")
        raise


def check_all_datetimes() -> None:
    print(run_command_and_ignore_exceptions(["timedatectl"], "Unable to run timedatectl for system time info"))

    print(
        f"Time from internal RTC rtc0 (PSEQ_RTC, being used) is: {run_command_and_ignore_exceptions(['sudo', 'hwclock', '-r'], 'Unable to obtain time from internal RTC rtc0 (PSEQ_RTC, being used) for validation')}"
    )

    bus = SMBus(I2C_BUS_NUMBER)
    print(f"Time from external RTC (DS3231) is: {convert_external_RTC_datetime_format_to_timedatectl_format(bus=bus)}")
    if bus:
        bus.close()

    print(
        f"Time from internal RTC rtc1 (tegra-RTC, not being used) is: {run_command_and_ignore_exceptions(['sudo', 'hwclock', '--rtc', '/dev/rtc1'], 'Unable to obtain time from internal RTC rtc1 (tegra-RTC, not being used)')}"
    )


def set_datetime_from_external_rtc(bus: SMBus) -> None:
    success_message = "The system time was set from the external RTC"
    command = ["sudo", "timedatectl", "set-time", convert_external_RTC_datetime_format_to_timedatectl_format(bus=bus)]
    run_command_and_raise_exceptions(command, "Failed to set time from external RTC", success_message)


def set_datetime_from_internal_rtc() -> None:
    success_message = "The system time was set from the internal RTC"
    command = ["sudo", "hwclock", "-s"]
    run_command_and_raise_exceptions(command, "Failed to set time from internal RTC", success_message)


def set_datetime_on_both_RTCs() -> None:
    bus = None
    try:
        bus = SMBus(I2C_BUS_NUMBER)
        set_datetime_from_external_rtc(bus=bus)
    except Exception:
        set_datetime_from_internal_rtc()
    finally:
        if bus:
            bus.close()


def set_datetime_with_retries() -> None:
    if retry_function(set_datetime_on_both_RTCs, MAX_RETRIES, 1, "Failed to set time from both RTC sources"):
        return
    else:
        reboot_sequence(MAX_RETRIES, [1, 60, 300])


if __name__ == "__main__":
    # Constants
    MAX_RETRIES = 60
    RTC_ADDRESS = 104  # Replace with the actual RTC address if different
    I2C_BUS_NUMBER = 1  # Replace with the actual bus number if different

    UPDATE_OR_CHECK = Path(sys.argv[1])
    START_DATETIME_FILE_PATH = Path(sys.argv[2])

    if UPDATE_OR_CHECK == "update":
        set_datetime_with_retries()
        check_all_datetimes()
    elif UPDATE_OR_CHECK == "check":
        check_all_datetimes()
    else:
        print("Invalid input. Please provide 'update' or 'check' as the first argument")
        sys.exit(1)
