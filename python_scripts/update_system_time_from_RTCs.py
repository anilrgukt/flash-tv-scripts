from datetime import datetime as dt
from smbus2 import SMBus
import subprocess
import traceback
import time

# Constants
MAX_RETRIES = 60
RTC_ADDRESS = 104
I2C_BUS_NUMBER = 1  # Replace with the actual bus number if different
# TIMEDATECTL_SUCCESSFUL = None
# INTERNAL_RTC0_READ_SUCCESSFUL = None
# INTERNAL_RTC1_READ_SUCCESSFUL = None
# EXTERNAL_RTC_READ_SUCCESSFUL = None

def read_rtc_data(bus):
    return bus.read_i2c_block_data(RTC_ADDRESS, 0, 8)

def hex_rtc_data(bus):
    return [hex(x) for x in read_rtc_data(bus)]

def dec_rtc_data(hex_data):
    return [int(x.replace("0x", "")) for x in hex_data]

def convert_rtc_format_to_timedatectl_format(bus):
    rtc_data = dec_rtc_data(hex_rtc_data(bus))
    return f"20{rtc_data[6]:02}-{rtc_data[5]:02}-{rtc_data[4]:02} {rtc_data[2]:02}:{rtc_data[1]:02}:{rtc_data[0]:02}"

def reboot_5m():
  for attempt in range(1, MAX_RETRIES + 1):
        try:
            subprocess.run(["sudo", "reboot"], check=True)
            return
        except:
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
        except:
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
        except:
            print(traceback.format_exc())
            if attempt < MAX_RETRIES:
                time.sleep(1)
                print(f"1 second interval reboot attempt failed, retrying (attempt {attempt}/{MAX_RETRIES})")
            else:
                print("Maximum amount of 1 second interval reboot attempts reached, now attempting to reboot every 1 minute")
                reboot_1m()

def check_times(bus):
    
    try:
        timedatectl = subprocess.check_output(["timedatectl"])
        for line in timedatectl.splitlines():
            print(line.strip().decode('utf-8'))
        #TIMEDATECTL_SUCCESSFUL = True
    except:
        print(traceback.format_exc())
        print("Warning: unable to run timedatectl for system time info")
        pass
        #TIMEDATECTL_SUCCESSFUL = False
    try:
        print(f"Time from internal RTC rtc0 (PSEQ_RTC, being used) is: {subprocess.check_output(['sudo', 'hwclock', '-r']).strip().decode('utf-8')}")
        #INTERNAL_RTC0_READ_SUCCESSFUL = True
    except:
        print(traceback.format_exc())
        print("Warning: Unable to obtain time from internal RTC rtc0 (PSEQ_RTC, being used) for validation")
        pass
        #INTERNAL_RTC0_READ_SUCCESSFUL = False
    try:
        print(f"Time from external RTC (DS3231) is: {convert_rtc_format_to_timedatectl_format(bus)}")
        bus.close()
    except:
        print(traceback.format_exc())
        print("Warning: Unable to obtain time from external RTC for validation, proceeding anyway since time was successfully set from internal RTC")
        pass
    try:
        print(f"Time from internal RTC rtc1 (tegra-RTC, not being used) is: {subprocess.check_output(['sudo', 'hwclock', '--rtc', '/dev/rtc1']).decode('utf-8')}")
        #INTERNAL_RTC1_READ_SUCCESSFUL = True
    except:
        print(traceback.format_exc())
        print("Info: Unable to obtain time from internal RTC rtc1 (tegra-RTC, not being used)")
        pass
        #INTERNAL_RTC1_READ_SUCCESSFUL = False
    if bus:
        bus.close()
    return

def set_time():
    
    bus = SMBus(I2C_BUS_NUMBER)
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            subprocess.run(["sudo", "hwclock", "-s"], check=True)
            print(f"Time for timedatectl was set to: {dt.now()} from internal RTC")
            check_times(bus)
            if bus:
            	bus.close()
            return
        except:
            print(traceback.format_exc())
            print("Failed to set time from internal RTC, attempting to set time from external RTC")
            try:
                subprocess.run(["sudo", "timedatectl", "set-time", convert_rtc_format_to_timedatectl_format(bus)], check=True)
                print(f"Time for timedatectl was set to: {convert_rtc_format_to_timedatectl_format(bus)} from external RTC")
                check_times(bus)
                if bus:
                    bus.close()
                return
            except:
                if attempt < MAX_RETRIES:
                    time.sleep(1)
                    print(f"Failed to set time from external RTC, retrying again starting from internal RTC (attempt {attempt}/{MAX_RETRIES})")
                    continue
                else:
                    print("Maximum amount of time setting attempts reached, attempting to reboot system")
                    if bus:
                        bus.close()
                    reboot_1s()

if __name__ == "__main__":
    set_time()
