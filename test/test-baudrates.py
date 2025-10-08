#!/usr/bin/env python3
"""Test multiple baudrates to find the correct one"""
import serial
import time

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATES = [9600, 19200, 38400, 57600, 115200]

print("🔍 Testing different baudrates for PN532\n")

for baud in BAUDRATES:
    print(f"Testing {baud} baud...", end=" ")

    try:
        ser = serial.Serial(PORT, baud, timeout=1)
        time.sleep(0.1)

        # Send GetFirmwareVersion
        command = bytearray([
            0x00, 0x00, 0xFF, 0x02, 0xFE,
            0xD4, 0x02, 0x2A, 0x00
        ])

        ser.write(command)
        time.sleep(0.3)

        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"✅ RESPONSE! ({len(response)} bytes)")
            print(f"   Data: {response.hex(' ')}")

            if b'\x00\x00\xFF' in response:
                print(f"\n🎉 FOUND IT! Module responds at {baud} baud")
                print(f"   Use NFC_BAUD_RATE={baud} in your config\n")
                break
        else:
            print("No response")

        ser.close()

    except Exception as e:
        print(f"Error: {e}")

print("\nTest complete")
