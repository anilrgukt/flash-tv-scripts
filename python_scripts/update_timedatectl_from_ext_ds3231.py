from datetime import datetime as dt
from smbus2 import SMBus
import subprocess
import traceback
import time

# Constants
MAX_RETRIES = 60
RTC_ADDRESS = 104

def read_rtc_data(bus):
    return bus.read_i2c_block_data(RTC_ADDRESS, 0, 8)

def hex_rtc_data():
    return [hex(x) for x in read_rtc_data(bus)]

def dec_rtc_data(hex_data):
    return [int(x.replace("0x", "")) for x in hex_data]

def format_timedatectl_time():
    rtc_data = dec_rtc_data(hex_rtc_data())
    return f"20{rtc_data[6]:02}-{rtc_data[5]:02}-{rtc_data[4]:02} {rtc_data[2]:02}:{rtc_data[1]:02}:{rtc_data[0]:02}"

def reboot_1m():
  for attempt in range(1, MAX_RETRIES + 1):
        try:
            subprocess.run(["sudo", "reboot"], check=True)
        except subprocess.CalledProcessError:
            print(traceback.format_exc())
            if attempt < MAX_RETRIES:
                time.sleep(60)
                print(f"Retrying reboot (attempt {attempt}/{MAX_RETRIES})")
            else:
                print(f"Maximum amount of 1 minute interval reboot attempts reached, since the system was unable to set the time from either of the RTCs and also unable to reboot, expect incorrect data from this time onwards: {dt.now()}")
                break  

def reboot_1s():
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            subprocess.run(["sudo", "reboot"], check=True)
        except subprocess.CalledProcessError:
            print(traceback.format_exc())
            if attempt < MAX_RETRIES:
                time.sleep(1)
                print(f"Reboot attempt failed, retrying... (attempt {attempt}/{MAX_RETRIES})")
            else:
                print("Maximum amount of 1 second interval reboot attempts reached, now attempting to reboot every 1 minute")
                reboot_1m()

def set_time():
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            subprocess.run(["sudo", "hwclock", "-s"], check=True)
            return
        except subprocess.CalledProcessError:
            print(traceback.format_exc())
            print("Setting time from internal RTC failed, attempting to set time from external RTC...")
            try:
                formatted_time = format_timedatectl_time()
                subprocess.run(["sudo", "timedatectl", "set-time", formatted_time], check=True)
                print(f"Time for timedatectl was set to: {formatted_time}")
                bus.close()
                return
            except subprocess.CalledProcessError:
                if attempt < MAX_RETRIES:
                    time.sleep(1)
                    print(f"Setting time from external RTC also failed, retrying starting from internal RTC... (attempt {attempt}/{MAX_RETRIES})")
                else:
                    print("Maximum amount of time setting attempts reached, rebooting system.")
                    bus.close()
                    reboot_1s()

if __name__ == "__main__":
    set_time()
