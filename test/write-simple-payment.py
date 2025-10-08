#!/usr/bin/env python3
"""
Write payment request to phone/tag when detected
Tests actual data exchange, not just detection
"""
import serial
import json
import time
from adafruit_pn532.uart import PN532_UART

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

# Simple payment request
payment = {
    "merchant": "Alice's Coffee",
    "amount": "5.00 USDC",
    "item": "Grande Latte",
    "tap": time.strftime('%H:%M:%S')
}

print("🔧 Payment Request Data Exchange Test")
print("="*60)

try:
    # Setup
    uart = serial.Serial(PORT, baudrate=BAUDRATE, timeout=1)
    uart.dtr = False
    uart.rts = False
    time.sleep(0.2)

    pn532 = PN532_UART(uart, debug=False)
    ic, ver, rev, support = pn532.firmware_version
    print(f"✅ PN532 v{ver}.{rev}\n")

    pn532.SAM_configuration()

    payment_json = json.dumps(payment, indent=2)
    print("Payment to send:")
    print(payment_json)
    print()

    print("="*60)
    print("📱 TAP YOUR PHONE")
    print("="*60)
    print("Will attempt to send payment data when detected\n")

    while True:
        uid = pn532.read_passive_target(timeout=0.5)

        if uid:
            uid_hex = uid.hex().upper()
            print(f"\n🎉 Device detected: {uid_hex}")

            # Try to determine what kind of device this is
            print("   Analyzing device...")

            # For NFC-enabled phones/cards, try different approaches
            if len(uid) == 4:
                print("   Type: 4-byte UID (Mifare Classic/compatible)")

                # Try to authenticate (Mifare Classic)
                try:
                    # Default key
                    key = b'\xFF\xFF\xFF\xFF\xFF\xFF'
                    authenticated = pn532.mifare_classic_authenticate_block(
                        uid, 4, 0x60, key
                    )

                    if authenticated:
                        print("   ✅ Mifare authentication successful!")

                        # Try to write data
                        data = payment_json[:16].encode('utf-8')
                        data = data.ljust(16, b'\x00')  # Pad to 16 bytes

                        try:
                            pn532.mifare_classic_write_block(4, data)
                            print(f"   ✅ Wrote data: {data[:16]}")
                            print("   📱 Try reading with NFC Tools app!")

                        except Exception as e:
                            print(f"   ⚠️  Write failed: {e}")

                    else:
                        print("   ❌ Authentication failed (not a writable Mifare)")

                except Exception as e:
                    print(f"   ℹ️  Not a Mifare Classic: {e}")

                # Try NTAG/Ultralight commands
                try:
                    print("   Trying NTAG/Ultralight read...")
                    # Read page 4 (user data starts here)
                    data = pn532.ntag2xx_read_block(4)
                    if data:
                        print(f"   📖 Current data on page 4: {data.hex()}")

                        # Try to write
                        write_data = payment_json[:4].encode('utf-8')
                        write_data = write_data.ljust(4, b'\x00')

                        pn532.ntag2xx_write_block(4, write_data)
                        print(f"   ✅ Wrote to NTAG: {write_data.hex()}")
                        print("   📱 Read with NFC Tools app to verify!")

                except AttributeError:
                    print("   ℹ️  NTAG commands not available in this library version")
                except Exception as e:
                    print(f"   ℹ️  Not an NTAG: {e}")

            elif len(uid) == 7:
                print("   Type: 7-byte UID (Modern NFC tag or phone)")
                print("   ℹ️  This is likely your phone in reader mode")
                print("   💡 Phone is detecting the module, but can't write to it")
                print("   💡 You need an NFC tag, or implement card emulation")

            print("\n   Summary:")
            print("   - If you have blank NFC tags → Great! Can write data")
            print("   - If this is your phone → Need card emulation mode")
            print("   - To test reading: Use 'NFC Tools' app on your phone\n")

            time.sleep(2)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n✅ Test stopped")
    if 'uart' in locals():
        uart.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
