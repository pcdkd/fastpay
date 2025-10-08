#!/usr/bin/env python3
"""
Write COMPLETE payment request to NTAG tag
Splits data across multiple pages to fit everything
"""
import serial
import json
import time
from adafruit_pn532.uart import PN532_UART

PORT = '/dev/tty.usbserial-ABSCDY4Z'
BAUDRATE = 115200

# FastPay payment request (compact format to fit on tag)
payment = {
    "v": 1,  # version (shortened)
    "m": "direct",  # mode
    "req": {
        "addr": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "name": "Alice's Coffee",
        "amt": "5000000",
        "cur": "USD",
        "fiat": "5.00",
        "desc": "Latte",
        "nonce": str(int(time.time() * 1000)),
        "exp": str(int((time.time() + 180) * 1000))
    },
    "sig": "0x1234abcd"  # Mock signature
}

def write_ntag_payload(pn532, uid, payload_bytes):
    """
    Write payload across multiple NTAG pages
    NTAG213: 144 bytes user data (pages 4-39, 4 bytes per page)
    """
    print(f"   Payload size: {len(payload_bytes)} bytes")

    # NTAG user data starts at page 4
    start_page = 4
    bytes_per_page = 4

    # Split payload into 4-byte chunks
    pages_needed = (len(payload_bytes) + bytes_per_page - 1) // bytes_per_page
    print(f"   Pages needed: {pages_needed}")

    if pages_needed > 36:  # NTAG213 has 36 user pages
        print(f"   ⚠️  Payload too large! Truncating to 144 bytes")
        payload_bytes = payload_bytes[:144]
        pages_needed = 36

    # Write each page
    for i in range(pages_needed):
        page_num = start_page + i
        start_idx = i * bytes_per_page
        end_idx = min(start_idx + bytes_per_page, len(payload_bytes))

        # Get 4 bytes (pad if needed)
        chunk = payload_bytes[start_idx:end_idx]
        chunk = chunk.ljust(bytes_per_page, b'\x00')

        try:
            pn532.ntag2xx_write_block(page_num, chunk)
            print(f"   ✅ Page {page_num}: {chunk.hex()}")
        except Exception as e:
            print(f"   ❌ Page {page_num} failed: {e}")
            return False

    return True

print("🔧 Write COMPLETE Payment Request to NTAG")
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

    # Create compact JSON (no whitespace)
    payment_json = json.dumps(payment, separators=(',', ':'))

    print("Payment Request:")
    print("-" * 60)
    print(json.dumps(payment, indent=2))
    print("-" * 60)
    print(f"\nCompact JSON: {len(payment_json)} bytes")
    print(f"Preview: {payment_json[:80]}...\n")

    print("="*60)
    print("📱 PLACE NFC TAG ON MODULE")
    print("="*60)
    print("Waiting for tag...\n")

    tag_found = False
    attempts = 0

    while not tag_found and attempts < 30:
        uid = pn532.read_passive_target(timeout=0.5)

        if uid and len(uid) == 4:
            uid_hex = uid.hex().upper()
            print(f"🎉 NTAG detected: {uid_hex}\n")

            # Try to read existing data first
            print("📖 Reading current tag data...")
            try:
                page4 = pn532.ntag2xx_read_block(4)
                print(f"   Page 4: {page4.hex()} ({page4})")
            except:
                pass

            # Write payment request
            print("\n📝 Writing payment request...")

            payload = payment_json.encode('utf-8')
            success = write_ntag_payload(pn532, uid, payload)

            if success:
                print("\n" + "="*60)
                print("✅ PAYMENT REQUEST WRITTEN TO TAG!")
                print("="*60)

                # Verify by reading back
                print("\n📖 Verifying write...")
                try:
                    # Read first few pages to verify
                    read_back = bytearray()
                    for page in range(4, 8):  # Read first 16 bytes
                        data = pn532.ntag2xx_read_block(page)
                        read_back.extend(data)

                    read_text = read_back.decode('utf-8', errors='ignore')
                    print(f"   Read back: {read_text[:50]}...")

                    if read_text.startswith('{"v":1'):
                        print("\n   ✅ Verification successful!")
                    else:
                        print("\n   ⚠️  Read back doesn't match expected format")

                except Exception as e:
                    print(f"   ⚠️  Verification failed: {e}")

                print("\n" + "="*60)
                print("📱 NOW READ WITH YOUR PHONE!")
                print("="*60)
                print("\nSteps:")
                print("1. Open 'NFC Tools' app on your phone")
                print("2. Tap 'READ' tab")
                print("3. Hold phone near the tag")
                print("4. You should see your payment request JSON!")
                print("\nWhat you'll see:")
                print(f'  {payment_json[:60]}...')

                tag_found = True

        attempts += 1
        if attempts % 5 == 0 and not tag_found:
            print(f"   Still waiting... ({attempts}/30)")

        time.sleep(0.5)

    if not tag_found:
        print("\n⏱️  No NTAG tag detected")
        print("\n💡 Make sure:")
        print("   - Tag is NTAG type (NTAG213, NTAG215, etc.)")
        print("   - Tag is within 1-2cm of module")
        print("   - Tag is not locked/password protected")

    uart.close()
    print("\n✅ Test complete")

except KeyboardInterrupt:
    print("\n⚠️  Stopped by user")
    if 'uart' in locals():
        uart.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
