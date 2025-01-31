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


def read_RTC_date(bus: SMBus) -> list[int]:
    return bus.read_i2c_block_data(RTC_ADDRESS, 0, 8)


def hex_RTC_date(bus: SMBus) -> list[str]:
    return [hex(x) for x in read_RTC_date(bus=bus)]


def dec_RTC_date(bus: SMBus) -> list[int]:
    return [int(x.replace("0x", "")) for x in hex_RTC_date(bus=bus)]


def is_within_12_days(*, file_path: Path | str, ext_RTC_date: datetime_class | None = None) -> bool | None:
    if Path(file_path).exists():
        with Path(file_path).open() as file:
            start_date_str = file.read().strip()

        start_date = datetime_class.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")

        if ext_RTC_date:
            delta = abs(ext_RTC_date - start_date)

            if delta.days <= 12:
                return True
            else:
                stderr_print("The date from the external RTC was more than 12 days away from the start date")
                return False
        else:
            stderr_print("No external RTC date provided for comparison to the start date")
            return None
    else:
        stderr_print(f"Start date file '{file_path}' not found")
        return None


def convert_RTC_format_to_timedatectl_format(bus: SMBus) -> str:
    try:
        RTC_date = dec_RTC_date(bus=bus)
        formatted_RTC_date = f"20{RTC_date[6]:02}-{RTC_date[5]:02}-{RTC_date[4]:02} {RTC_date[2]:02}:{RTC_date[1]:02}:{RTC_date[0]:02}"
        datetime_RTC_date = datetime_class.strptime(formatted_RTC_date, "%Y-%m-%d %H:%M:%S")
        if is_within_12_days(file_path=START_DATE_FILE_PATH, ext_RTC_date=datetime_RTC_date):
            return formatted_RTC_date
        else:
            return f"The date from the external RTC, 20{RTC_date[6]:02}-{RTC_date[5]:02}-{RTC_date[4]:02} {RTC_date[2]:02}:{RTC_date[1]:02}:{RTC_date[0]:02}, was incomparable or incorrect"
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


def check_times(bus: SMBus) -> None:
    print(run_command_and_ignore_exceptions(["timedatectl"], "Unable to run timedatectl for system time info"))

    print(
        f"Time from internal RTC rtc0 (PSEQ_RTC, being used) is: {run_command_and_ignore_exceptions(['sudo', 'hwclock', '-r'], 'Unable to obtain time from internal RTC rtc0 (PSEQ_RTC, being used) for validation')}"
    )

    print(f"Time from external RTC (DS3231) is: {convert_RTC_format_to_timedatectl_format(bus=bus)}")

    print(
        f"Time from internal RTC rtc1 (tegra-RTC, not being used) is: {run_command_and_ignore_exceptions(['sudo', 'hwclock', '--rtc', '/dev/rtc1'], 'Unable to obtain time from internal RTC rtc1 (tegra-RTC, not being used)')}"
    )


def set_time_external(bus: SMBus) -> None:
    success_message = "The system time was set from the external RTC"
    command = ["sudo", "timedatectl", "set-time", convert_RTC_format_to_timedatectl_format(bus=bus)]
    run_command_and_raise_exceptions(command, "Failed to set time from external RTC", success_message)


def set_time_internal() -> None:
    success_message = "The system time was set from the internal RTC"
    command = ["sudo", "hwclock", "-s"]
    run_command_and_raise_exceptions(command, "Failed to set time from internal RTC", success_message)


def set_time_both(bus: SMBus) -> None:
    try:
        set_time_external(bus=bus)
    except Exception:
        set_time_internal()


def set_time(bus: SMBus) -> None:
    def set_time_both_partial(bus: SMBus = bus):
        return set_time_both(bus=bus)

    if retry_function(set_time_both_partial, MAX_RETRIES, 1, "Failed to set time from both RTC sources"):
        return
    else:
        reboot_sequence(MAX_RETRIES, [1, 60, 300])


if __name__ == "__main__":
    # Constants
    MAX_RETRIES = 60
    RTC_ADDRESS = 104
    I2C_BUS_NUMBER = 1  # Replace with the actual bus number if different
    BUS = SMBus(I2C_BUS_NUMBER)
    START_DATE_FILE_PATH = Path(sys.argv[1])
    # print(START_DATE_FILE_PATH)

    set_time(bus=BUS)
    check_times(bus=BUS)

    if BUS:
        BUS.close()
