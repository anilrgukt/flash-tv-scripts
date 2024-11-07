import asyncio
from bleak import BleakScanner
from construct import Struct, Byte, Array, ConstructError

# Define the Eddystone format based on the provided data
eddystone_format = Struct("frame_type" / Byte, "tx_power" / Byte, "namespace" / Array(6, Byte), "instance" / Array(6, Byte), "reserved" / Byte)


def process_data(data):
    battery_byte_1 = data[-10]
    battery_byte_2 = data[-9]
    accelerometer_x_byte1 = data[-6]
    accelerometer_x_byte2 = data[-5]
    accelerometer_y_byte1 = data[-4]
    accelerometer_y_byte2 = data[-3]
    accelerometer_z_byte1 = data[-2]
    accelerometer_z_byte2 = data[-1]

    def to_signed_16bit(value):
        if value & 0x8000:  # if MSB is set
            return value - 0x10000
        else:
            return value

    x = to_signed_16bit((accelerometer_x_byte1 << 8) | accelerometer_x_byte2)
    y = to_signed_16bit((accelerometer_y_byte1 << 8) | accelerometer_y_byte2)
    z = to_signed_16bit((accelerometer_z_byte1 << 8) | accelerometer_z_byte2)
    battery = (battery_byte_1 << 8) | battery_byte_2

    return x, y, z, battery


def device_found(device, advertisement_data):
    # Filter devices by MAC address containing "DD"
    if "DD:34" in device.address:
        # Decode Eddystone data if available
        try:
            eddystone_data = advertisement_data.service_data["0000feaa-0000-1000-8000-00805f9b34fb"]
            print(f"Device Address: {device.address}")
            print(f"RSSI          : {advertisement_data.rssi} dBm")
            print(47 * "-")
            # Process additional data
            x, y, z, battery = process_data(eddystone_data)
            print(f"Accelerometer X: {x}")
            print(f"Accelerometer Y: {y}")
            print(f"Accelerometer Z: {z}")
            print(f"Battery Level  : {battery}")
            print(47 * "-")
        except KeyError:
            pass
        except ConstructError:
            pass


async def scan():
    scanner = BleakScanner(detection_callback=device_found)
    try:
        while True:
            await asyncio.sleep(1.0)  # Keep the scanner running indefinitely
    except KeyboardInterrupt:
        await scanner.stop()


async def main():
    while True:
        await scan()
        await asyncio.sleep(0.1)  # Adjust this value to control the polling interval


asyncio.run(main())
