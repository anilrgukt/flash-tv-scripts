from __future__ import annotations

import sys
import traceback
from datetime import datetime as datetime_class
from datetime import timezone, tzinfo
from pathlib import Path

from smbus2 import SMBus


def get_local_timezone() -> tzinfo | None:
    return datetime_class.now(timezone.utc).astimezone().tzinfo


def stderr_print(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def convert_int_to_BCD_format(value: int) -> int:
    return (value // 10) << 4 | (value % 10)


def get_current_datetime_in_BCD_format() -> list[int]:
    datetime_now = datetime_class.now(get_local_timezone())

    return [
        convert_int_to_BCD_format(datetime_now.second),
        convert_int_to_BCD_format(datetime_now.minute),
        convert_int_to_BCD_format(datetime_now.hour),
        convert_int_to_BCD_format(datetime_now.weekday() + 1),  # Adjust weekday to RTC format (1-7)
        convert_int_to_BCD_format(datetime_now.day),
        convert_int_to_BCD_format(datetime_now.month),
        convert_int_to_BCD_format(datetime_now.year % 100),  # Get last two digits of the year
        convert_int_to_BCD_format(0),  # Set extra alarm bit to 0 to remove the default value of 255
    ]


def set_external_RTC_time(rtc_address: int, i2c_bus_number: int) -> None:
    try:
        bus = SMBus(i2c_bus_number)
        bus.write_i2c_block_data(rtc_address, 0, get_current_datetime_in_BCD_format())
        bus.close()
        print(f"Time for external RTC was set to: {get_current_datetime_in_BCD_format()}")
    except Exception:
        stderr_print(traceback.format_exc())
        stderr_print("Failed to properly set time for external RTC. Please retry before continuing.")
        # Exit with non-zero error code to end upper shell
        sys.exit(1)


def save_current_date_to_file(file_path: Path | str) -> None:
    current_date = datetime_class.now(get_local_timezone()).strftime("%Y-%m-%d %H:%M:%S")

    with Path(file_path).open(mode="w") as file:
        file.write(current_date)


if __name__ == "__main__":
    # Constants
    RTC_ADDRESS = 104  # Replace with the actual RTC address if different
    I2C_BUS_NUMBER = 1  # Replace with the actual bus number if different

    # Path taken as first command line input argument
    start_date_file_path = Path(sys.argv[1])

    # Set the time on the external RTC
    set_external_RTC_time(rtc_address=RTC_ADDRESS, i2c_bus_number=I2C_BUS_NUMBER)

    # Save the current date to the start date file
    save_current_date_to_file(file_path=start_date_file_path)
