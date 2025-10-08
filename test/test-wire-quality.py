#!/usr/bin/env python3
"""Test if we can at least send/receive SOMETHING on the serial port"""
import serial
import time

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

print("🔍 Testing raw serial communication quality\n")

try:
    ser = serial.Serial(PORT, BAUDRATE, timeout=0.5)
    print(f"✅ Port opened at {BAUDRATE} baud")

    # Test 1: Send bytes and check if they echo back (some modules echo)
    print("\nTest 1: Checking for echo...")
    test_bytes = b'\x55\xAA\xFF\x00'
    ser.write(test_bytes)
    time.sleep(0.2)

    if ser.in_waiting > 0:
        received = ser.read(ser.in_waiting)
        print(f"   Got {len(received)} bytes back: {received.hex(' ')}")
        if received == test_bytes:
            print("   ⚠️  Perfect echo detected - module might be in wrong mode")
        else:
            print("   ✅ Module is responding with different data")
    else:
        print("   No echo (normal for PN532)")

    # Test 2: Send continuous data
    print("\nTest 2: Sending continuous stream...")
    ser.write(b'\xFF' * 100)
    time.sleep(0.3)

    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"   ✅ Got {len(response)} bytes response")
        print(f"   First 20 bytes: {response[:20].hex(' ')}")
    else:
        print("   ❌ No response to data stream")

    # Test 3: Check DTR/RTS control (some modules need these)
    print("\nTest 3: Toggling control lines...")

    # Try with DTR low
    ser.dtr = False
    ser.rts = False
    time.sleep(0.1)
    ser.write(bytearray([0x00, 0x00, 0xFF, 0x02, 0xFE, 0xD4, 0x02, 0x2A, 0x00]))
    time.sleep(0.3)

    if ser.in_waiting > 0:
        print(f"   ✅ Response with DTR/RTS LOW")
        print(f"   Data: {ser.read(ser.in_waiting).hex(' ')}")
    else:
        print("   No response with DTR/RTS low")

    # Try with DTR high, RTS low
    ser.dtr = True
    ser.rts = False
    time.sleep(0.1)
    ser.write(bytearray([0x00, 0x00, 0xFF, 0x02, 0xFE, 0xD4, 0x02, 0x2A, 0x00]))
    time.sleep(0.3)

    if ser.in_waiting > 0:
        print(f"   ✅ Response with DTR HIGH, RTS LOW")
        print(f"   Data: {ser.read(ser.in_waiting).hex(' ')}")
    else:
        print("   No response with DTR high")

    ser.close()

    print("\n" + "="*50)
    print("📊 CONCLUSION:")
    print("If NO responses in any test → Bad wires or defective module")
    print("If ANY response → Module is alive, just wrong protocol/mode")

except Exception as e:
    print(f"❌ Error: {e}")
