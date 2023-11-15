from datetime import datetime as dt
from smbus2 import SMBus
import subprocess
import traceback
import time
import sys
import os

# Constants
MAX_RETRIES = 60
RTC_ADDRESS = 104
I2C_BUS_NUMBER = 1  # Replace with the actual bus number if different
START_DATE_FILE_PATH = f"{sys.argv[1]}"
BUS = SMBus(I2C_BUS_NUMBER)

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

def read_RTC_data(bus=BUS):
    return BUS.read_i2c_block_data(RTC_ADDRESS, 0, 8)

def hex_RTC_data():
    return [hex(x) for x in read_RTC_data()]

def dec_RTC_data(hex_data):
    return [int(x.replace("0x", "")) for x in hex_data]
	
def is_within_12_days(file_path=START_DATE_FILE_PATH, ext_RTC_date=None):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            start_date_str = file.read().strip()

        start_date = dt.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")

        if ext_RTC_date:
            delta = abs(ext_RTC_date - start_date)
            if delta.days <= 12:
                print("The date from the external RTC was within 12 days of the start date, proceeding to attempt to set the time")
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

def convert_RTC_format_to_timedatectl_format():
	try:
		RTC_data = dec_RTC_data(hex_RTC_data())
		if is_within_12_days(RTC_data):
			return f"20{RTC_data[6]:02}-{RTC_data[5]:02}-{RTC_data[4]:02} {RTC_data[2]:02}:{RTC_data[1]:02}:{RTC_data[0]:02}"
		else:
			return f"The date from the external RTC, 20{RTC_data[6]:02}-{RTC_data[5]:02}-{RTC_data[4]:02} {RTC_data[2]:02}:{RTC_data[1]:02}:{RTC_data[0]:02}, was too far from the start date"
	except Exception as e:
		return str(e)
		
def run_command(command, error_message, success_message=None, raise_exception=True):
	try:
        	result = subprocess.check_output(command)
        	if success_message:
	            print(success_message)
        	return result.strip().decode('utf-8')
	except Exception as e:
		err_print(f"{error_message}: {str(e)}")
		if raise_exception:
			raise e
		return None

def check_times():
    print(run_command(["timedatectl"], "Unable to run timedatectl for system time info", raise_exception=False))

    print(f"Time from internal RTC rtc0 (PSEQ_RTC, being used) is: {run_command(['sudo', 'hwclock', '-r'], 'Unable to obtain time from internal RTC rtc0 (PSEQ_RTC, being used) for validation', raise_exception=False)}")

    print(f"Time from external RTC (DS3231) is: {convert_RTC_format_to_timedatectl_format()}")

    print(f"Time from internal RTC rtc1 (tegra-RTC, not being used) is: {run_command(['sudo', 'hwclock', '--RTC', '/dev/RTC1'], 'Unable to obtain time from internal RTC rtc1 (tegra-RTC, not being used)', raise_exception=False)}")

def set_time_external():
    success_message = f"The system time was set from the external RTC"
    command = ["sudo", "timedatectl", "set-time", convert_RTC_format_to_timedatectl_format()]
    run_command(command, "Failed to set time from external RTC", success_message, raise_exception=True)

def set_time_internal():
    success_message = f"The system time was set from the internal RTC"
    command = ["sudo", "hwclock", "-s"]
    run_command(command, "Failed to set time from internal RTC", success_message, raise_exception=True)

def set_time_both():
    try:
    	set_time_external()
    except Exception:
    	set_time_internal()
    return

# Inside set_time function
def set_time():
    if retry_operation(set_time_both, MAX_RETRIES, 1, "Failed to set time from both RTC sources"):
        return
    else:
        reboot_sequence(MAX_RETRIES, [1, 60, 300])

if __name__ == "__main__":
    set_time()
    check_times()
    if BUS:
    	BUS.close()
