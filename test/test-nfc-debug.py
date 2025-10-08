#!/usr/bin/env python3
"""Debug PN532 NFC module - comprehensive diagnostics"""
import serial
import time

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

print("🔍 PN532 NFC Module Debug Tool")
print("="*50)
print(f"Port: {PORT}")
print(f"Baudrate: {BAUDRATE}\n")

try:
    # Open serial port
    ser = serial.Serial(PORT, BAUDRATE, timeout=2)
    print("✅ Serial port opened")
    print(f"   DTR: {ser.dtr}, RTS: {ser.rts}\n")
    time.sleep(0.2)

    # Test 1: Check if ANY data is received
    print("TEST 1: Checking for any existing data in buffer...")
    ser.reset_input_buffer()
    time.sleep(0.1)
    if ser.in_waiting > 0:
        garbage = ser.read(ser.in_waiting)
        print(f"   Found {len(garbage)} bytes: {garbage.hex(' ')}")
    else:
        print("   ✓ Buffer is clean\n")

    # Test 2: Send wake-up sequence (some PN532 modules need this)
    print("TEST 2: Sending PN532 wake-up sequence...")
    wakeup = bytearray([0x55, 0x55, 0x00, 0x00, 0x00])
    ser.write(wakeup)
    time.sleep(0.5)

    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"   Got wake-up response: {response.hex(' ')}\n")
    else:
        print("   No wake-up response (this is sometimes normal)\n")

    # Test 3: SAM Configuration (required before other commands)
    print("TEST 3: Sending SAM Configuration...")
    sam_config = bytearray([
        0x00, 0x00, 0xFF,  # Preamble
        0x05,              # Length (5 bytes: D4 14 01 14 01)
        0xFB,              # Length checksum (0x100 - 0x05)
        0xD4,              # Direction
        0x14,              # SAMConfiguration command
        0x01,              # Normal mode
        0x14,              # Timeout (1 second)
        0x01,              # Use IRQ
        0xFE,              # Data checksum
        0x00               # Postamble
    ])

    ser.write(sam_config)
    time.sleep(0.5)

    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"   ✅ SAM Config response: {response.hex(' ')}")
        if b'\x00\x00\xFF' in response:
            print("   ✅ Valid PN532 frame detected!\n")
        else:
            print("   ⚠️  Response format unexpected\n")
    else:
        print("   ❌ No SAM Config response\n")

    # Test 4: GetFirmwareVersion (the main test)
    print("TEST 4: Requesting firmware version...")
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
    time.sleep(0.5)

    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"   ✅ Firmware response: {response.hex(' ')}")

        # Try to parse
        if b'\x00\x00\xFF' in response and len(response) >= 13:
            try:
                # Find start of frame
                start = response.index(b'\x00\x00\xFF')
                ic = response[start + 7]
                ver = response[start + 8]
                rev = response[start + 9]

                print(f"\n   🎉 PN532 WORKING!")
                print(f"   Firmware: v{ver}.{rev}")
                print(f"   IC: 0x{ic:02X}\n")
            except:
                print("   Response detected but couldn't parse firmware\n")
        else:
            print("   Response format unexpected\n")
    else:
        print("   ❌ No firmware response\n")

    # Test 5: Raw byte echo test
    print("TEST 5: Testing raw communication...")
    ser.write(b'\x55')
    time.sleep(0.2)
    if ser.in_waiting > 0:
        echo = ser.read(ser.in_waiting)
        print(f"   Got response to 0x55: {echo.hex(' ')}\n")
    else:
        print("   ❌ No response to raw byte\n")

    print("="*50)
    print("\n📊 DIAGNOSIS:")

    if ser.in_waiting == 0:
        print("\n❌ Module is NOT responding to any commands\n")
        print("🔍 Check these in order:")
        print("   1. **POWER LED** - Is there a LED lit on the NFC module?")
        print("      If NO LED → Check VCC and GND connections")
        print("      If LED ON → Continue to step 2")
        print("\n   2. **MODE SWITCH** - Does your module have physical switches?")
        print("      Some DFRobot modules have I2C/UART switches")
        print("      Make sure it's set to UART mode (not I2C)")
        print("\n   3. **WIRING** - Double-check these connections:")
        print("      FT232 TX (yellow?) → NFC C/R")
        print("      FT232 RX (green?)  → NFC D/T")
        print("      NOT: TX→TX or RX→RX (that won't work!)")
        print("\n   4. **CABLE QUALITY** - Try different jumper wires")
        print("      Sometimes wires are broken internally")
        print("\n   5. **MODULE DEFECT** - Try connecting VCC to 3.3V instead of 5V")
        print("      (if your FT232 has a 3.3V pin)")

    ser.close()
    print("\n✅ Test complete")

except serial.SerialException as e:
    print(f"❌ Serial error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
