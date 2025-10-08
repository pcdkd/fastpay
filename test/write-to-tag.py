#!/usr/bin/env python3
"""
Write payment request to a PHYSICAL NFC tag
Easier to test than card emulation - just needs a blank NFC tag
"""
import serial
import json
import time
from adafruit_pn532.uart import PN532_UART

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

# Test payment request
payment_request = {
    "version": 1,
    "mode": "direct",
    "request": {
        "merchantAddress": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "merchantName": "Alice's Coffee",
        "amount": "5000000",
        "currency": "USD",
        "fiatAmount": "5.00",
        "description": "Grande Latte",
        "nonce": str(int(time.time() * 1000)),
        "expiry": str(int((time.time() + 180) * 1000))
    },
    "signature": "0x1234...abcd"  # Mock for testing
}

print("🔧 Write Payment Request to Physical NFC Tag")
print("="*60)
print("This writes to a blank NFC tag (NTAG213, Mifare Classic, etc.)\n")

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

    # Prepare payment data
    compact_json = json.dumps(payment_request, separators=(',', ':'))
    print("Payment Request:")
    print(compact_json[:100] + "...")
    print(f"\nSize: {len(compact_json)} bytes\n")

    print("="*60)
    print("📱 PLACE AN NFC TAG ON THE MODULE")
    print("="*60)
    print("Waiting for tag...")
    print("(Press Ctrl+C to stop)\n")

    tag_found = False
    attempts = 0

    while not tag_found and attempts < 30:
        # Try to read a tag (any type)
        uid = pn532.read_passive_target(timeout=0.5)

        if uid:
            print(f"\n🎉 Tag detected!")
            print(f"   UID: {uid.hex().upper()}")
            print(f"   UID Length: {len(uid)} bytes\n")

            # Determine tag type
            if len(uid) == 4:
                print("   Tag type: Mifare Classic or NTAG")
            elif len(uid) == 7:
                print("   Tag type: Mifare Ultralight or NTAG21x")

            # Try to write NDEF
            print("\n📝 Writing NDEF message...")

            try:
                # Attempt to write (this is simplified - real NDEF write needs more)
                # For full implementation, need to:
                # 1. Check tag type
                # 2. Authenticate if needed (Mifare Classic)
                # 3. Format NDEF container
                # 4. Write NDEF message with proper TLV structure

                print("   ⚠️  Full NDEF write not implemented yet")
                print("   (Requires tag-specific write commands)")

                print("\n✅ Tag detected successfully!")
                print("\n💡 To complete NDEF write, you need:")
                print("   1. Tag-specific library (nfcpy, ndef, etc.)")
                print("   2. Or use Adafruit's write_text_to_ndef() if available")
                print("   3. Or use NFC Tools app to write test data")

                tag_found = True

            except Exception as e:
                print(f"   ❌ Write error: {e}")

            break
        else:
            attempts += 1
            if attempts % 5 == 0:
                print(f"   Still waiting... ({attempts}/30)")
            time.sleep(1)

    if not tag_found:
        print("\n⏱️  No tag detected")
        print("\n📋 Options to test NFC reading:")
        print("\n1. **Get a blank NFC tag** (NTAG213 recommended)")
        print("   - Amazon: Search 'NTAG213 NFC tags'")
        print("   - ~$10 for 10 tags")
        print("   - Works with all phones")
        print("\n2. **Use NFC Tools app** to write test data:")
        print("   - Install 'NFC Tools' from Play Store")
        print("   - Write → Add a record → Text")
        print("   - Paste your JSON payment request")
        print("   - Write to any NFC tag/card")
        print("   - Test reading with phone")
        print("\n3. **Test card emulation** (complex):")
        print("   - Run write-payment-request.py")
        print("   - Requires full Type 4 Tag APDU handling")
        print("   - Coming in next iteration")

    uart.close()
    print("\n✅ Test complete")

except KeyboardInterrupt:
    print("\n\n⚠️  Stopped by user")
    if 'uart' in locals():
        uart.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
