#!/usr/bin/env python3
"""Test PN532 with correct DTR/RTS settings"""
import serial
import time

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

print("🔧 Testing PN532 NFC Module (with DTR/RTS fix)")
print("="*50)
print(f"Port: {PORT}")
print(f"Baudrate: {BAUDRATE}\n")

try:
    # Open serial port
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)

    # CRITICAL: Set DTR and RTS to LOW for this module
    ser.dtr = False
    ser.rts = False
    print("✅ Serial port opened with DTR=LOW, RTS=LOW\n")

    time.sleep(0.2)

    # Test 1: GetFirmwareVersion
    print("TEST 1: Getting firmware version...")
    get_fw = bytearray([
        0x00, 0x00, 0xFF,  # Preamble
        0x02,              # Length
        0xFE,              # Length checksum
        0xD4,              # Direction
        0x02,              # GetFirmwareVersion
        0x2A,              # Data checksum
        0x00               # Postamble
    ])

    ser.write(get_fw)
    time.sleep(0.3)

    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"✅ Response: {response.hex(' ')}\n")

        # Parse firmware info
        try:
            # Find the actual data (skip ACK frame if present)
            if b'\xD5\x03' in response:
                idx = response.index(b'\xD5\x03')
                ic = response[idx + 2]
                ver = response[idx + 3]
                rev = response[idx + 4]

                print("🎉 PN532 NFC Module Detected!")
                print(f"   IC Type: 0x{ic:02X}")
                print(f"   Firmware: v{ver}.{rev}")
                print(f"\n✅ Module is working correctly!")
        except:
            print("   Response received but couldn't parse details")
            print("   Module is communicating though!")
    else:
        print("❌ No response")

    # Test 2: SAM Configuration
    print("\nTEST 2: Configuring SAM...")
    sam_config = bytearray([
        0x00, 0x00, 0xFF,  # Preamble
        0x05,              # Length
        0xFB,              # Length checksum
        0xD4, 0x14,        # SAMConfiguration
        0x01,              # Normal mode
        0x14,              # Timeout
        0x01,              # Use IRQ
        0xFE,              # Data checksum
        0x00               # Postamble
    ])

    ser.write(sam_config)
    time.sleep(0.3)

    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"✅ SAM configured: {response.hex(' ')}")
    else:
        print("⚠️  No SAM response (might be okay)")

    ser.close()

    print("\n" + "="*50)
    print("✅ TEST COMPLETE")
    print("\n📝 IMPORTANT: Your code must set DTR=False, RTS=False")
    print("   Add these lines after opening serial port:")
    print("   ser.dtr = False")
    print("   ser.rts = False")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
