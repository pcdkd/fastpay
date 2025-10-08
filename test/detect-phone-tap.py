#!/usr/bin/env python3
"""
Simple test: Just detect when phone taps the NFC module
This proves the hardware interaction works
"""
import serial
import time
from adafruit_pn532.uart import PN532_UART

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

print("🔧 Phone Tap Detection Test")
print("="*60)
print("This will beep/print when it detects your phone\n")

try:
    # Open serial
    uart = serial.Serial(PORT, baudrate=BAUDRATE, timeout=1)
    uart.dtr = False
    uart.rts = False
    time.sleep(0.2)

    # Initialize PN532
    pn532 = PN532_UART(uart, debug=False)
    ic, ver, rev, support = pn532.firmware_version
    print(f"✅ PN532 v{ver}.{rev}\n")

    # Configure SAM
    pn532.SAM_configuration()

    print("="*60)
    print("📱 TAP YOUR PHONE ON THE NFC MODULE")
    print("="*60)
    print("Listening for NFC devices...")
    print("(Press Ctrl+C to stop)\n")

    tap_count = 0
    last_uid = None

    while True:
        # Read for any NFC target (tag, phone, card)
        uid = pn532.read_passive_target(timeout=0.5)

        if uid:
            # Convert to hex string for comparison
            uid_hex = uid.hex().upper()

            # Only announce if it's a new device (avoid spam from continuous read)
            if uid_hex != last_uid:
                tap_count += 1
                print(f"\n🎉 TAP #{tap_count} DETECTED!")
                print(f"   Time: {time.strftime('%H:%M:%S')}")
                print(f"   Device UID: {uid_hex}")
                print(f"   UID Length: {len(uid)} bytes")

                if len(uid) == 4:
                    print(f"   Type: Likely NFC tag or card")
                elif len(uid) == 7:
                    print(f"   Type: Likely phone or modern NFC tag")
                else:
                    print(f"   Type: Unknown ({len(uid)} byte UID)")

                print(f"\n   ✅ Your phone/tag CAN communicate with the module!")
                print(f"   Waiting for next tap...\n")

                last_uid = uid_hex

                # Keep reading same device for a moment
                time.sleep(0.5)
        else:
            # No device detected
            if last_uid is not None:
                # Device was removed
                last_uid = None
                # print("   Device removed\n")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\n📊 Session Summary:")
    print(f"   Total taps detected: {tap_count}")
    print(f"\n✅ Test complete")

    if 'uart' in locals():
        uart.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
