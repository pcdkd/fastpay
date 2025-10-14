#!/usr/bin/env python3
"""
Test PN532 using Adafruit's official library
This library has been tested on thousands of modules
"""
import serial
import time
from adafruit_pn532.uart import PN532_UART

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

print("🔧 Testing PN532 with Adafruit Library")
print("="*60)
print(f"Port: {PORT}")
print(f"Baudrate: {BAUDRATE}\n")

try:
    # Open serial port
    print("Opening serial port...")
    uart = serial.Serial(PORT, baudrate=BAUDRATE, timeout=1)

    # CRITICAL: Force DTR/RTS low (based on our findings)
    uart.dtr = False
    uart.rts = False
    print(f"✅ Port opened with DTR={uart.dtr}, RTS={uart.rts}\n")

    # Give the PN532 ample time to settle before running firmware probe.
    time.sleep(1.0)

    # Initialize PN532 with Adafruit library
    print("Initializing PN532 with Adafruit library...")
    pn532 = PN532_UART(uart, debug=False)

    # Try to get firmware version
    print("Attempting to read firmware version...\n")

    ic, ver, rev, support = pn532.firmware_version

    print("="*60)
    print("🎉 SUCCESS! PN532 DETECTED!")
    print("="*60)
    print(f"   IC: 0x{ic:02X}")
    print(f"   Firmware: v{ver}.{rev}")
    print(f"   Support: 0x{support:02X}")
    print("\n✅ Module is working with Adafruit library!")
    print("\n💡 This confirms the module hardware is functional.")
    print("   We can use Adafruit's code as reference for our implementation.")

except RuntimeError as e:
    print(f"❌ Adafruit library error: {e}")
    print("\n🔍 This suggests:")
    print("   1. Module may not be in correct UART mode")
    print("   2. Hardware configuration issue (solder jumpers on back?)")
    print("   3. Module may need different initialization sequence")

except Exception as e:
    print(f"❌ Error: {e}")
    print(f"   Type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

finally:
    print("\n" + "="*60)
    if 'uart' in locals():
        uart.close()
        print("Serial port closed")
