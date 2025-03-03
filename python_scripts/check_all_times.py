from __future__ import annotations

import subprocess
import sys
import traceback
from datetime import datetime as datetime_class

from smbus2 import SMBus


def stderr_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def read_RTC_datetime(bus: SMBus) -> list[int]:
    return bus.read_i2c_block_data(RTC_ADDRESS, 0, 8)


def convert_external_RTC_datetime_to_hexadecimal_format(bus: SMBus) -> list[str]:
    return [hex(x) for x in read_RTC_datetime(bus=bus)]


def convert_external_RTC_datetime_to_decimal_format(bus: SMBus) -> list[int]:
    return [int(x.replace("0x", "")) for x in convert_external_RTC_datetime_to_hexadecimal_format(bus=bus)]


def convert_external_RTC_datetime_format_to_timedatectl_format(bus: SMBus) -> str:
    try:
        RTC_datetime_decimal_array = convert_external_RTC_datetime_to_decimal_format(bus=bus)
        RTC_datetime_str = f"20{RTC_datetime_decimal_array[6]:02}-{RTC_datetime_decimal_array[5]:02}-{RTC_datetime_decimal_array[4]:02} {RTC_datetime_decimal_array[2]:02}:{RTC_datetime_decimal_array[1]:02}:{RTC_datetime_decimal_array[0]:02}"
        RTC_datetime = datetime_class.strptime(RTC_datetime_str, "%Y-%m-%d %H:%M:%S")

        if is_external_RTC_datetime_within_12_days_of_start_datetime(RTC_datetime=RTC_datetime):
            return RTC_datetime_str
        else:
            return f"The datetime from the external RTC, 20{RTC_datetime_decimal_array[6]:02}-{RTC_datetime_decimal_array[5]:02}-{RTC_datetime_decimal_array[4]:02} {RTC_datetime_decimal_array[2]:02}:{RTC_datetime_decimal_array[1]:02}:{RTC_datetime_decimal_array[0]:02}, was incomparable or incorrect"
    except Exception as e:
        return str(e)


def run_command(command):
    try:
        return subprocess.check_output(command).strip().decode("utf-8")
    except subprocess.CalledProcessError:
        stderr_print(traceback.format_exc())
        return None


def check_times():
    bus = SMBus(I2C_BUS_NUMBER)

    timedatectl_output = run_command(["timedatectl"])
    if timedatectl_output:
        for line in timedatectl_output.splitlines():
            print(line.strip())
    else:
        stderr_print("Warning: Unable to run timedatectl for system time info")

    internal_rtc0_time = run_command(["sudo", "hwclock", "-r"])
    if internal_rtc0_time:
        print(f"Time from internal RTC rtc0 (PSEQ_RTC, being used) is: {internal_rtc0_time}")
    else:
        stderr_print("Warning: Unable to obtain time from internal RTC rtc0 (PSEQ_RTC, being used) for validation")

    external_rtc_time = convert_rtc_format_to_timedatectl_format(dec_rtc_data(hex_rtc_data(bus)))
    if external_rtc_time:
        print(f"Time from external RTC (DS3231) is: {external_rtc_time}")
    else:
        stderr_print("Warning: Unable to obtain time from external RTC for validation")

    internal_rtc1_time = run_command(["sudo", "hwclock", "--rtc", "/dev/rtc1"])
    if internal_rtc1_time:
        print(f"Time from internal RTC rtc1 (tegra-RTC, not being used) is: {internal_rtc1_time}")
    else:
        stderr_print("Info: Unable to obtain time from internal RTC rtc1 (tegra-RTC, not being used)")

    if bus:
        bus.close()


if __name__ == "__main__":
    RTC_ADDRESS = 104  # Replace with the actual RTC address if different
    I2C_BUS_NUMBER = 1  # Replace with the actual bus number if different

    check_times()
