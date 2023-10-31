from datetime import datetime as dt
from smbus2 import SMBus
import subprocess
import traceback
import time
import sys

# Constants
MAX_RETRIES = 60
RTC_ADDRESS = 104
I2C_BUS_NUMBER = 1  # Replace with the actual bus number if different

def err_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def retry_operation(operation, max_retries, sleep_interval, error_message, *args, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            operation(*args, **kwargs)
            return True
        except Exception as e:
            err_print(f"{error_message} (attempt {attempt}/{max_retries}): {str(e)}")
            if attempt < max_retries:
                time.sleep(sleep_interval)
                continue
            else:
                err_print("Maximum retries reached. Proceeding with the next step.")
                return False

def reboot(interval, max_retries):
    def reboot_operation():
        subprocess.run(["sudo", "reboot"], check=True)

    retry_operation(reboot_operation, max_retries, interval, f"{interval} interval reboot attempt failed")

def reboot_sequence(max_retries, intervals):
    for interval in intervals:
        reboot(interval, max_retries)

def read_rtc_data(bus):
    return bus.read_i2c_block_data(RTC_ADDRESS, 0, 8)

def hex_rtc_data(bus):
    return [hex(x) for x in read_rtc_data(bus)]

def dec_rtc_data(hex_data):
    return [int(x.replace("0x", "")) for x in hex_data]

def convert_rtc_format_to_timedatectl_format(bus):
	try:
		rtc_data = dec_rtc_data(hex_rtc_data(bus))
		if 20{rtc_data[6]:02} - 2023 > 5:
			return f"20{rtc_data[6]:02}-{rtc_data[5]:02}-{rtc_data[4]:02} {rtc_data[2]:02}:{rtc_data[1]:02}:{rtc_data[0]:02}"
		else:
			return "The year from the external RTC, {20{rtc_data[6]:02}}, was too far from the expected year"
	except Exception as e:
		return str(e)
		
def run_command(command, error_message, success_message=None):
    try:
        result = subprocess.check_output(command)
        if success_message:
            print(success_message)
        return result.decode('utf-8').strip()
    except Exception as e:
        err_print(f"{error_message}: {str(e)}")
        raise e

def check_times(bus):
    print(run_command(["timedatectl"], "Unable to run timedatectl for system time info"))

    print(f"Time from internal RTC rtc0 (PSEQ_RTC, being used) is: {run_command(['sudo', 'hwclock', '-r'], 'Unable to obtain time from internal RTC rtc0 (PSEQ_RTC, being used) for validation')}")

    print(f"Time from external RTC (DS3231) is: {convert_rtc_format_to_timedatectl_format(bus)}")

    print(f"Time from internal RTC rtc1 (tegra-RTC, not being used) is: {run_command(['sudo', 'hwclock', '--rtc', '/dev/rtc1'], 'Unable to obtain time from internal RTC rtc1 (tegra-RTC, not being used)')}")

def set_time_external(bus):
    success_message = f"Time for timedatectl was set to: {convert_rtc_format_to_timedatectl_format(bus)} from external RTC"
    command = ["sudo", "timedatectl", "set-time", convert_rtc_format_to_timedatectl_format(bus)]
    run_command(command, "Failed to set time from external RTC", success_message)

def set_time_internal():
    success_message = f"Time for timedatectl was set to: {dt.now()} from internal RTC"
    command = ["sudo", "hwclock", "-s"]
    run_command(command, "Failed to set time from internal RTC", success_message)

def set_time_both(bus):
    try:
    	set_time_external(bus)
    except Exception:
    	set_time_internal()
    return

# Inside set_time function
def set_time(bus):
    if retry_operation(set_time_both, MAX_RETRIES, 1, "Failed to set time from both RTC sources", bus):
        return
    else:
        reboot_sequence(MAX_RETRIES, [1, 60, 300])

if __name__ == "__main__":
    bus = SMBus(I2C_BUS_NUMBER)
    set_time(bus)
    check_times(bus)
    if bus:
    	bus.close()
