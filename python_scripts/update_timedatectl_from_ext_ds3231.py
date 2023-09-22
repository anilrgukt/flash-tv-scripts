from datetime import datetime as dt
from smbus2 import SMBus
import subprocess

def int_to_bcd(input_integer):
    # Step 2: Initialize variables
    result = 0
    multiplier = 1

    # Step 3: Loop through each decimal digit in reverse order
    while input_integer > 0:
        digit = input_integer % 10  # Get the last digit
        result += digit * multiplier  # Add the digit to the result
        multiplier *= 16  # Multiply the multiplier by 16 (shift left by 4 bits)
        input_integer //= 10  # Remove the last digit

    # The 'result' variable now contains the BCD representation
    return (result)  # Convert to hexadecimal for BCD representation

trimmed_dt_now = lambda: list(dt.now().timetuple()[:-2])
modulus_dt_now = lambda: [trimmed_dt_now()[5]%60, trimmed_dt_now()[4]%60, trimmed_dt_now()[3]%24, trimmed_dt_now()[6], trimmed_dt_now()[2], trimmed_dt_now()[1], trimmed_dt_now()[0]%100, 0]
int_bcd_dt_now = lambda: [int_to_bcd(x) for x in modulus_dt_now()]
hex_bcd_dt_now = lambda: [hex(x) for x in int_bcd_dt_now()]

#print(f"dt.now() BCD Int: {int_bcd_dt_now()}")
#print(f"dt.now() BCD Hex: {hex_bcd_dt_now()}")

bus = SMBus(1)
#bus.write_i2c_block_data(104, 0, int_bcd_dt_now())
rtc_data = lambda: bus.read_i2c_block_data(104, 0, 8)
hex_rtc_data = lambda: [hex(x) for x in rtc_data()]
int_rtc_data = lambda: [int(x) for x in rtc_data()]
#print(f"RTC Hex: {hex_rtc_data()}")
#print(f"RTC Int: {int_rtc_data()}")

dec_rtc_data = lambda: [int(x.replace("0x", "")) for x in hex_rtc_data()]
#print(f"RTC Dec: {dec_rtc_data()}")
#dt_for_hwclock = f"{dec_rtc_data()[5]:02}/{dec_rtc_data()[4]:02}/20{dec_rtc_data()[6]:02} {dec_rtc_data()[2]:02}:{dec_rtc_data()[1]:02}:{dec_rtc_data()[0]:02}"
dt_for_timedatectl = f"20{dec_rtc_data()[6]:02}-{dec_rtc_data()[5]:02}-{dec_rtc_data()[4]:02} {dec_rtc_data()[2]:02}:{dec_rtc_data()[1]:02}:{dec_rtc_data()[0]:02}"
#print(print(f"Time for hwclock will be set to: {dt_for_hwclock}"))
print(f"Time for timedatectl will be set to: {dt_for_timedatectl}")
#command = ["sudo", "hwclock", "--set", "--date", dt_for_hwclock]
command1 = ["sudo", "timedatectl", "set-ntp", "0"]
command2 = ["sudo", "timedatectl", "set-time", dt_for_timedatectl]
subprocess.run(command1, check=True)
subprocess.run(command2, check=True)
bus.close()
