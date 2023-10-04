from datetime import datetime as dt
from smbus2 import SMBus
import subprocess
import traceback
import time
from subprocess import check_output

# Constants
MAX_RETRIES = 60
RTC_ADDRESS = 104
# TIMEDATECTL_SUCCESSFUL = None
# INTERNAL_RTC_READ_SUCCESSFUL = None
# EXTERNAL_RTC_READ_SUCCESSFUL = None


def read_rtc_data(bus):
    return bus.read_i2c_block_data(RTC_ADDRESS, 0, 8)

def hex_rtc_data():
    return [hex(x) for x in read_rtc_data(bus)]

def dec_rtc_data(hex_data):
    return [int(x.replace("0x", "")) for x in hex_data]

def convert_rtc_format_to_timedatectl_format():
    rtc_data = dec_rtc_data(hex_rtc_data())
    return f"20{rtc_data[6]:02}-{rtc_data[5]:02}-{rtc_data[4]:02} {rtc_data[2]:02}:{rtc_data[1]:02}:{rtc_data[0]:02}"

def reboot_5m():
  for attempt in range(1, MAX_RETRIES + 1):
        try:
            subprocess.run(["sudo", "reboot"], check=True)
            return
        except subprocess.CalledProcessError:
            print(traceback.format_exc())
            if attempt < MAX_RETRIES:
                time.sleep(300)
                print(f"5 minute interval reboot attempt failed, retrying (attempt {attempt}/{MAX_RETRIES})")
            else:
                print(f"Maximum amount of 5 minute interval reboot attempts reached, since the system was unable to set the time from either of the RTCs and also unable to reboot, expect incorrect data from this time onwards: {dt.now()}")
                return

def reboot_1m():
  for attempt in range(1, MAX_RETRIES + 1):
        try:
            subprocess.run(["sudo", "reboot"], check=True)
            return
        except subprocess.CalledProcessError:
            print(traceback.format_exc())
            if attempt < MAX_RETRIES:
                time.sleep(60)
                print(f"1 minute interval reboot attempt failed, retrying (attempt {attempt}/{MAX_RETRIES})")
            else:
                print("Maximum amount of 1 minute interval reboot attempts reached, now attempting to reboot every 5 minutes")
                reboot_5m()

def reboot_1s():
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            subprocess.run(["sudo", "reboot"], check=True)
            return
        except subprocess.CalledProcessError:
            print(traceback.format_exc())
            if attempt < MAX_RETRIES:
                time.sleep(1)
                print(f"1 second interval reboot attempt failed, retrying (attempt {attempt}/{MAX_RETRIES})")
            else:
                print("Maximum amount of 1 second interval reboot attempts reached, now attempting to reboot every 1 minute")
                reboot_1m()

def set_time():
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            check_output(["timedatectl", check=True)
            #TIMEDATECTL_SUCCESSFUL = True
        except subprocess.CalledProcessError:
            print(traceback.format_exc())
            print("Warning: unable to run timedatectl for system time info")
            #TIMEDATECTL_SUCCESSFUL = False
        try:
            subprocess.run(["sudo", "hwclock", "-s"], check=True)
            print(f"Time for timedatectl was set to: {dt.now()} from internal RTC")
            try:
                print(f"External RTC time is: {convert_rtc_format_to_timedatectl_format()}")
                bus.close()
                return
            except subprocess.CalledProcessError:
                print(traceback.format_exc())
                print("Warning: Unable to obtain time from external RTC for validation, proceeding anyway since time was successfully set from internal RTC")
            try:
                subprocess.run(["sudo", "hwclock", "-r"], check=True)
                #INTERNAL_RTC_READ_SUCCESSFUL = True
            except subprocess.CalledProcessError:
                print(traceback.format_exc())
                print("Warning: Unable to read from internal RTC after attempting to set time from it")
                #INTERNAL_RTC_READ_SUCCESSFUL = False
            return
        except subprocess.CalledProcessError:
            print(traceback.format_exc())
            print("Failed to set time from internal RTC, attempting to set time from external RTC")
            try:
                subprocess.run(["sudo", "timedatectl", "set-time", convert_rtc_format_to_timedatectl_format()], check=True)
                print(f"Time for timedatectl was set to: {convert_rtc_format_to_timedatectl_format()} from external RTC")
                if bus:
                    bus.close()
                return
            except subprocess.CalledProcessError:
                if attempt < MAX_RETRIES:
                    time.sleep(1)
                    print(f"Failed to set time from external RTC, retrying again starting from internal RTC (attempt {attempt}/{MAX_RETRIES})")
                else:
                    print("Maximum amount of time setting attempts reached, attempting to reboot system")
                    if bus:
                        bus.close()
                    reboot_1s()

if __name__ == "__main__":
    set_time()
