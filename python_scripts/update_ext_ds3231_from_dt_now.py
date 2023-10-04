from datetime import datetime as dt
import smbus2
import traceback
import sys

# Constants
RTC_ADDRESS = 104  # Replace with the actual RTC address if different
I2C_BUS_NUMBER = 1  # Replace with the actual bus number if different

def get_bcd(value):
    # Converts an integer to BCD format
    return (value // 10) << 4 | (value % 10)

def get_current_time_bcd():
    now = dt.now()
    return [
        get_bcd(now.second),
        get_bcd(now.minute),
        get_bcd(now.hour),
        get_bcd(now.weekday() + 1),  # Adjust weekday to RTC format (1-7)
        get_bcd(now.day),
        get_bcd(now.month),
        get_bcd(now.year % 100)  # Get last two digits of the year
    ]

def set_external_rtc_time():
    try:
        bus = smbus2.SMBus(I2C_BUS_NUMBER)
        rtc_data = get_current_time_bcd()
        bus.write_i2c_block_data(RTC_ADDRESS, 0, rtc_data)
        bus.close()
        print(f"Time for external RTC was set to: {rtc_data}")
    except Exception:
        print(traceback.format_exc())
        print("Failed to properly set time for external RTC. Please retry before continuing.")
        sys.exit(1)

if __name__ == "__main__":
    set_external_rtc_time()
