from datetime import datetime as dt
from smbus2 import SMBus
import subprocess
import traceback
import time
import sys

RTC_ADDRESS = 104
I2C_BUS_NUMBER = 1  # Replace with the actual bus number if different

def stderr_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def read_rtc_data(bus):
    return bus.read_i2c_block_data(RTC_ADDRESS, 0, 8)

def hex_rtc_data(bus):
    return [hex(x) for x in read_rtc_data(bus)]

def dec_rtc_data(hex_data):
    return [int(x.replace("0x", "")) for x in hex_data]

def convert_rtc_format_to_timedatectl_format(rtc_data):
    return f"20{rtc_data[6]:02}-{rtc_data[5]:02}-{rtc_data[4]:02} {rtc_data[2]:02}:{rtc_data[1]:02}:{rtc_data[0]:02}"

def run_command(command):
    try:
        return subprocess.check_output(command).strip().decode('utf-8')
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
    check_times()
