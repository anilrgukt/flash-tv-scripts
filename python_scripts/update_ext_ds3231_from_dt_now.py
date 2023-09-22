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

print(f"Time for external RTC will be set to: {hex_bcd_dt_now()}")

bus = SMBus(1)
bus.write_i2c_block_data(104, 0, int_bcd_dt_now())
bus.close()
