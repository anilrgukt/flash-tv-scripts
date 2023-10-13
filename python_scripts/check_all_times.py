from datetime import datetime as dt
from smbus2 import SMBus
import subprocess
import traceback
import time

RTC_ADDRESS = 104
I2C_BUS_NUMBER = 1  # Replace with the actual bus number if different

def read_rtc_data(bus):
    return bus.read_i2c_block_data(RTC_ADDRESS, 0, 8)

def hex_rtc_data(bus):
    return [hex(x) for x in read_rtc_data(bus)]

def dec_rtc_data(hex_data):
    return [int(x.replace("0x", "")) for x in hex_data]

def convert_rtc_format_to_timedatectl_format(bus):
    rtc_data = dec_rtc_data(hex_rtc_data(bus))
    return f"20{rtc_data[6]:02}-{rtc_data[5]:02}-{rtc_data[4]:02} {rtc_data[2]:02}:{rtc_data[1]:02}:{rtc_data[0]:02}"

def check_times():

    bus = SMBus(I2C_BUS_NUMBER)
    
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

if __name__ == "__main__":
    check_times()
