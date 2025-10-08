#!/usr/bin/env python3
"""Test PN532 NFC module communication"""
import serial
import time

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

print("🔧 Testing PN532 NFC Module")
print(f"Port: {PORT}")
print(f"Baudrate: {BAUDRATE}\n")

try:
    # Open serial port
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    print("✅ Serial port opened\n")
    time.sleep(0.1)  # Let serial stabilize

    # Send GetFirmwareVersion command to PN532
    # Frame: Preamble + Length + Command + Checksum + Postamble
    print("📡 Sending GetFirmwareVersion command to PN532...")

    command = bytearray([
        0x00, 0x00, 0xFF,  # Preamble
        0x02,              # Length
        0xFE,              # Length checksum (0x100 - 0x02)
        0xD4,              # Direction (host to PN532)
        0x02,              # GetFirmwareVersion command
        0x2A,              # Data checksum (0x100 - 0xD4 - 0x02)
        0x00               # Postamble
    ])

    ser.write(command)
    print("   Command sent, waiting for response...\n")

    # Wait for response
    time.sleep(0.5)

    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"✅ Received {len(response)} bytes from PN532:")
        print(f"   Raw: {response.hex(' ')}\n")

        # Parse response (simplified)
        if len(response) >= 13:
            # Response format: 00 00 FF LEN LCS D5 03 IC VER REV SUP ...
            if response[0:3] == b'\x00\x00\xFF':
                print("✅ Valid PN532 response frame detected!")

                # Try to parse firmware info (byte positions may vary)
                try:
                    ic = response[7]
                    ver = response[8]
                    rev = response[9]
                    support = response[10]

                    print(f"\n🎉 PN532 NFC Module Detected!")
                    print(f"   IC Version: 0x{ic:02X}")
                    print(f"   Firmware: v{ver}.{rev}")
                    print(f"   Support: 0x{support:02X}")
                    print(f"\n✅ NFC module is working correctly!")
                except IndexError:
                    print("   Response received but couldn't parse firmware details")
                    print("   This might still be valid - module is responding!")
            else:
                print("⚠️  Response received but frame format unexpected")
                print("   Module may still be working - check wiring")
        else:
            print("⚠️  Response too short, expected ~13 bytes")
            print("   Module may be responding but signal quality is poor")
            print("   Check wiring connections")
    else:
        print("❌ No response from PN532")
        print("\n🔍 Troubleshooting:")
        print("   1. Check wiring:")
        print("      FT232 VCC → NFC VCC")
        print("      FT232 GND → NFC GND")
        print("      FT232 TX  → NFC C/R  (crossover!)")
        print("      FT232 RX  → NFC D/T  (crossover!)")
        print("   2. Make sure wires are firmly connected")
        print("   3. Check NFC module has power (LED on?)")
        print("   4. Verify module is in UART mode (not I2C/SPI)")

    ser.close()

except serial.SerialException as e:
    print(f"❌ Serial port error: {e}")
except KeyboardInterrupt:
    print("\n⚠️  Test interrupted by user")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
