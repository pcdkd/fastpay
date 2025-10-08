#!/usr/bin/env python3
"""Test PN532 with wake-up sequence that worked"""
import serial
import time

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

print("🔧 Testing PN532 with wake-up sequence")
print("="*50)

try:
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    print("✅ Port opened\n")

    # Replicate what worked in test-wire-quality.py
    print("Step 1: Sending data with DTR/RTS HIGH (default)...")
    ser.dtr = True
    ser.rts = True
    time.sleep(0.1)

    # Send some dummy data to "wake" the module
    ser.write(b'\x55\xAA\xFF\x00')
    time.sleep(0.2)

    # Clear any garbage
    if ser.in_waiting > 0:
        garbage = ser.read(ser.in_waiting)
        print(f"   Cleared {len(garbage)} bytes")

    # Now set DTR/RTS LOW (this is when it worked)
    print("\nStep 2: Setting DTR/RTS LOW...")
    ser.dtr = False
    ser.rts = False
    time.sleep(0.2)

    print("\nStep 3: Sending GetFirmwareVersion...")
    get_fw = bytearray([
        0x00, 0x00, 0xFF, 0x02, 0xFE,
        0xD4, 0x02, 0x2A, 0x00
    ])

    ser.write(get_fw)
    time.sleep(0.5)  # Longer wait

    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"✅ Got response: {response.hex(' ')}\n")

        # Parse it
        if b'\xD5\x03' in response:
            idx = response.index(b'\xD5\x03')
            ic = response[idx + 2]
            ver = response[idx + 3]
            rev = response[idx + 4]

            print("🎉 SUCCESS!")
            print(f"   IC: 0x{ic:02X}")
            print(f"   Firmware: v{ver}.{rev}")
        else:
            print("   Got data but couldn't parse firmware")
    else:
        print("❌ Still no response")

        # Try one more thing - maybe it needs even MORE time
        print("\nStep 4: Trying with even longer delay...")
        time.sleep(1)

        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"✅ Delayed response: {response.hex(' ')}")
        else:
            print("❌ No delayed response either")

            # Last attempt - send wake-up with DTR/RTS low
            print("\nStep 5: Sending wake-up sequence with DTR/RTS LOW...")
            wakeup = bytearray([
                0x55, 0x55, 0x00, 0x00, 0x00,  # Wake-up
                0x00, 0x00, 0xFF, 0x02, 0xFE,  # GetFirmwareVersion
                0xD4, 0x02, 0x2A, 0x00
            ])
            ser.write(wakeup)
            time.sleep(0.5)

            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"✅ Wake-up response: {response.hex(' ')}")
            else:
                print("❌ No response to wake-up either")

    ser.close()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
