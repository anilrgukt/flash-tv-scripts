from datetime import datetime as dt
from smbus2 import SMBus
import subprocess

bus = SMBus(1)

rtc_data = lambda: bus.read_i2c_block_data(104, 0, 8)
hex_rtc_data = lambda: [hex(x) for x in rtc_data()]
#int_rtc_data = lambda: [int(x) for x in rtc_data()]
#print(f"RTC Hex: {hex_rtc_data()}")
#print(f"RTC Int: {int_rtc_data()}")

dec_rtc_data = lambda: [int(x.replace("0x", "")) for x in hex_rtc_data()]
#print(f"RTC Dec: {dec_rtc_data()}")

#dt_for_hwclock = f"{dec_rtc_data()[5]:02}/{dec_rtc_data()[4]:02}/20{dec_rtc_data()[6]:02} {dec_rtc_data()[2]:02}:{dec_rtc_data()[1]:02}:{dec_rtc_data()[0]:02}"
dt_for_timedatectl = f"20{dec_rtc_data()[6]:02}-{dec_rtc_data()[5]:02}-{dec_rtc_data()[4]:02} {dec_rtc_data()[2]:02}:{dec_rtc_data()[1]:02}:{dec_rtc_data()[0]:02}"

#command = ["sudo", "hwclock", "--set", "--date", dt_for_hwclock]
command1 = ["sudo", "timedatectl", "set-ntp", "0"]
command2 = ["sudo", "timedatectl", "set-time", dt_for_timedatectl]
subprocess.run(command1, check=True)
subprocess.run(command2, check=True)
bus.close()

#print(print(f"Time for hwclock was be set to: {dt_for_hwclock}"))
print(f"Time for timedatectl was set to: {dt_for_timedatectl}")
